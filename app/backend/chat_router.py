"""Chat IA - Asistente Inteligente GI (FIX BUG-019 + SPEC_013).

Capacidades:
- Consultas en lenguaje natural (15+ intents)
- Memoria conversacional (sesiones persistentes)
- Acciones sobre el sistema (modificar contratos, etc.)
- Confirmaciones para acciones destructivas

Storage: chat_sessions.db (SQLite) en data/
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .settings import settings
from .orchestrator import process_invoice
from .watcher import parse_invoice_file, move_file


router = APIRouter(prefix="/chat", tags=["chat"])

# ----------------------------------------------------------------------
# Storage de sesiones (SPEC_013)
# ----------------------------------------------------------------------
CHAT_DB = PROJECT_ROOT = Path(__file__).resolve().parents[2] / "data" / "chat_sessions.db"
CHAT_DB.parent.mkdir(parents=True, exist_ok=True)

CHAT_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT NOT NULL,
    last_active_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    intent TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""


def get_chat_conn():
    conn = sqlite3.connect(str(CHAT_DB))
    conn.row_factory = sqlite3.Row
    return conn


def init_chat_db():
    with get_chat_conn() as conn:
        conn.executescript(CHAT_SCHEMA)
        conn.commit()


# Inicializar al cargar el módulo
init_chat_db()


def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Devuelve un session_id existente o crea uno nuevo."""
    if session_id:
        with get_chat_conn() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row:
                # Update last_active
                conn.execute(
                    "UPDATE sessions SET last_active_at = ? WHERE id = ?",
                    (datetime.utcnow().isoformat(timespec="seconds") + "Z", session_id),
                )
                conn.commit()
                return session_id
    # Crear nueva
    new_id = f"chat-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with get_chat_conn() as conn:
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?)",
            (new_id, "Nueva conversación", now, now),
        )
        conn.commit()
    return new_id


def save_message(session_id: str, role: str, content: str, intent: Optional[str] = None):
    with get_chat_conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, intent, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, intent, datetime.utcnow().isoformat(timespec="seconds") + "Z"),
        )
        conn.commit()


def load_context(session_id: str, n: int = 5) -> list:
    """Carga los últimos N mensajes de la sesión."""
    with get_chat_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, intent FROM messages WHERE session_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (session_id, n),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def get_last_entity(session_id: str, entity_type: str) -> Optional[str]:
    """Busca la última mención de una entidad (supplier_id, amount, etc.) en el contexto."""
    ctx = load_context(session_id, n=10)
    for msg in reversed(ctx):
        if msg["role"] != "user":
            continue
        content = msg["content"]
        if entity_type == "supplier_id":
            m = re.search(r"\bSUP\d{3}\b", content)
            if m:
                return m.group(0)
        elif entity_type == "amount":
            m = re.search(r"\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)", content.replace(".", "").replace(",", ""))
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    pass
        elif entity_type == "invoice_id":
            m = re.search(r"\b(?:FC-\d{4}-\d{8}|[A-Z]{2,}-?\d{2,})\b", content)
            if m:
                return m.group(0)
    return None


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    intent: str
    message: str
    data: Optional[dict] = None
    session_id: Optional[str] = None
    requires_confirmation: Optional[str] = None  # accion que requiere confirm


# ----------------------------------------------------------------------
# Entity Extraction (SPEC_013)
# ----------------------------------------------------------------------

ENTITY_PATTERNS = {
    "supplier_id": r"\bSUP\d{3}\b",
    "invoice_id": r"\b(?:FC-\d{4}-\d{8}|[A-Z]{2,}-?\d{2,})\b",
    "amount": r"\$\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*([kKmM]?)|(\d{3,})\s*(?:mil|k)?",
    "mode": r"\b(exacto|no\s+superar|strict|exacto\s*monto|monto\s*exacto)\b",
    "field": r"\b(email|tel[eé]fono|nombre|categor[ií]a|cuit|direcci[oó]n)\b",
}


