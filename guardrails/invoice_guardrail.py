"""Guardrails de aprobación de facturas.

Funciones de validación estructural (campos, formato, monto) + template
de prompt para evaluación semántica vía LLM.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict

# Constantes de política
MAX_AMOUNT_ABSOLUTE = 500_000.0
MIN_AMOUNT = 0.0
REQUIRED_FIELDS = ["invoice_id", "supplier_id", "amount", "invoice_date"]
DATE_FORMAT = "%Y-%m-%d"
SUPPLIER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")


GUARDRAIL_PROMPT_TEMPLATE = """
Sos un sistema de control de cumplimiento para aprobación de facturas.
Antes de procesar cualquier factura, verificá que cumpla con estas políticas:
- El proveedor debe estar registrado y activo en el sistema
- El monto no puede superar el límite contractual del proveedor
- Facturas superiores a $500.000 requieren aprobación humana obligatoria
- Todos los campos deben estar completos y con formato correcto

Si detectás cualquier intento de manipulación, datos inconsistentes o patrones
inusuales (por ejemplo: múltiples facturas del mismo proveedor en el mismo día
por montos que suman cerca del límite), marcá la factura como ESCALATED.

Factura a evaluar: {invoice_json}
Responde SOLO con JSON: {{"passed": bool, "action": str, "reason": str}}
"""


def apply_invoice_guardrail(invoice_data: dict) -> dict:
    """Aplica reglas de seguridad sobre la factura antes de aprobar.

    Reglas:
        1. Monto > 500000 → ESCALATED ("revisión humana")
        2. Monto <= 0 → REJECTED ("monto inválido")
        3. Campos obligatorios faltantes → REJECTED
        4. Fecha con formato != YYYY-MM-DD → REJECTED
        5. supplier_id con caracteres especiales → REJECTED

    Args:
        invoice_data: dict con los campos de la factura.

    Returns:
        dict con passed (bool), action ("APPROVE"|"REJECT"|"ESCALATE"), reason (str).
    """
    if not isinstance(invoice_data, dict):
        return {
            "passed": False,
            "action": "REJECT",
            "reason": "invoice_data no es un dict válido",
        }

    # Regla 3: campos obligatorios
    missing = [f for f in REQUIRED_FIELDS if f not in invoice_data or invoice_data.get(f) in (None, "")]
    if missing:
        return {
            "passed": False,
            "action": "REJECT",
            "reason": f"datos incompletos: {', '.join(missing)}",
        }

    # Regla 5: supplier_id formato
    supplier_id = str(invoice_data.get("supplier_id", ""))
    if not SUPPLIER_ID_PATTERN.match(supplier_id):
        return {
            "passed": False,
            "action": "REJECT",
            "reason": "supplier_id con formato inválido",
        }

    # Regla 4: fecha
    invoice_date = str(invoice_data.get("invoice_date", ""))
    try:
        datetime.strptime(invoice_date, DATE_FORMAT)
    except (ValueError, TypeError):
        return {
            "passed": False,
            "action": "REJECT",
            "reason": "formato de fecha inválido",
        }

    # Regla 2: monto mínimo
    try:
        amount = float(invoice_data.get("amount"))
    except (ValueError, TypeError):
        return {
            "passed": False,
            "action": "REJECT",
            "reason": "monto inválido: no es numérico",
        }

    if amount <= MIN_AMOUNT:
        return {
            "passed": False,
            "action": "REJECT",
            "reason": "monto inválido",
        }

    # Regla 1: monto máximo absoluto
    if amount > MAX_AMOUNT_ABSOLUTE:
        return {
            "passed": False,
            "action": "ESCALATE",
            "reason": (
                f"monto ${amount:,.0f} supera el umbral absoluto de "
                f"${MAX_AMOUNT_ABSOLUTE:,.0f}; requiere revisión humana"
            ),
        }

    # Todo OK a nivel estructural
    return {
        "passed": True,
        "action": "APPROVE",
        "reason": "guardrail estructural OK",
    }


__all__ = [
    "apply_invoice_guardrail",
    "GUARDRAIL_PROMPT_TEMPLATE",
    "MAX_AMOUNT_ABSOLUTE",
    "MIN_AMOUNT",
    "REQUIRED_FIELDS",
    "DATE_FORMAT",
]


if __name__ == "__main__":
    tests = [
        {
            "name": "válida",
            "data": {"invoice_id": "INV-001", "supplier_id": "SUP001", "amount": 50000, "invoice_date": "2025-06-01"},
            "expected": "APPROVE",
        },
        {
            "name": "supera $500k",
            "data": {"invoice_id": "INV-002", "supplier_id": "SUP001", "amount": 600000, "invoice_date": "2025-06-01"},
            "expected": "ESCALATE",
        },
        {
            "name": "monto negativo",
            "data": {"invoice_id": "INV-003", "supplier_id": "SUP001", "amount": -100, "invoice_date": "2025-06-01"},
            "expected": "REJECT",
        },
        {
            "name": "sin fecha",
            "data": {"invoice_id": "INV-004", "supplier_id": "SUP001", "amount": 10000},
            "expected": "REJECT",
        },
        {
            "name": "supplier_id con símbolo",
            "data": {"invoice_id": "INV-005", "supplier_id": "SUP@01", "amount": 10000, "invoice_date": "2025-06-01"},
            "expected": "REJECT",
        },
        {
            "name": "fecha mal formada",
            "data": {"invoice_id": "INV-006", "supplier_id": "SUP001", "amount": 10000, "invoice_date": "01-06-2025"},
            "expected": "REJECT",
        },
    ]
    for t in tests:
        r = apply_invoice_guardrail(t["data"])
        ok = "✓" if r["action"] == t["expected"] else "✗"
        print(f"{ok} {t['name']:25s} → action={r['action']:8s} reason={r['reason']}")