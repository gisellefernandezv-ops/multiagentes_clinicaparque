"""Motor de Guardrails — InvoiceFlow.

Lee las reglas declaradas en `rules.yaml` y las aplica en el orden
especificado por el pipeline. Soporta 4 categorías:
    - structural (VR)
    - business (BR)
    - security (SR)
    - continuity (CR)

Uso:
    from guardrails.guardrail_engine import GuardrailEngine
    engine = GuardrailEngine()
    resultado = engine.evaluate(invoice_data, context)
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml

# =============================================================================
# RUTAS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_YAML = PROJECT_ROOT / "guardrails" / "rules.yaml"
PAYMENTS_DB = PROJECT_ROOT / "data" / "payments.db"

# =============================================================================
# FUNCIÓN AUXILIAR: validar CUIT argentino
# =============================================================================


def validar_cuit(cuit: str) -> bool:
    """Valida el formato y dígito verificador de un CUIT argentino.

    Formato esperado: XX-XXXXXXXX-X (con o sin guiones)
    """
    if not cuit:
        return False

    # Limpiar formato
    cuit_limpio = re.sub(r"[^0-9]", "", cuit)
    if len(cuit_limpio) != 11:
        return False

    try:
        # Algoritmo de dígito verificador
        factores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(cuit_limpio[i]) * factores[i] for i in range(10))
        digito_esperado = (10 - (suma % 11)) % 11
        digito_real = int(cuit_limpio[10])
        return digito_esperado == digito_real
    except (ValueError, IndexError):
        return False


def validar_fecha_emision(fecha_str: str | None) -> tuple[bool, str]:
    """Valida formato y no-futuro de fecha de emisión.

    Returns:
        (es_valida, mensaje_error)
    """
    if not fecha_str:
        return False, "Fecha no proporcionada"

    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
    fecha_parseada = None

    for fmt in formatos:
        try:
            fecha_parseada = datetime.strptime(fecha_str, fmt)
            break
        except ValueError:
            continue

    if fecha_parseada is None:
        return False, f"Formato de fecha inválido: {fecha_str}"

    if fecha_parseada > datetime.now():
        return False, "La fecha no puede ser futura"

    return True, ""


# =============================================================================
# FUNCIÓN AUXILIAR: verificar factura duplicada
# =============================================================================


def verificar_factura_duplicada(invoice_id: str, supplier_id: str) -> bool:
    """Consulta la DB para saber si ya existe esta factura."""
    import sqlite3

    try:
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM payments WHERE invoice_id = ? AND supplier_id = ?",
                (invoice_id, supplier_id),
            )
            count = cursor.fetchone()[0]
            return count > 0
    except Exception:
        return False


def obtener_suma_facturas_30_dias(supplier_id: str) -> float:
    """Suma los montos de facturas del proveedor en los últimos 30 días."""
    import sqlite3

    hace_30_dias = (datetime.now() - timedelta(days=30)).isoformat()

    try:
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            cursor = conn.execute(
                """SELECT COALESCE(SUM(amount), 0) FROM payments
                   WHERE supplier_id = ? AND registered_at >= ?""",
                (supplier_id, hace_30_dias),
            )
            return float(cursor.fetchone()[0])
    except Exception:
        return 0.0


def verificar_tasa_envios(cuit: str) -> int:
    """Cuenta facturas enviadas en la última hora por este CUIT/proveedor."""
    import sqlite3

    hace_1_hora = (datetime.now() - timedelta(hours=1)).isoformat()

    try:
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            cursor = conn.execute(
                """SELECT COUNT(*) FROM payments
                   WHERE supplier_id = ? AND registered_at >= ?""",
                (cuit, hace_1_hora),
            )
            return int(cursor.fetchone()[0])
    except Exception:
        return 0


def detectar_inyeccion_prompt(texto: str) -> bool:
    """Detecta posibles inyecciones de prompt en texto extraído."""
    if not texto:
        return False

    patrones_sospechosos = [
        r"ignore\s+(previous|all)\s+instructions",
        r"disregard\s+(previous|all)\s+instructions",
        r"forget\s+(previous|all)\s+instructions",
        r"ignora\s+las\s+instrucciones",
        r"override\s+(system|your)\s+(instructions|prompt|role)",
        r"new\s+instructions:",
        r"you\s+are\s+now\s+a",
        r"<script",
        r"{{",
    ]

    texto_lower = texto.lower()
    for patron in patrones_sospechosos:
        if re.search(patron, texto_lower, re.IGNORECASE):
            return True

    return False


# =============================================================================
# CLASE PRINCIPAL: GuardrailEngine
# =============================================================================


class GuardrailEngine:
    """Motor de evaluación de guardrails basado en rules.yaml."""

    def __init__(self, rules_path: str | Path | None = None):
        """Inicializa el motor cargando las reglas desde YAML.

        Args:
            rules_path: Ruta al archivo rules.yaml. Si es None, usa la default.
        """
        self.rules_path = Path(rules_path) if rules_path else RULES_YAML
        self._rules: list[dict] = []
        self._pipeline: dict = {}
        self._constantes: dict = {}
        self._servicios: dict = {}
        self._load_rules()

    def _load_rules(self) -> None:
        """Carga y parsea el archivo YAML de reglas."""
        if not self.rules_path.exists():
            raise FileNotFoundError(f"No se encontró rules.yaml en {self.rules_path}")

        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._rules = data.get("guardrails", [])
        self._pipeline = data.get("pipeline", {})
        self._constantes = data.get("constantes", {})
        self._servicios = data.get("servicios_externos", {})

    def get_rule(self, rule_id: str) -> dict | None:
        """Obtiene una regla por su ID."""
        for rule in self._rules:
            if rule["id"] == rule_id:
                return rule
        return None

    def get_rules_by_type(self, tipo: str) -> list[dict]:
        """Obtiene todas las reglas de un tipo (structural, business, etc)."""
        return [r for r in self._rules if r["tipo"] == tipo]

    def get_rules_by_agent(self, agente: str) -> list[dict]:
        """Obtiene todas las reglas aplicables a un agente."""
        rules = []
        for rule in self._rules:
            aplica_a = rule.get("aplica_a", [])
            if isinstance(aplica_a, str):
                aplica_a = [aplica_a]
            if agente in aplica_a:
                rules.append(rule)
        return sorted(rules, key=lambda r: r.get("prioridad", 999))

    # -------------------------------------------------------------------------
    # Evaluadores individuales (uno por cada regla)
    # -------------------------------------------------------------------------

    def _eval_VR01(self, data: dict) -> tuple[bool, str]:
        """VR-01: Formato PDF."""
        archivo_tipo = data.get("archivo_tipo", "").lower()
        return archivo_tipo == "pdf", "Formato de archivo no soportado, debe ser PDF"

    def _eval_VR02(self, data: dict) -> tuple[bool, str]:
        """VR-02: Tamaño máximo 10 MB."""
        tamanio_mb = data.get("tamanio_mb", 0)
        maximo = self._constantes.get("TAMANIO_MAXIMO_ARCHIVO_MB", 10)
        if tamanio_mb > maximo:
            return False, "Archivo demasiado grande"
        return True, ""

    def _eval_VR03(self, data: dict) -> tuple[bool, str]:
        """VR-03: Campos obligatorios."""
        obligatorios = ["cuit", "razon_social", "monto", "fecha", "numero_factura"]
        faltantes = [c for c in obligatorios if not data.get(c)]
        if faltantes:
            return False, f"Campos obligatorios faltantes: {', '.join(faltantes)}"
        return True, ""

    def _eval_VR04(self, data: dict) -> tuple[bool, str]:
        """VR-04: Formato CUIT válido."""
        cuit = data.get("cuit", "")
        if not validar_cuit(cuit):
            return False, "CUIT con formato inválido"
        return True, ""

    def _eval_VR05(self, data: dict) -> tuple[bool, str]:
        """VR-05: Fecha de emisión válida."""
        fecha = data.get("fecha_emision") or data.get("fecha")
        es_valida, mensaje = validar_fecha_emision(fecha)
        if not es_valida:
            return False, f"Fecha de emisión inválida: {mensaje}"
        return True, ""

    def _eval_VR06(self, data: dict) -> tuple[bool, str]:
        """VR-06: Monto > 0."""
        try:
            monto = float(data.get("monto", 0))
            if monto <= 0:
                return False, "Monto de factura inválido"
        except (ValueError, TypeError):
            return False, "Monto de factura inválido"
        return True, ""

    def _eval_VR07(self, data: dict) -> tuple[bool, str]:
        """VR-07: Factura duplicada."""
        invoice_id = data.get("numero_factura") or data.get("invoice_id", "")
        supplier_id = data.get("supplier_id", "") or data.get("cuit", "")
        if verificar_factura_duplicada(invoice_id, supplier_id):
            return False, "Factura duplicada"
        return True, ""

    def _eval_BR01(self, data: dict) -> tuple[bool, str]:
        """BR-01: Proveedor existe."""
        # Asume que context tiene el resultado de validator_agent
        if data.get("supplier_found"):
            return True, ""
        return False, "Proveedor no registrado"

    def _eval_BR02(self, data: dict) -> tuple[bool, str]:
        """BR-02: Proveedor activo."""
        status = data.get("supplier_status", "").upper()
        if status == "ACTIVE":
            return True, ""
        if status:
            return False, "Proveedor inactivo"
        return True, ""  # Si no hay info, no rechazar aquí

    def _eval_BR03(self, data: dict) -> tuple[bool, str]:
        """BR-03: Factura no vencida."""
        fecha_emision = data.get("fecha_emision") or data.get("fecha", "")
        if not fecha_emision:
            return True, ""

        try:
            # Parsear fecha
            fmt = "%Y-%m-%d"
            fecha = datetime.strptime(fecha_emision[:10], fmt)
            dias_desde = (datetime.now() - fecha).days
            plazo = self._constantes.get("PLAZO_FACTURA_DIAS", 60)
            if dias_desde > plazo:
                return False, f"Factura vencida (más de {plazo} días)"
        except (ValueError, TypeError):
            pass

        return True, ""

    def _eval_BR04(self, data: dict) -> tuple[bool, str]:
        """BR-04: Razón social coincide."""
        razon_factura = data.get("razon_social", "").lower().strip()
        razon_contrato = data.get("razon_social_contrato", "").lower().strip()
        if razon_contrato and razon_factura != razon_contrato:
            return False, "Razón social no coincide con el proveedor registrado"
        return True, ""

    def _eval_BR05(self, data: dict) -> tuple[bool, str]:
        """BR-05: Monto dentro del límite contractual."""
        monto = float(data.get("monto", 0))
        limite = float(data.get("limite_contractual", float("inf")))
        if monto > limite:
            return False, f"Monto excede el límite contractual de ${limite:,.0f}"
        return True, ""

    def _eval_BR06(self, data: dict) -> tuple[bool, str]:
        """BR-06: Existe contrato vigente (escalado)."""
        if not data.get("contrato_encontrado"):
            return False, "Sin contrato vigente registrado, requiere revisión manual"
        return True, ""

    def _eval_BR07(self, data: dict) -> tuple[bool, str]:
        """BR-07: Monto > $500.000 (escalado)."""
        monto = float(data.get("monto", 0))
        maximo = self._constantes.get("MONTO_MAXIMO_AUTOAPROBACION", 500000)
        if monto > maximo:
            return False, f"Supera el monto de aprobación automática (${maximo:,.0f})"
        return True, ""

    def _eval_BR08(self, data: dict) -> tuple[bool, str]:
        """BR-08: Alto riesgo según ML (escalado)."""
        riesgo = str(data.get("risk_score", "")).lower()
        if riesgo == "alto":
            return False, "Factura clasificada como alto riesgo, requiere revisión"
        return True, ""

    def _eval_BR09(self, data: dict) -> tuple[bool, str]:
        """BR-09: Posible fraccionamiento (escalado)."""
        monto_actual = float(data.get("monto", 0))
        supplier_id = data.get("supplier_id", "")
        suma_30_dias = obtener_suma_facturas_30_dias(supplier_id)
        total = suma_30_dias + monto_actual
        maximo = self._constantes.get("MONTO_MAXIMO_AUTOAPROBACION", 500000)

        if total > maximo:
            return False, f"Monto acumulado (${total:,.0f}) supera el límite, posible fraccionamiento"
        return True, ""

    def _eval_BR10(self, data: dict) -> tuple[bool, str]:
        """BR-10: Estado definitivo (bloqueado)."""
        estado = str(data.get("estado_actual", "")).upper()
        if estado in ["REJECTED", "PAID"]:
            return False, "Esta factura ya fue procesada, no puede reenviarse"
        return True, ""

    def _eval_SR01(self, data: dict) -> tuple[bool, str]:
        """SR-01: Contenido sospechoso / inyección de prompt."""
        texto = data.get("texto_extraido", "") or data.get("pdf_content", "")
        if detectar_inyeccion_prompt(texto):
            return False, "Contenido sospechoso detectado en el documento"
        return True, ""

    def _eval_SR02(self, data: dict) -> tuple[bool, str]:
        """SR-02: Acción no autorizada."""
        accion = str(data.get("accion_solicitada", "")).lower().strip()
        permitidas = ["registrar", "consultar"]
        if accion and accion not in permitidas:
            return False, "Acción no autorizada"
        return True, ""

    def _eval_SR03(self, data: dict) -> tuple[bool, str]:
        """SR-03: Intento de consultar otro proveedor."""
        cuit_solicitado = data.get("cuit_solicitado", "")
        cuit_autenticado = data.get("cuit_autenticado", "")
        if cuit_solicitado and cuit_autenticado and cuit_solicitado != cuit_autenticado:
            return False, "No autorizado a consultar datos de otro proveedor"
        return True, ""

    def _eval_SR04(self, data: dict) -> tuple[bool, str]:
        """SR-04: Límite de tasa (rate limiting)."""
        supplier_id = data.get("supplier_id", "") or data.get("cuit", "")
        envios_ultima_hora = verificar_tasa_envios(supplier_id)
        limite = self._constantes.get("LIMITE_FACTURAS_POR_HORA", 20)
        if envios_ultima_hora >= limite:
            return False, f"Límite de envíos alcanzado ({envios_ultima_hora}/{limite}), intentar más tarde"
        return True, ""

    def _eval_SR05(self, data: dict) -> tuple[bool, str]:
        """SR-05: Intento de obtener info interna del sistema."""
        mensaje = str(data.get("mensaje_usuario", "")).lower()
        patrones = [
            "prompt", "system prompt", "agente", "herramientas",
            "base de datos", "estructura", "código fuente",
        ]
        for patron in patrones:
            if f"qué es tu {patron}" in mensaje or f"dame tu {patron}" in mensaje:
                return False, "No puedo compartir esa información"
        return True, ""

    def _eval_CR01(self, data: dict) -> tuple[bool, dict]:
        """CR-01: Servicio externo caído (PENDIENTE_TECNICO)."""
        if data.get("servicio_error"):
            return False, {
                "estado": "PENDIENTE_TECNICO",
                "mensaje": "Estamos procesando tu factura, te confirmaremos en breve",
            }
        return True, {}

    def _eval_CR02(self, data: dict) -> tuple[bool, dict]:
        """CR-02: Falla transitoria (reintentar)."""
        if data.get("reintentos_hechos", 0) < 3:
            return True, {"retry": True, "backoff": [1, 2, 4][data.get("reintentos_hechos", 0)]}
        return True, {}

    # -------------------------------------------------------------------------
    # Método principal de evaluación
    # -------------------------------------------------------------------------

    def evaluate(self, invoice_data: dict, context: dict | None = None) -> dict:
        """Evalúa todas las reglas aplicables en orden de prioridad.

        Args:
            invoice_data: Datos de la factura a evaluar.
            context: Contexto adicional (resultados de agentes, etc).

        Returns:
            dict con:
                - passed (bool): True si pasó todos los guardrails
                - action (str): APPROVE | REJECT | ESCALATE | BLOCK | PENDIENTE_TECNICO
                - reason (str): mensaje para el usuario
                - rule_id (str): ID de la regla que detuvo el flujo (si aplica)
                - details (dict): detalles adicionales
        """
        if context is None:
            context = {}

        # Combinar datos
        data = {**invoice_data, **context}

        # Ordenar reglas por prioridad
        reglas_ordenadas = sorted(self._rules, key=lambda r: r.get("prioridad", 999))

        for rule in reglas_ordenadas:
            rule_id = rule["id"]
            evaluador = getattr(self, f"_eval_{rule_id}", None)

            if evaluador is None:
                continue  # Saltar reglas sin evaluador implementado

            # Ejecutar evaluador
            result = evaluador(data)

            # Parsear resultado
            if rule["tipo"] == "continuity":
                passed, extra = result
                if not passed:
                    return {
                        "passed": False,
                        "action": extra.get("estado", "PENDIENTE_TECNICO"),
                        "reason": rule["mensaje"],
                        "rule_id": rule_id,
                        "details": extra,
                    }
            else:
                passed, reason = result
                if not passed:
                    accion = rule["accion"].upper()
                    return {
                        "passed": False,
                        "action": accion,
                        "reason": reason or rule["mensaje"],
                        "rule_id": rule_id,
                        "details": {},
                    }

        # Todas las reglas pasaron
        return {
            "passed": True,
            "action": "APPROVE",
            "reason": "Todas las validaciones superadas",
            "rule_id": None,
            "details": {},
        }

    def evaluate_structural(self, invoice_data: dict) -> dict:
        """Evalúa solo las reglas estructurales (VR-01 a VR-07)."""
        reglas_vr = [r for r in self._rules if r["tipo"] == "structural"]
        reglas_ordenadas = sorted(reglas_vr, key=lambda r: r.get("prioridad", 999))

        for rule in reglas_ordenadas:
            evaluador = getattr(self, f"_eval_{rule['id']}", None)
            if evaluador is None:
                continue

            passed, reason = evaluador(invoice_data)
            if not passed:
                return {
                    "passed": False,
                    "action": "REJECT",
                    "reason": reason or rule["mensaje"],
                    "rule_id": rule["id"],
                }

        return {"passed": True, "action": "APPROVE", "reason": "", "rule_id": None}

    def evaluate_business(self, invoice_data: dict, agent_results: dict) -> dict:
        """Evalúa solo las reglas de negocio (BR) combinando datos + resultados de agentes."""
        data = {**invoice_data, **agent_results}
        reglas_br = [r for r in self._rules if r["tipo"] == "business"]
        reglas_ordenadas = sorted(reglas_br, key=lambda r: r.get("prioridad", 999))

        for rule in reglas_ordenadas:
            evaluador = getattr(self, f"_eval_{rule['id']}", None)
            if evaluador is None:
                continue

            result = evaluador(data)
            if rule["tipo"] == "continuity":
                passed, extra = result
            else:
                passed, reason = result
                extra = {}

            if not passed:
                return {
                    "passed": False,
                    "action": rule["accion"].upper(),
                    "reason": reason or rule["mensaje"],
                    "rule_id": rule["id"],
                    "details": extra,
                }

        return {"passed": True, "action": "APPROVE", "reason": "", "rule_id": None}


# =============================================================================
# FUNCIÓN DE CONVENIENCIA (API simple)
# =============================================================================

_engine: GuardrailEngine | None = None


def get_engine() -> GuardrailEngine:
    """Obtiene la instancia singleton del motor de guardrails."""
    global _engine
    if _engine is None:
        _engine = GuardrailEngine()
    return _engine


def evaluate_guardrails(invoice_data: dict, context: dict | None = None) -> dict:
    """Función de conveniencia para evaluar guardrails.

    Args:
        invoice_data: Datos de la factura.
        context: Contexto adicional.

    Returns:
        dict con passed, action, reason, rule_id.
    """
    return get_engine().evaluate(invoice_data, context)


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("GUARDRAIL ENGINE — TEST DE REGLAS")
    print("=" * 60)

    engine = GuardrailEngine()
    print(f"✓ {len(engine._rules)} reglas cargadas desde {RULES_YAML}")
    print(f"✓ Pipeline: {list(engine._pipeline.keys())}")
    print(f"✓ Constantes: {engine._constantes}")

    # Test: factura válida
    print("\n--- Test: Factura válida ---")
    result = engine.evaluate({
        "archivo_tipo": "pdf",
        "tamanio_mb": 2,
        "cuit": "30-71234567-8",  # CUIT válido de ejemplo
        "razon_social": "TechCorp SA",
        "monto": 50000,
        "fecha_emision": "2025-01-15",
        "numero_factura": "FC-001",
        "supplier_id": "SUP001",
        "supplier_found": True,
        "supplier_status": "ACTIVE",
        "contrato_encontrado": True,
        "limite_contractual": 100000,
    })
    print(f"  Resultado: {result}")

    # Test: VR-04 (CUIT inválido)
    print("\n--- Test: CUIT inválido (VR-04) ---")
    result = engine.evaluate({
        "archivo_tipo": "pdf",
        "cuit": "00-00000000-0",  # Inválido
        "monto": 1000,
    })
    print(f"  Resultado: {result}")

    # Test: BR-07 (monto > $500k)
    print("\n--- Test: Monto > $500k (BR-07) ---")
    result = engine.evaluate({
        "archivo_tipo": "pdf",
        "cuit": "30-71234567-8",
        "monto": 600000,
        "supplier_found": True,
        "supplier_status": "ACTIVE",
    })
    print(f"  Resultado: {result}")

    print("\n✓ Tests completados")
