"""File watcher para el inbox (drop folder).

Detecta archivos nuevos en data/inbox/ y los procesa automáticamente.
Mueve los procesados a data/processed/ y los que fallan a data/rejected/.
"""
from __future__ import annotations

import json
import shutil
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .settings import settings


class InboxEventHandler(FileSystemEventHandler):
    """Handler que dispara `on_new_file` cuando se crea un archivo en inbox."""

    def __init__(self, on_new_file: Callable[[Path], None]):
        self.on_new_file = on_new_file

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        # Damos un pequeño delay para que el archivo termine de copiarse
        def _delayed():
            time.sleep(0.3)
            if path.exists() and path.stat().st_size > 0:
                self.on_new_file(path)
        threading.Thread(target=_delayed, daemon=True).start()


class InboxWatcher:
    """Watcher que monitorea el inbox y procesa automáticamente."""

    def __init__(self, on_new_file: Optional[Callable[[Path], None]] = None):
        self.observer: Optional[Observer] = None
        self._on_new_file = on_new_file
        self._running = False

    def start(self):
        if self._running:
            return
        handler = InboxEventHandler(
            self._on_new_file or self._default_handler
        )
        self.observer = Observer()
        self.observer.schedule(handler, str(settings.inbox_dir), recursive=False)
        self.observer.start()
        self._running = True
        print(f"[watcher] [OK] Watching {settings.inbox_dir}")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=2)
            self._running = False
            print("[watcher] stopped")

    def _default_handler(self, path: Path):
        """Handler por defecto: loguea y deja que el endpoint haga el resto."""
        print(f"[watcher] Nuevo archivo detectado: {path.name}")


# ----------------------------------------------------------------------
# Helpers de movimiento y parseo
# ----------------------------------------------------------------------