def extract_entities(text: str, session_id: Optional[str] = None) -> dict:
    """Extrae entidades del texto. Si falta, busca en el contexto."""
    entities = {}
    text_lower = text.lower()

    # Supplier ID
    m = re.search(ENTITY_PATTERNS["supplier_id"], text, re.I)
    if m:
        entities["supplier_id"] = m.group(0).upper()
    elif session_id:
        last = get_last_entity(session_id, "supplier_id")
        if last:
            entities["supplier_id"] = last

    # Invoice ID
    m = re.search(ENTITY_PATTERNS["invoice_id"], text, re.I)
    if m:
        entities["invoice_id"] = m.group(0).upper()
    elif session_id:
        last = get_last_entity(session_id, "invoice_id")
        if last:
            entities["invoice_id"] = last

    # Amount (MEJORADO para formato argentino: 52.000, 52000, $52.000, etc)
    # Primero buscar formato con $: "$200.000" o "$200,000" o "$52.000"
    m = re.search(r"\$\s*([\d.]+)", text)
    if m:
        amt_str = m.group(1).strip()
        # Detectar formato AR: 200.000 vs 200,000 vs 200.000,50
        if "," in amt_str and "." in amt_str:
            if amt_str.rfind(",") > amt_str.rfind("."):
                amt_str = amt_str.replace(".", "").replace(",", ".")
            else:
                amt_str = amt_str.replace(",", "")
        elif "," in amt_str:
            parts = amt_str.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                amt_str = amt_str.replace(",", ".")
            elif len(parts) == 2 and len(parts[1]) == 3:
                # Formato AR con miles: 52.000 -> 52000
                amt_str = amt_str.replace(".", "").replace(",", "")
        elif "." in amt_str:
            parts = amt_str.split(".")
            if len(parts) == 2 and len(parts[1]) == 3:
                # Posible formato AR con miles: 52.000 = 52000
                amt_str = amt_str.replace(".", "")
            elif len(parts) == 2 and len(parts[1]) == 2:
                # Formato con decimales: 52.00 = 52
                amt_str = amt_str.replace(".", "")
        try:
            entities["amount"] = float(amt_str)
        except ValueError:
            pass
    else:
        # Formato sin $: buscar numeros grandes (4+ digitos)
        # Incluye formato argentino: 52.000, 52000, 200k, 200 mil
        m = re.search(r"\b(\d{1,3}(?:[.,]\d{3})+|\d{4,7})\b", text)
        if m:
            amt_str = m.group(1)
            # Limpiar formato argentino
            amt_str = amt_str.replace(".", "").replace(",", "")
            try:
                entities["amount"] = float(amt_str)
            except ValueError:
                pass
    if "amount" not in entities and session_id:
        last = get_last_entity(session_id, "amount")
        if last:
            entities["amount"] = last

    # Mode (exacto / no_superar)
    if re.search(r"\b(exacto|exacto\s*monto|monto\s*exacto|strict)\b", text, re.I):
        entities["mode"] = "EXACTO"
    elif re.search(r"\b(no\s+superar|hasta|m[aá]ximo)\b", text, re.I):
        entities["mode"] = "NO_SUPERAR"

    # Field (email, telefono, etc)
    m = re.search(ENTITY_PATTERNS["field"], text, re.I)
    if m:
        entities["field"] = m.group(0).lower()

    return entities


# ----------------------------------------------------------------------
# Intent Parsing (ordenado por especificidad)
# ----------------------------------------------------------------------

INTENT_RE = [
    # 0. context_related (preguntas sobre el ultimo resultado listado - ALTA PRIORIDAD)
    (re.compile(r"\b(cual\s+((fue?\s+)?la|el|es?)|la\s+(ultima|ultimo|anterior|pasada)|ultima|ultimo|anterior)\b", re.I),
     "context_related"),
    # 1. process_all
    (re.compile(r"\b(proces[áa]|aprueb[áa]|revis[áa]).*(todo|Todas|all)\b", re.I),
     "process_all"),
    # 2. process_one
    (re.compile(r"\b(proces[áa]|aprueb[áa]).*([A-Z]{2,}-?\d{2,})\b", re.I),
     "process_one"),
    # 3. process_path
    (re.compile(r"([\/\\]inbox[\/\\][^\s]+\.(?:json|txt))", re.I),
     "process_path"),
    # 4. set_contract_limit (FIX SPEC_013 + BUG-020: regex con verbos completos)
    (re.compile(r"\b(cambiar?|modificar?|actualizar?|poner|establecer|definir?|fijar?|subir|bajar?|ajustar?)\b.*(l[íi]mite|monto|m[áa]ximo|tope|amount|cap|techo|contrato|que\s+no)", re.I),
     "set_contract_limit"),
    # 5. set_contract_mode (cambiar modo exacto/no_superar)
    (re.compile(r"\b(cambi[áa]r?|poner|modific[áa]r?)\b.*(modo|forma).*(contrato|validaci[óo]n|exacto|no\s*superar)", re.I),
     "set_contract_mode"),
    # 6. activate_supplier
    (re.compile(r"\b(activ[áa]r?|activ[áa]lo|habilit[áa]r?)\b.*(SUP\d{3}|proveedor)", re.I),
     "activate_supplier"),
    # 7. deactivate_supplier
    (re.compile(r"\b(desactiv[áa]r?|deshabilit[áa]r?|suspend[ée]r?|inactiv[áa]r?)\b.*(SUP\d{3}|proveedor)", re.I),
     "deactivate_supplier"),
    # 8. update_supplier_field (cambiar X de SUP00X a Y)
    (re.compile(r"\b(cambi[áa]r?|modific[áa]r?|actualiz[áa]r?)\b.*(email|tel[ée]fono|nombre|categor[íi]a|cuit)", re.I),
     "update_supplier_field"),
    # 9. delete_supplier
    (re.compile(r"\b(elimin[áa]r?|eliminar|borr[áa]r?|remov[ée]r?|dar\s*de\s*baja)\b.*(SUP\d{3}|proveedor)", re.I),
     "delete_supplier"),
    # 10. history_amounts (debe ir ANTES que history)
    (re.compile(r"(monto|importe|precio|valor|cu[aá]nto|cuesta).*(historial|procesad|registrad|pagad|hist)", re.I),
     "history_amounts"),
    # 11. inbox_amounts con contexto
    (re.compile(r"(monto|importe|precio|valor|suman|cu[aá]nto|cuesta).*inbox|inbox.*(monto|importe|suman|cu[aá]nto)", re.I),
     "inbox_amounts"),
    # 12. totals
    (re.compile(r"total.*(factur|general|sistem|aprobad)|total\s*factur|totalizado|cu[aá]nto.*suman|totaliz|sumar", re.I),
     "totals"),
    # 13. history (genérico)
    (re.compile(r"\bhistorial\b|pagos?\s+(registrad|procesad)", re.I),
     "history"),
    # 13b. Memory shortcut: "ahora/ese mismo/esa misma/el mismo"
    (re.compile(r"\b(ahora\s+\w+|ese\s+mismo|esa\s+misma|el\s+mismo)\b", re.I),
     "memory_action"),
    # 14. summary
    (re.compile(r"\b(resumen|sumario|panoram|overview)\b", re.I),
     "summary"),
    # 15. help
    (re.compile(r"\b(ayuda|help|qu[ée]\s+(pod[eé]s|hac)|c[oó]mo|opciones)\b", re.I),
     "help"),
    # 16. inbox_amounts catch-all
    (re.compile(r"\b(montos?|importes?|precios?|valores?|cuesta|cu[aá]nto|cu[aá]nta|cu[aá]ntes|cu[aá]les|sumar)\b", re.I),
     "inbox_amounts"),
    # 17. list_inbox
    (re.compile(r"\b(qu[ée]\s+(hay|facturas)|list.*inbox|pendientes|archivos\s+en|cuales.*facturas|facturas.*(hay|pendientes))\b", re.I),
     "list_inbox"),
    # X. list_by_status (facturas por estado)
    (re.compile(r"\b(cuantas?|cuenta|tengo|hay)\b.*\b(facturas?|aprobadas?|rechazadas?)\b", re.I),
     "list_by_status"),
    # X. listar_facturas
    # X. listar_facturas (MEJORADO)
    (re.compile(r"\blist(?:ar|o|ando|e)?\s*(?:las\s+)?(?:facturas?|todas?|facturitas?)", re.I),
     "listar_facturas"),
    # X. list_suppliers
    (re.compile(r"\blistar?\s+proveedores?|ver\s+proveedores?", re.I),
     "list_suppliers"),
    # X. supplier_info
    (re.compile(r"\binfo\b.*\b(SUP\d{3}|proveedor)", re.I),
     "supplier_info"),
]


