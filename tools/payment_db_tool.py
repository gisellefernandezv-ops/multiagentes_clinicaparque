"""Tool MCP — escritura en SQLite de pagos.

Crea automáticamente la tabla `payments` si no existe. Devuelve un
`confirmation_id` único para cada registro.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from google.adk.tools import ToolContext

# Path de la DB (relativo a la raíz del proyecto)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "payments.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    amount REAL NOT NULL,
    decision TEXT NOT NULL,
    rejection_reason TEXT,
    payment_status TEXT NOT NULL,
    confirmation_id TEXT NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_supplier ON payments(supplier_id);
"""


def _ensure_db():
    """Asegura que el directorio y la tabla existan."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def _generate_confirmation_id() -> str:
    """Genera un confirmation_id legible: PAY-XXXXXXXX (8 hex chars)."""
    return f"PAY-{uuid.uuid4().hex[:8].upper()}"


def register_payment_tool(
    invoice_id: str,
    supplier_id: str,
    amount: float,
    decision: str,
    rejection_reason: str = "",
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """Registra el resultado de la aprobación en la base de datos de pagos.

    Registra tanto facturas aprobadas como rechazadas. El estado de pago
    (`payment_status`) se infiere desde `decision`:
        - APPROVED → "PENDING_PAYMENT"
        - ESCALATED → "PENDING_HUMAN_REVIEW"
        - REJECTED → "REJECTED"

    Args:
        invoice_id: ID de la factura.
        supplier_id: ID del proveedor.
        amount: Monto de la factura.
        decision: APPROVED | REJECTED | ESCALATED.
        rejection_reason: Motivo (vacío si APPROVED).
        tool_context: ADK ToolContext (opcional, para logging/state).

    Returns:
        dict con success, confirmation_id, payment_status, registered_at.
    """
    # Validación mínima
    if not invoice_id or not supplier_id:
        return {
            "success": False,
            "confirmation_id": "",
            "payment_status": "ERROR",
            "registered_at": "",
            "error": "invoice_id y supplier_id son obligatorios",
        }

    decision_norm = (decision or "").upper().strip()
    if decision_norm not in {"APPROVED", "REJECTED", "ESCALATED"}:
        return {
            "success": False,
            "confirmation_id": "",
            "payment_status": "ERROR",
            "registered_at": "",
            "error": f"decision inválida: {decision!r}",
        }

    # Mapear decisión a estado de pago
    status_map = {
        "APPROVED": "PENDING_PAYMENT",
        "ESCALATED": "PENDING_HUMAN_REVIEW",
        "REJECTED": "REJECTED",
    }
    payment_status = status_map[decision_norm]

    confirmation_id = _generate_confirmation_id()
    registered_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    try:
        _ensure_db()
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                """
                INSERT INTO payments (
                    invoice_id, supplier_id, amount, decision,
                    rejection_reason, payment_status, confirmation_id, registered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    supplier_id,
                    float(amount),
                    decision_norm,
                    rejection_reason or "",
                    payment_status,
                    confirmation_id,
                    registered_at,
                ),
            )
            conn.commit()

        # Si tenemos tool_context, dejamos constancia en el state
        if tool_context is not None:
            try:
                tool_context.state.update(
                    {
                        "confirmation_id": confirmation_id,
                        "registered_at": registered_at,
                    }
                )
            except Exception:
                pass

        return {
            "success": True,
            "confirmation_id": confirmation_id,
            "payment_status": payment_status,
            "registered_at": registered_at,
            "error": "",
        }

    except Exception as e:
        return {
            "success": False,
            "confirmation_id": "",
            "payment_status": "ERROR",
            "registered_at": "",
            "error": f"SQLite insert failed: {e}",
        }


def list_payments(limit: int = 50) -> list:
    """Helper de debugging: devuelve los últimos N registros de la DB."""
    _ensure_db()
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM payments ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    # Test rápido
    res = register_payment_tool(
        invoice_id="INV-TEST-001",
        supplier_id="SUP001",
        amount=50000.0,
        decision="APPROVED",
        rejection_reason="",
    )
    print("Registro 1:", res)

    res2 = register_payment_tool(
        invoice_id="INV-TEST-002",
        supplier_id="SUP001",
        amount=200000.0,
        decision="REJECTED",
        rejection_reason="Excede límite contractual",
    )
    print("Registro 2:", res2)

    print("\nÚltimos pagos:")
    for p in list_payments(5):
        print(f"  {p['confirmation_id']}  {p['invoice_id']}  ${p['amount']}  {p['decision']}")