def parse_invoice_file(path: Path) -> Optional[dict]:
    """Parsea un archivo del inbox (.json o .txt con bloques clave:valor)."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")

    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError as e:
            print(f"[parse] ERROR JSON en {path.name}: {e}")
            return None

    if path.suffix.lower() == ".txt":
        # FIX BUG-012: detectar formato FACTURA (seccionado) vs key:value
        # FIX BUG-014: deteccion ampliada para Factura B (varios formatos)
        text_up = text.upper()
        if ("FACTURA" in text_up and (
            "TOTAL: ARS" in text_up or
            "TOTAL:$" in text_up or
            "TOTAL $" in text_up or
            "FACTURA B" in text_up or
            "[FACTURA B]" in text_up
        )):
            parsed = _parse_factura_txt(text, path.name)
            if parsed:
                return parsed
        # Formato simple key: value (uno por linea)
        result = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if k == "amount":
                    try:
                        v = float(v.replace(",", "").replace(".", "").replace(" ", ""))
                        if "," in text.split("amount:")[1].split("\n")[0]:
                            v = float(v / 100)
                    except ValueError:
                        pass
                result[k] = v
        return result or None

    return None


def _parse_factura_txt(text: str, filename: str = "") -> Optional[dict]:
    """FIX BUG-015: parser para FACTURA A/B/C argentina real.

    Tipos:
      - A (cod 01): emisor Resp. Inscripto -> discrimina IVA
      - B (cod 06): emisor Resp. Inscripto -> consumidor final (IVA incluido)
      - C (cod 11): emisor Monotributo/Exento -> sin IVA

    Formato esperado:
        [EMISOR] Razon Social / CUIT / Condicion IVA / Ing. Brutos / Inicio Act.
        [IDENTIFICACION] Codigo tipo / Punto de Venta / Numero / Fecha
        [RECEPTOR] Señor/es / Direccion / Localidad / CUIT / Condicion IVA
        [CONDICIONES] Contado / Cta. Cte. / Remito
        [ITEMS] Cantidad / Descripcion / P. Unitario / Importe
        [TOTALES] Subtotal / IVA (solo A) / Total
        [FISCAL] CAE / Vencimiento / Codigo Barras
    """
    import re
    result = {
        "tipo_comprobante": "FACTURA",
        "items": [],
        "format": "factura_abc_txt",
    }

    # Detectar tipo de comprobante (A, B, o C)
    m = re.search(r"\[FACTURA\s+([ABC])\]", text)
    if m:
        result["tipo_comprobante"] = f"FACTURA {m.group(1)}"
        result["letra_comprobante"] = m.group(1)

    # Detectar codigo AFIP (01=A, 06=B, 11=C)
    m = re.search(r"CODIGO\s*N..?\s*(\d+)", text)
    if m:
        result["codigo_tipo"] = m.group(1)
        codigo_map = {"01": "A", "06": "B", "11": "C", "13": "NC", "02": "ND"}
        if m.group(1) in codigo_map:
            result["letra_comprobante"] = codigo_map[m.group(1)]

    # ====== IDENTIFICACION ======
    m = re.search(r"N..?\s*(\d{4})\s*-\s*(\d{8})", text)
    if m:
        result["punto_venta"] = m.group(1)
        result["numero_comprobante"] = m.group(2)
        # FIX BUG-015: nomenclatura uniforme FC-<PV>-<NRO>
        result["invoice_id"] = f"FC-{m.group(1)}-{m.group(2)}"
    m = re.search(r"FECHA:\s+(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        d, mo, y = m.groups()
        result["invoice_date"] = f"{y}-{int(mo):02d}-{int(d):02d}"

    # ====== EMISOR ======
    m = re.search(r"Razon Social:\s+(.+)", text)
    if m: result["emisor_razon_social"] = m.group(1).strip()
    m = re.search(r"Rubro/Matricula:\s+(.+)", text)
    if m: result["emisor_rubro"] = m.group(1).strip()
    m = re.search(r"Direccion:\s+(.+)", text)
    if m: result["emisor_direccion"] = m.group(1).strip()
    m = re.search(r"CUIT:\s+(\d{2}-?\d{8}-?\d)", text)
    if m: result["emisor_cuit"] = m.group(1)
    m = re.search(r"Ing\. Brutos:\s+(.+)", text)
    if m: result["emisor_ingresos_brutos"] = m.group(1).strip()
    m = re.search(r"Inicio Act\.:\s+(.+)", text)
    if m: result["emisor_inicio_actividades"] = m.group(1).strip()
    m = re.search(r"Condicion IVA:\s+(.+)", text)
    if m: result["emisor_condicion_iva"] = m.group(1).strip()

    # ====== RECEPTOR ======
    m = re.search(r"Señor/es:\s+(.+)", text)
    if m: result["receptor_razon_social"] = m.group(1).strip()
    m = re.search(r"Dirección:\s+(.+)", text)
    if m: result["receptor_direccion"] = m.group(1).strip()
    m = re.search(r"Localidad:\s+(.+)", text)
    if m: result["receptor_localidad"] = m.group(1).strip()
    m = re.search(r"CUIT:\s+(\d{2}-?\d{8}-?\d)", text)
    if m:
        result["receptor_cuit"] = m.group(1)
        result["cuit"] = m.group(1)
    m = re.search(r"Condicion IVA:\s+(.+)", text)
    if m: result["receptor_condicion_iva"] = m.group(1).strip()

    # ====== CONDICIONES DE VENTA ======
    if re.search(r"Contado\s*\[X\]", text):
        result["condicion_venta"] = "Contado"
    elif re.search(r"Cta\. Cte\.\s*\[X\]", text):
        result["condicion_venta"] = "Cuenta Corriente"
    m = re.search(r"Remito\s*N..?:?\s*(.+)", text)
    if m and m.group(1).strip() != "-":
        result["remito_numero"] = m.group(1).strip()

    # ====== ITEMS ======
    items_section = re.search(r"CANT\.\s+DESCRIPCION.*?={5,}(.*?)={5,}", text, re.DOTALL)
    if items_section:
        for line in items_section.group(1).split("\n"):
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^(\d+)\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)$", line)
            if m:
                cantidad = int(m.group(1))
                descripcion = m.group(2).strip()
                precio_unit = _parse_amount_ar(m.group(3))
                importe = _parse_amount_ar(m.group(4))
                if precio_unit is not None and importe is not None:
                    result["items"].append({
                        "cantidad": cantidad,
                        "descripcion": descripcion,
                        "precio_unitario": precio_unit,
                        "importe": importe,
                    })

    # ====== TOTALES (diferente por tipo) ======
    letra = result.get("letra_comprobante", "B")

    # Para Factura A: subtotal + IVA + total
    m = re.search(r"Subtotal.*?gravado.*?:\s*([\d.,]+)", text)
    if m:
        result["subtotal_gravado"] = _parse_amount_ar(m.group(1))

    m = re.search(r"IVA\s+21%.*?:\s*([\d.,]+)", text)
    if m:
        result["iva_21"] = _parse_amount_ar(m.group(1))

    # TOTAL siempre presente
    m = re.search(r"TOTAL\s*\$\s*([\d.,]+)", text)
    if m:
        total = _parse_amount_ar(m.group(1))
        if total is not None:
            result["amount"] = total
            result["total"] = total

    result.setdefault("currency", "ARS")
    # subtotal para factura B/C = total (sin IVA)
    if letra in ("B", "C") and "subtotal_gravado" not in result:
        result["subtotal_gravado"] = result.get("amount", 0.0)
        result["iva_21"] = 0.0

    # ====== FISCAL ======
    m = re.search(r"CAE:\s+(\d+)", text)
    if m: result["cae"] = m.group(1)
    m = re.search(r"Vencimiento:\s+(\d{1,2}/\d{1,2}/\d{4})", text)
    if m: result["cae_vencimiento"] = m.group(1)
    m = re.search(r"Codigo Barras:\s+(\d+)", text)
    if m: result["codigo_barras"] = m.group(1)

    # ====== IMPRESOR ======
    m = re.search(r"Impreso por\s+(.+?)\s*-\s*C\.U\.I\.T\.\s*(\d{2}-?\d{8}-?\d)", text)
    if m:
        result["impresor_razon_social"] = m.group(1).strip()
        result["impresor_cuit"] = m.group(2)
    m = re.search(r"Exp\.\s*(\d+)", text)
    if m: result["impresor_expediente"] = m.group(1)
    m = re.search(r"Fecha de Imp\.\s+(\w+\s+\d{4})", text)
    if m: result["impresor_fecha"] = m.group(1)
    m = re.search(r"Imp\. del\s+(\S+)\s+al\s+(\S+)", text)
    if m:
        result["impresor_rango_desde"] = m.group(1)
        result["impresor_rango_hasta"] = m.group(2)

    # ====== Supplier ID resolucion ======
    # FIX BUG-015: ahora filename es FC-PV-NRO.txt (sin SUPXXX)
    # Buscar por CUIT del emisor en suppliers.db
    if "supplier_id" not in result and "emisor_cuit" in result:
        sid = _resolve_supplier_by_cuit(result["emisor_cuit"])
        if sid:
            result["supplier_id"] = sid
    # Fallback: buscar SUPXXX en filename o cuerpo
    if "supplier_id" not in result:
        fname_match = re.search(r"SUP(\d{3})", filename)
        if fname_match:
            result["supplier_id"] = f"SUP{fname_match.group(1)}"
        else:
            m = re.search(r"SUP(\d{3})", text)
            if m:
                result["supplier_id"] = f"SUP{m.group(1)}"

    return result if result else None




def _resolve_supplier_by_cuit(cuit: str) -> Optional[str]:
    """FIX BUG-015: resuelve supplier_id a partir del CUIT del emisor.

    Busca en app/data/suppliers.db por CUIT (con o sin guiones).
    """
    import sqlite3
    from pathlib import Path
    db_path = Path(__file__).resolve().parents[1] / "data" / "suppliers.db"
    if not db_path.exists():
        return None
    cuit_norm = cuit.replace("-", "").replace(" ", "")
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            # Buscar con y sin guiones
            row = conn.execute(
                "SELECT supplier_id FROM suppliers WHERE REPLACE(cuit, '-', '') = ?",
                (cuit_norm,),
            ).fetchone()
            if row:
                return row["supplier_id"]
    except Exception:
        pass
    return None

def _parse_amount_ar(s: str) -> Optional[float]:
    """Parsea monto en formato argentino: 1.234.567,89 → 1234567.89"""
    if not s:
        return None
    s = s.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None






def _resolve_supplier_by_cuit(cuit: str) -> Optional[str]:
    """FIX BUG-015: resuelve supplier_id a partir del CUIT del emisor.

    Busca en app/data/suppliers.db por CUIT (con o sin guiones).
    """
    import sqlite3
    from pathlib import Path
    db_path = Path(__file__).resolve().parents[1] / "data" / "suppliers.db"
    if not db_path.exists():
        return None
    cuit_norm = cuit.replace("-", "").replace(" ", "")
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            # Buscar con y sin guiones
            row = conn.execute(
                "SELECT supplier_id FROM suppliers WHERE REPLACE(cuit, '-', '') = ?",
                (cuit_norm,),
            ).fetchone()
            if row:
                return row["supplier_id"]
    except Exception:
        pass
    return None

def _parse_amount_ar(s: str) -> Optional[float]:
    """Parsea monto en formato argentino: 1.234.567,89 → 1234567.89"""
    if not s:
        return None
    s = s.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None




def move_file(src: Path, dst_dir: Path) -> Path:
    """Mueve `src` a `dst_dir` (sobrescribe si existe)."""
    dst = dst_dir / src.name
    if dst.exists():
        # Renombrar con timestamp para no pisar
        ts = time.strftime("%Y%m%d-%H%M%S")
        dst = dst_dir / f"{src.stem}.{ts}{src.suffix}"
    shutil.move(str(src), str(dst))
    return dst