def parse_intent(message: str) -> tuple[str, Optional[str]]:
    msg_norm = message.strip()
    for pat, intent in INTENT_RE:
        m = pat.search(msg_norm)
        if m:
            param = m.group(1) if m.groups() else None
            return intent, param
    return "unknown", None


# ----------------------------------------------------------------------
# Action Handlers (SPEC_013)
# ----------------------------------------------------------------------

def action_set_contract_limit(entities: dict) -> dict:
    """FIX SPEC_013: cambiar límite de contrato de un proveedor."""
    sid = entities.get("supplier_id")
    new_limit = entities.get("amount")
    mode = entities.get("mode")  # opcional, mantiene si no se pasa
    if not sid:
        return {"intent": "set_contract_limit", "ok": False, "error": "Falta supplier_id (ej: SUP001)"}
    if not new_limit:
        return {"intent": "set_contract_limit", "ok": False, "error": "Falta el monto (ej: 200000)"}
    try:
        with httpx.Client(timeout=10.0) as client:
            # 1. Obtener contrato actual
            r = client.get(f"http://localhost:8001/suppliers/{sid}/contract")
            if r.status_code != 200:
                return {"intent": "set_contract_limit", "ok": False, "error": f"No se pudo obtener contrato de {sid}"}
            current = r.json().get("contract") or {}
            old_limit = current.get("contract_limit", 0)
            current_mode = current.get("mode", "NO_SUPERAR")
            # 2. Si no se especifica mode, mantener el actual
            final_mode = mode or current_mode
            # 3. POST nuevo contrato (reemplaza)
            r = client.post(
                f"http://localhost:8001/suppliers/{sid}/contract",
                json={
                    "contract_limit": new_limit,
                    "mode": final_mode,
                    "start_date": current.get("start_date"),
                    "end_date": current.get("end_date"),
                },
            )
            if r.status_code == 200:
                return {
                    "intent": "set_contract_limit",
                    "ok": True,
                    "supplier_id": sid,
                    "old_limit": old_limit,
                    "new_limit": new_limit,
                    "mode": final_mode,
                    "message": f"✅ Límite de {sid} actualizado de ${old_limit:,.0f} a ${new_limit:,.0f} (modo: {final_mode})",
                }
            return {"intent": "set_contract_limit", "ok": False, "error": f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def action_set_contract_mode(entities: dict) -> dict:
    """FIX SPEC_013: cambiar modo del contrato (EXACTO/NO_SUPERAR)."""
    sid = entities.get("supplier_id")
    mode = entities.get("mode")
    if not sid:
        return {"intent": "set_contract_mode", "ok": False, "error": "Falta supplier_id"}
    if not mode:
        return {"intent": "set_contract_mode", "ok": False, "error": "Falta el modo (exacto/no_superar)"}
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"http://localhost:8001/suppliers/{sid}/contract")
            if r.status_code != 200:
                return {"ok": False, "error": f"No hay contrato para {sid}"}
            current = r.json().get("contract") or {}
            old_mode = current.get("mode", "?")
            r = client.post(
                f"http://localhost:8001/suppliers/{sid}/contract",
                json={
                    "contract_limit": current.get("contract_limit", 0),
                    "mode": mode,
                    "start_date": current.get("start_date"),
                    "end_date": current.get("end_date"),
                },
            )
            if r.status_code == 200:
                return {
                    "intent": "set_contract_mode",
                    "ok": True,
                    "supplier_id": sid,
                    "old_mode": old_mode,
                    "new_mode": mode,
                    "message": f"✅ Modo del contrato de {sid} cambiado de {old_mode} a {mode}",
                }
            return {"intent": "set_contract_mode", "ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"intent": "set_contract_mode", "ok": False, "error": str(e)}


def action_activate_supplier(entities: dict) -> dict:
    sid = entities.get("supplier_id")
    if not sid:
        return {"intent": "activate_supplier", "ok": False, "error": "Falta supplier_id"}
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.put(
                f"http://localhost:8001/suppliers/{sid}/status",
                json={"status": "ACTIVE"},
            )
            if r.status_code == 200:
                return {"intent": "activate_supplier", "ok": True, "supplier_id": sid, "new_status": "ACTIVE",
                        "message": f"✅ {sid} activado"}
            return {"intent": "activate_supplier", "ok": False, "error": f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"intent": "activate_supplier", "ok": False, "error": str(e)}


def action_deactivate_supplier(entities: dict) -> dict:
    sid = entities.get("supplier_id")
    if not sid:
        return {"intent": "deactivate_supplier", "ok": False, "error": "Falta supplier_id"}
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.put(
                f"http://localhost:8001/suppliers/{sid}/status",
                json={"status": "INACTIVE"},
            )
            if r.status_code == 200:
                return {"intent": "deactivate_supplier", "ok": True, "supplier_id": sid, "new_status": "INACTIVE",
                        "message": f"✅ {sid} desactivado"}
            return {"intent": "deactivate_supplier", "ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"intent": "deactivate_supplier", "ok": False, "error": str(e)}


def action_delete_supplier(entities: dict) -> dict:
    """FIX SPEC_013: baja lógica con confirmación."""
    sid = entities.get("supplier_id")
    if not sid:
        return {"intent": "delete_supplier", "ok": False, "error": "Falta supplier_id"}
    # Devuelve requires_confirmation; el frontend debe pedir confirm
    return {
        "intent": "delete_supplier",
        "ok": False,
        "requires_confirmation": "delete_supplier",
        "supplier_id": sid,
        "message": f"⚠️ ¿Confirmás dar de baja al proveedor {sid}? Esta acción no se puede deshacer. Respondé 'sí' o 'no'.",
    }


def action_delete_supplier_confirmed(entities: dict) -> dict:
    sid = entities.get("supplier_id")
    if not sid:
        return {"intent": "delete_supplier", "ok": False, "error": "Falta supplier_id"}
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.delete(f"http://localhost:8001/suppliers/{sid}")
            if r.status_code == 200:
                return {"intent": "delete_supplier", "ok": True, "supplier_id": sid,
                        "message": f"✅ {sid} dado de baja (INACTIVE)"}
            return {"intent": "delete_supplier", "ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"intent": "delete_supplier", "ok": False, "error": str(e)}


def action_update_supplier_field(entities: dict) -> dict:
    """FIX SPEC_013: actualizar un campo del proveedor."""
    sid = entities.get("supplier_id")
    field = entities.get("field")
    if not sid:
        return {"intent": "update_supplier_field", "ok": False, "error": "Falta supplier_id"}
    if not field:
        return {"intent": "update_supplier_field", "ok": False, "error": "Falta el campo a modificar (email, telefono, nombre, etc.)"}

    # Extraer el valor: buscar después de "a" o "por"
    # El valor está después del patrón "a" seguido de algo
    # Ej: "cambiar email de SUP001 a billing@x.com"
    value_match = re.search(r"a\s+['\"]?([\w@\.\-\+\$]+(?:\s+[\w@\.\-\+\$]+)*)", entities.get("raw_message", ""))
    if not value_match:
        # Intentar extraer un email
        email_match = re.search(r"[\w\.\-]+@[\w\.\-]+\.\w+", entities.get("raw_message", ""))
        if email_match and field == "email":
            value = email_match.group(0)
        else:
            # Intentar después de "por"
            value_match = re.search(r"por\s+['\"]?(.+?)(?:['\"]|$)", entities.get("raw_message", ""))
            if value_match:
                value = value_match.group(1).strip()
            else:
                return {"intent": "update_supplier_field", "ok": False, "error": f"No se pudo extraer el valor para {field}"}
    else:
        value = value_match.group(1).strip().strip("'\"")

    field_map = {
        "email": "email",
        "teléfono": "phone",
        "telefono": "phone",
        "nombre": "name",
        "categoría": "category",
        "categoria": "category",
        "dirección": None,  # no soportado en modelo
        "direccion": None,
        "cuit": "cuit",
    }
    api_field = field_map.get(field)
    if not api_field:
        return {"intent": "update_supplier_field", "ok": False, "error": f"Campo '{field}' no soportado"}

    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.put(
                f"http://localhost:8001/suppliers/{sid}",
                json={api_field: value},
            )
            if r.status_code == 200:
                return {"intent": "update_supplier_field", "ok": True, "supplier_id": sid, "field": api_field, "new_value": value,
                        "message": f"✅ {sid}.{api_field} = {value}"}
            return {"intent": "update_supplier_field", "ok": False, "error": f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"intent": "update_supplier_field", "ok": False, "error": str(e)}


# ----------------------------------------------------------------------
# Read Handlers (consultas)
# ----------------------------------------------------------------------

def handle_process_all() -> dict:
    files = sorted(settings.inbox_dir.glob("*"))
    files = [f for f in files if f.is_file() and f.suffix.lower() in {".json", ".txt"}]
    results = [_process_single_file(f) for f in files]
    return {
        "intent": "process_all",
        "message": f"Procesadas {len(results)} facturas del inbox.",
        "data": {"results": results},
    }


def handle_process_one(invoice_id: str) -> dict:
    candidates = list(settings.inbox_dir.glob(f"*{invoice_id}*"))
    if not candidates:
        return {
            "intent": "process_one",
            "message": f"No encontré ninguna factura con ID {invoice_id} en el inbox.",
            "data": {"found": False, "invoice_id": invoice_id},
        }
    results = [_process_single_file(f) for f in candidates]
    return {
        "intent": "process_one",
        "message": f"Procesada factura {invoice_id}",
        "data": {"results": results},
    }


def handle_process_path(path_str: str) -> dict:
    path_str = path_str.strip().strip('"').strip("'")
    path = Path(path_str)
    if not path.exists():
        alt = settings.inbox_dir / path.name
        if alt.exists():
            path = alt
        else:
            return {"intent": "process_path", "message": f"No encontré el archivo: {path_str}",
                    "data": {"found": False}}
    return {"intent": "process_path", "message": f"Procesado {path.name}",
            "data": {"results": [_process_single_file(path)]}}


def handle_list_by_status(message: str = "") -> dict:
    """Lista facturas por estado."""
    if not settings.payments_db.exists():
        return {"intent": "list_by_status", "message": "No hay datos aun.", "data": {}}
    
    msg_lower = message.lower()
    if "aprobad" in msg_lower:
        estado = "APPROVED"
        label = "aprobadas"
    elif "rechazad" in msg_lower:
        estado = "REJECTED"
        label = "rechazadas"
    elif "escalad" in msg_lower:
        estado = "ESCALATED"
        label = "escaladas"
    else:
        estado = None
        label = "todas"
    
    with sqlite3.connect(str(settings.payments_db)) as conn:
        conn.row_factory = sqlite3.Row
        if estado:
            rows = conn.execute("SELECT * FROM payments WHERE decision = ? ORDER BY id DESC LIMIT 50", (estado,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM payments ORDER BY id DESC LIMIT 50").fetchall()
    
    items = [dict(r) for r in rows]
    
    if not items:
        return {"intent": "list_by_status", "message": "No hay facturas " + label + ".", "data": {}}
    
    lines_out = ["Facturas " + label + " (" + str(len(items)) + " total):"]
    for item in items[:15]:
        lines_out.append("- " + str(item.get('invoice_id', '?')) + " | " + str(item.get('supplier_id', '?')) + " | $" + f"{item.get('amount', 0):,.2f}")
    
    return {"intent": "list_by_status", "message": "\n".join(lines_out), "data": {"items": items}}


def handle_context_related(session_id: str) -> dict:
    """Responde preguntas contextuales sobre el ultimo resultado listado."""
    ctx = load_context(session_id, n=10)
    
    # Buscar el ultimo intent que haya listado algo
    last_list_intent = None
    last_assistant_msg = None
    
    for msg in reversed(ctx):
        if msg.get("role") == "assistant":
            last_assistant_msg = msg.get("content", "")
            last_list_intent = msg.get("intent")
            if last_list_intent in ("list_by_status", "history", "history_counts", "list_inbox", "list_suppliers", "listar_facturas", "totals"):
                break
    
    if not last_assistant_msg:
        return {
            "intent": "context_related",
            "message": "No tengo contexto previo. Decime que queres saber y te ayudo.",
            "data": {}
        }
    
    # Extraer el ultimo item de la respuesta
    lines = last_assistant_msg.split("\n")
    
    # Buscar lineas que parezcan items (contienen $ o IDs de factura/proveedor)
    items = []
    for line in lines:
        if ("$" in line or "FC-" in line or "SUP" in line) and ("-" in line or ":" in line):
            items.append(line.strip())
    
    if items:
        # El primer item es el mas reciente (orden DESC)
        return {
            "intent": "context_related",
            "message": f"La ultima es: {items[0]}",
            "data": {"last_item": items[0], "items": items}
        }
    
    # Si no pudimos extraer items, responder con el mensaje original resumido
    summary = last_assistant_msg[:300] + ("..." if len(last_assistant_msg) > 300 else "")
    return {
        "intent": "context_related",
        "message": f"La ultima que liste fue: {summary}",
        "data": {"last_message": last_assistant_msg}
    }


def handle_list_suppliers() -> dict:
    """Lista todos los proveedores."""
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get("http://localhost:8001/suppliers")
            if r.status_code == 200:
                suppliers = r.json()
                lines_out = ["Proveedores (" + str(len(suppliers)) + " total):"]
                for s in suppliers[:20]:
                    status = "ACTIVO" if s.get("status") == "ACTIVE" else "INACTIVO"
                    lines_out.append("- " + s['supplier_id'] + " - " + s['name'] + " (" + status + ")")
                return {"intent": "list_suppliers", "message": "\n".join(lines_out), "data": {}}
    except:
        pass
    return {"intent": "list_suppliers", "message": "Error al obtener proveedores", "data": {}}


def handle_supplier_info(entities: dict) -> dict:
    """Muestra info de un proveedor."""
    import re
    sid = entities.get("supplier_id")
    raw = entities.get("raw_message", "")
    
    if not sid:
        match = re.search(r"\bSUP\d{3}\b", raw)
        if match:
            sid = match.group(0)
    
    if not sid:
        return {"intent": "supplier_info", "message": "Decime que proveedor. Ejemplo: info de SUP001", "data": {}}
    
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get("http://localhost:8001/suppliers/" + sid)
            if r.status_code == 200:
                s = r.json()
                status = "ACTIVO" if s.get("status") == "ACTIVE" else "INACTIVO"
                msg = "Proveedor: " + s['name'] + "\nID: " + s['supplier_id'] + "\nEstado: " + status
                return {"intent": "supplier_info", "message": msg, "data": {}}
            return {"intent": "supplier_info", "message": "No existe el proveedor " + sid, "data": {}}
    except:
        return {"intent": "supplier_info", "message": "Error al consultar proveedor", "data": {}}


def handle_listar_facturas(message: str = "") -> dict:
    """Lista todas las facturas."""
    if not settings.payments_db.exists():
        return {"intent": "listar_facturas", "message": "No hay datos aun.", "data": {}}
    
    with sqlite3.connect(str(settings.payments_db)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM payments ORDER BY id DESC LIMIT 50").fetchall()
    
    items = [dict(r) for r in rows]
    
    if not items:
        return {"intent": "listar_facturas", "message": "No hay facturas registradas.", "data": {}}
    
    lines_out = ["Todas las facturas (" + str(len(items)) + " total):"]
    for item in items[:15]:
        status_icon = {"APPROVED": "[OK]", "REJECTED": "[X]", "ESCALATED": "[!]"}.get(item.get('decision', ''), "[-]")
        lines_out.append(status_icon + " " + str(item.get('invoice_id', '?')) + " | " + str(item.get('supplier_id', '?')) + " | $" + f"{item.get('amount', 0):,.2f}")
    
    return {"intent": "listar_facturas", "message": "\n".join(lines_out), "data": {"items": items}}


def handle_list_inbox() -> dict:
    files = sorted(settings.inbox_dir.glob("*"))
    files = [f for f in files if f.is_file() and f.suffix.lower() in {".json", ".txt"}]
    items = []
    for f in files:
        try:
            inv = parse_invoice_file(f)
            items.append({
                "filename": f.name,
                "size": f.stat().st_size,
                "invoice_id": (inv or {}).get("invoice_id", "?"),
                "supplier_id": (inv or {}).get("supplier_id", "?"),
                "amount": (inv or {}).get("amount", 0),
                "invoice_date": (inv or {}).get("invoice_date", "?"),
            })
        except Exception:
            items.append({"filename": f.name, "size": f.stat().st_size, "error": True})
    return {
        "intent": "list_inbox",
        "message": f"{len(items)} factura(s) en el inbox.",
        "data": {"items": items},
    }


def handle_history() -> dict:
    if not settings.payments_db.exists():
        return {"intent": "history", "message": "Sin historial aún.", "data": {"items": []}}
    with sqlite3.connect(str(settings.payments_db)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM payments ORDER BY id DESC LIMIT 50").fetchall()
    return {"intent": "history", "message": f"{len(rows)} pago(s) registrado(s).",
            "data": {"items": [dict(r) for r in rows]}}


def handle_inbox_amounts() -> dict:
    list_result = handle_list_inbox()
    items = list_result.get("data", {}).get("items", [])
    amounts = []
    for i in items:
        try:
            amt = float(i.get("amount")) if i.get("amount") is not None else 0.0
        except (TypeError, ValueError):
            amt = 0.0
        amounts.append({
            "filename": i.get("filename"),
            "invoice_id": i.get("invoice_id"),
            "supplier_id": i.get("supplier_id"),
            "amount": amt,
        })
    total = sum(a["amount"] for a in amounts)
    if not amounts:
        return {"intent": "inbox_amounts",
                "message": "El inbox está vacío, no hay montos para mostrar.",
                "data": {"items": [], "total": 0, "count": 0}}
    sample = amounts[:5]
    lines = [f"• {a['invoice_id']} ({a['supplier_id']}): ${a['amount']:,.2f}" for a in sample]
    more = f"\n... y {len(amounts) - 5} más." if len(amounts) > 5 else ""
    msg = f"💰 Montos del inbox ({len(amounts)} factura(s), total **${total:,.2f}**):\n" + "\n".join(lines) + more
    return {"intent": "inbox_amounts", "message": msg,
            "data": {"items": amounts, "total": total, "count": len(amounts)}}


def handle_history_amounts() -> dict:
    history = handle_history()
    items = history.get("data", {}).get("items", [])
    if not items:
        return {"intent": "history_amounts", "message": "Sin historial de pagos aún.",
                "data": {"items": [], "total": 0}}
    amounts = []
    for i in items:
        amounts.append({
            "invoice_id": i.get("invoice_id"),
            "supplier_id": i.get("supplier_id"),
            "amount": float(i.get("amount") or 0),
            "decision": i.get("decision"),
        })
    total = sum(a["amount"] for a in amounts)
    total_approved = sum(a["amount"] for a in amounts if a.get("decision") == "APPROVED")
    msg = (f"💰 Montos del historial ({len(amounts)} factura(s)):\n"
           f"• Total facturado: **${total:,.2f}**\n"
           f"• Aprobado: **${total_approved:,.2f}**")
    return {"intent": "history_amounts", "message": msg,
            "data": {"items": amounts, "total": total, "total_approved": total_approved}}


def handle_totals() -> dict:
    if not settings.payments_db.exists():
        return {"intent": "totals", "message": "No hay datos aún.", "data": {}}
    with sqlite3.connect(str(settings.payments_db)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT decision, COUNT(*) as count, SUM(amount) as total
            FROM payments GROUP BY decision
        """).fetchall()
    breakdown = {r["decision"]: {"count": r["count"], "total": r["total"] or 0} for r in rows}
    grand_total = sum((r["total"] or 0) for r in rows)
    grand_count = sum(r["count"] for r in rows)
    msg_lines = ["📊 Totales generales del sistema:"]
    for d in ("APPROVED", "REJECTED", "ESCALATED"):
        if d in breakdown:
            info = breakdown[d]
            msg_lines.append(f"• {d}: {info['count']} factura(s), ${info['total']:,.2f}")
    msg_lines.append(f"\n**Total facturado: ${grand_total:,.2f}** en {grand_count} factura(s)")
    return {"intent": "totals", "message": "\n".join(msg_lines),
            "data": {"breakdown": breakdown, "grand_total": grand_total, "grand_count": grand_count}}


def handle_summary() -> dict:
    inbox = handle_list_inbox()
    history = handle_history()
    totals = handle_totals()
    return {
        "intent": "summary",
        "message": (
            f"📋 Resumen del sistema:\n"
            f"• 📥 Inbox: {len(inbox['data']['items'])} factura(s) pendiente(s)\n"
            f"• 📜 Historial: {len(history['data']['items'])} pago(s) registrado(s)\n"
            f"• 💰 Total facturado: ${totals['data'].get('grand_total', 0):,.2f}\n\n"
            f"Tip: preguntame 'cuánto suman las facturas' o 'mostrame el historial'."
        ),
        "data": {"inbox": inbox["data"], "history": history["data"], "totals": totals["data"]},
    }


def handle_help() -> dict:
    return {
        "intent": "help",
        "message": (
            "🤖 **Asistente IA - GI**\n\n"
            "📊 **Consultas:**\n"
            "• 'me podras decir los montos' → montos del inbox\n"
            "• 'mostrame el historial' → pagos registrados\n"
            "• 'cuánto suman las facturas' → totales por estado\n"
            "• 'resumen' → overview del sistema\n\n"
            "⚙️ **Acciones:**\n"
            "• 'procesá todo el inbox' → procesa pendientes\n"
            "• 'cambia el límite de SUP001 a 200000' → modifica contrato\n"
            "• 'desactivá SUP003' → cambia estado\n"
            "• 'cambiar email de SUP001 a x@y.com' → edita proveedor\n"
        ),
        "data": {},
    }


def _process_single_file(path: Path) -> dict:
    invoice = parse_invoice_file(path)
    if not invoice:
        new_path = move_file(path, settings.rejected_dir)
        return {"filename": path.name, "error": "No se pudo parsear", "moved_to": str(new_path)}
    try:
        result = process_invoice(invoice, source_file=str(path))
        result["filename"] = path.name
        if result.get("decision") in {"APPROVED", "REJECTED", "ESCALATED"}:
            new_path = move_file(path, settings.processed_dir)
            result["moved_to"] = str(new_path)
        return result
    except Exception as e:
        new_path = move_file(path, settings.rejected_dir)
        return {"filename": path.name, "error": str(e), "moved_to": str(new_path)}


# ----------------------------------------------------------------------
# Endpoint principal
# ----------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
def chat(msg: ChatMessage):
    # 1. Crear o recuperar sesión
    session_id = get_or_create_session(msg.session_id)
    save_message(session_id, "user", msg.message)

    # 2. Extraer entities (con contexto)
    entities = extract_entities(msg.message, session_id)
    entities["raw_message"] = msg.message

    # 3. Detectar confirmaciones
    lower_msg = msg.message.strip().lower()
    if lower_msg in ("sí", "si", "yes", "confirmo", "dale", "ok", "confirmar"):
        # Buscar la última accion que requeria confirmacion
        ctx = load_context(session_id, n=5)
        for prev in reversed(ctx):
            if prev["role"] == "assistant" and prev.get("intent") == "delete_supplier":
                # Re-procesar el mensaje anterior
                entities_action = {"supplier_id": prev.get("content", "").split("proveedor ")[1].split("?")[0] if "proveedor" in prev.get("content", "") else None}
                if entities_action.get("supplier_id"):
                    result = action_delete_supplier_confirmed(entities_action)
                    save_message(session_id, "assistant", result.get("message", ""), result.get("intent"))
                    return ChatResponse(**result, session_id=session_id)
        # Si no encontro nada, devolver error
        return ChatResponse(
            intent="confirmation",
            message="No tengo ninguna acción pendiente de confirmar.",
            session_id=session_id,
        )

    if lower_msg in ("no", "cancelar", "cancel"):
        return ChatResponse(
            intent="cancelled",
            message="❌ Acción cancelada.",
            session_id=session_id,
        )

    # 4. Parsear intent
    intent, param = parse_intent(msg.message)

    # 5. Dispatcher: acciones (write) vs consultas (read)
    if intent == "set_contract_limit":
        result = action_set_contract_limit(entities)
    elif intent == "set_contract_mode":
        result = action_set_contract_mode(entities)
    elif intent == "activate_supplier":
        result = action_activate_supplier(entities)
    elif intent == "deactivate_supplier":
        result = action_deactivate_supplier(entities)
    elif intent == "update_supplier_field":
        result = action_update_supplier_field(entities)
    elif intent == "delete_supplier":
        result = action_delete_supplier(entities)
    elif intent == "memory_action":
        # FIX SPEC_013: usar el último intent de la sesión
        ctx = load_context(session_id, n=3)
        last_intent = None
        for msg in reversed(ctx):
            if msg.get("intent"):
                last_intent = msg["intent"]
                break
        # Si el último intent era desactivar, desactivar; si activar, etc
        if last_intent == "deactivate_supplier":
            result = action_deactivate_supplier(entities)
        elif last_intent == "activate_supplier":
            result = action_activate_supplier(entities)
        elif last_intent == "set_contract_limit":
            result = action_set_contract_limit(entities)
        elif last_intent == "update_supplier_field":
            result = action_update_supplier_field(entities)
        else:
            result = {"intent": "memory_action", "ok": False,
                       "error": f"No se puede inferir la acción. Último intent: {last_intent}"}
    elif intent == "process_all":
        result = handle_process_all()
    elif intent == "process_one":
        invoice_id = entities.get("invoice_id") or param
        result = handle_process_one(invoice_id)
    elif intent == "process_path":
        result = handle_process_path(param)
    elif intent == "list_by_status":
        result = handle_list_by_status(msg.message)
    elif intent == "listar_facturas":
        result = handle_listar_facturas(msg.message)
    elif intent == "context_related":
        result = handle_context_related(session_id)
    elif intent == "list_suppliers":
        result = handle_list_suppliers()
    elif intent == "supplier_info":
        result = handle_supplier_info(entities)
    elif intent == "list_inbox":
        result = handle_list_inbox()
    elif intent == "history":
        result = handle_history()
    elif intent == "inbox_amounts":
        result = handle_inbox_amounts()
    elif intent == "history_amounts":
        result = handle_history_amounts()
    elif intent == "totals":
        result = handle_totals()
    elif intent == "summary":
        result = handle_summary()
    elif intent == "help":
        result = handle_help()
    else:
        result = {
            "intent": "unknown",
            "message": (
                "🤖 Soy tu Asistente IA. No entendí esa instrucción.\n\n"
                "Probá con:\n"
                "  • 'me podras decir los montos'\n"
                "  • 'qué facturas hay en el inbox'\n"
                "  • 'mostrame el historial'\n"
                "  • 'resumen' / 'ayuda'\n"
                "  • 'cambia el límite de SUP001 a 200000'\n"
            ),
        }

    # 6. Guardar respuesta
    save_message(session_id, "assistant", result.get("message", ""), result.get("intent"))

    return ChatResponse(**result, session_id=session_id)


# ----------------------------------------------------------------------
# Endpoints de gestión de sesiones
# ----------------------------------------------------------------------

@router.get("/sessions")
def list_sessions(limit: int = 20):
    with get_chat_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, last_active_at FROM sessions "
            "ORDER BY last_active_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/sessions")
def create_session(title: str = "Nueva conversación"):
    new_id = f"chat-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with get_chat_conn() as conn:
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?)",
            (new_id, title, now, now),
        )
        conn.commit()
    return {"id": new_id, "title": title, "created_at": now, "last_active_at": now}


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    with get_chat_conn() as conn:
        sess = conn.execute(
            "SELECT id, title, created_at, last_active_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if not sess:
            raise HTTPException(404, f"Sesión {session_id} no encontrada")
        msgs = conn.execute(
            "SELECT id, role, content, intent, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return {
        "session": dict(sess),
        "messages": [dict(m) for m in msgs],
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    with get_chat_conn() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, f"Sesión {session_id} no encontrada")
    return {"ok": True, "deleted": session_id}
