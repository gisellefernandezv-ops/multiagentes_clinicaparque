"""Orquestador de facturas (versión producto).

Pipeline:
  1) Guardrail estructural (determinístico)
  2) Llamada HTTP a supplier-service (validación)
  3) Llamada HTTP a contract-service (RAG + límite)
  4) Persistencia en SQLite (payments.db)
  5) Devolución de decisión final

Implementa el mismo flujo que el orquestador ADK pero llamando a los
microservicios reales en lugar de tools locales. Se puede usar ADK
en paralelo (decorador), pero el core es HTTP+SQL directo para
simplicidad operacional.
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from guardrails.invoice_guardrail import apply_invoice_guardrail
from service_clients import supplier_client, contract_client
from settings import settings


# Regex para normalizar supplier_id
SUPPLIER_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
DATE_FORMAT = "%Y-%m-%d"


def _ensure_payments_db():
    settings.payments_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(settings.payments_db)) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT NOT NULL,
            supplier_id TEXT NOT NULL,
            amount REAL NOT NULL,
            decision TEXT NOT NULL,
            rejection_reason TEXT,
            payment_status TEXT NOT NULL,
            confirmation_id TEXT NOT NULL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
        CREATE INDEX IF NOT EXISTS idx_payments_supplier ON payments(supplier_id);
        CREATE INDEX IF NOT EXISTS idx_payments_decision ON payments(decision);
        """)
        conn.commit()


def _generate_confirmation_id() -> str:
    return f"PAY-{uuid.uuid4().hex[:8].upper()}"


def _persist_payment(
    invoice_id: str,
    supplier_id: str,
    amount: float,
    decision: str,
    rejection_reason: str,
    payment_status: str,
    source_file: Optional[str] = None,
) -> dict:
    _ensure_payments_db()
    confirmation_id = _generate_confirmation_id()
    processed_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    try:
        with sqlite3.connect(str(settings.payments_db)) as conn:
            conn.execute(
                """INSERT INTO payments
                (invoice_id, supplier_id, amount, decision,
                 rejection_reason, payment_status, confirmation_id,
                 processed_at, source_file)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (invoice_id, supplier_id, amount, decision, rejection_reason,
                 payment_status, confirmation_id, processed_at, source_file),
            )
            conn.commit()
        return {"success": True, "confirmation_id": confirmation_id,
                "payment_status": payment_status, "processed_at": processed_at}
    except Exception as e:
        return {"success": False, "confirmation_id": "", "payment_status": "ERROR",
                "processed_at": "", "error": str(e)}


def process_invoice(invoice: Dict, source_file: Optional[str] = None) -> Dict:
    """Procesa una factura completa y devuelve la decisión final.

    Args:
        invoice: dict con {invoice_id, supplier_id, supplier_name,
                           amount, currency, invoice_date, ...}
        source_file: path del archivo del inbox (opcional, para auditoría).

    Returns:
        dict con {decision, invoice_id, supplier_id, amount,
                  rejection_reason, confirmation_id, payment_status,
                  guardrail_action, guardrail_reason,
                  validation, contract, steps[]}
    """
    steps = []

    # ---- PASO 1: Guardrail estructural ----
    gr = apply_invoice_guardrail(invoice)
    steps.append({"step": "guardrail", **gr})

    if not gr["passed"]:
        decision = "ESCALATED" if gr["action"] == "ESCALATE" else "REJECTED"
        payment_status = (
            "PENDING_HUMAN_REVIEW" if decision == "ESCALATED" else "REJECTED"
        )
        persist = _persist_payment(
            invoice.get("invoice_id", "UNKNOWN"),
            invoice.get("supplier_id", "UNKNOWN"),
            float(invoice.get("amount") or 0),
            decision,
            gr["reason"],
            payment_status,
            source_file,
        )
        return {
            "decision": decision,
            "invoice_id": invoice.get("invoice_id", "UNKNOWN"),
            "supplier_id": invoice.get("supplier_id", "UNKNOWN"),
            "amount": float(invoice.get("amount") or 0),
            "rejection_reason": gr["reason"],
            "confirmation_id": persist["confirmation_id"],
            "payment_status": persist["payment_status"],
            "guardrail_action": gr["action"],
            "guardrail_reason": gr["reason"],
            "validation": {},
            "contract": {},
            "steps": steps,
            "source_file": source_file,
        }

    # ---- PASO 2: Validación de proveedor (HTTP a supplier-service) ----
    supplier_id = invoice.get("supplier_id", "").strip().upper()
    supplier_info = supplier_client.get_supplier(supplier_id)
    steps.append({"step": "validation", "supplier_id": supplier_id, **supplier_info})

    if not supplier_info.get("found"):
        return _finalize(
            invoice, "REJECTED",
            f"Proveedor {supplier_id} no encontrado en el registro",
            supplier_info=supplier_info, steps=steps, source_file=source_file,
        )

    if supplier_info.get("status") != "ACTIVE":
        return _finalize(
            invoice, "REJECTED",
            f"Proveedor {supplier_id} está {supplier_info.get('status')} (no activo)",
            supplier_info=supplier_info, steps=steps, source_file=source_file,
        )

    # ---- PASO 3: Control contractual (HTTP a contract-service / RAG) ----
    amount = float(invoice.get("amount"))
    contract_info = contract_client.check_contract(supplier_id, amount)
    steps.append({"step": "contract", **contract_info})

    if not contract_info.get("found"):
        return _finalize(
            invoice, "REJECTED",
            f"No se encontró contrato vigente para {supplier_id}: "
            f"{contract_info.get('error', 'sin contrato')}",
            supplier_info=supplier_info, contract_info=contract_info,
            steps=steps, source_file=source_file,
        )

    if not contract_info.get("within_limit"):
        return _finalize(
            invoice, "REJECTED",
            f"Monto ${amount:,.0f} excede el límite contractual de "
            f"${contract_info['contract_limit']:,.0f} "
            f"(contrato de {supplier_info.get('name')})",
            supplier_info=supplier_info, contract_info=contract_info,
            steps=steps, source_file=source_file,
        )

    # ---- PASO 4: APROBADO ----
    return _finalize(
        invoice, "APPROVED", "",
        supplier_info=supplier_info, contract_info=contract_info,
        steps=steps, source_file=source_file,
    )


def _finalize(
    invoice: Dict, decision: str, rejection_reason: str,
    supplier_info: Optional[dict] = None,
    contract_info: Optional[dict] = None,
    steps: Optional[list] = None,
    source_file: Optional[str] = None,
) -> Dict:
    """Persiste el resultado y devuelve el dict final."""
    payment_status_map = {
        "APPROVED": "PENDING_PAYMENT",
        "ESCALATED": "PENDING_HUMAN_REVIEW",
        "REJECTED": "REJECTED",
    }
    payment_status = payment_status_map[decision]
    amount = float(invoice.get("amount") or 0)
    persist = _persist_payment(
        invoice.get("invoice_id", "UNKNOWN"),
        invoice.get("supplier_id", "UNKNOWN"),
        amount,
        decision,
        rejection_reason,
        payment_status,
        source_file,
    )
    return {
        "decision": decision,
        "invoice_id": invoice.get("invoice_id", "UNKNOWN"),
        "supplier_id": invoice.get("supplier_id", "UNKNOWN"),
        "amount": amount,
        "rejection_reason": rejection_reason,
        "confirmation_id": persist["confirmation_id"],
        "payment_status": persist["payment_status"],
        "guardrail_action": "APPROVE" if decision == "APPROVED" else (
            "ESCALATE" if decision == "ESCALATED" else "REJECT"
        ),
        "guardrail_reason": steps[0]["reason"] if steps else "",
        "validation": supplier_info or {},
        "contract": contract_info or {},
        "steps": steps or [],
        "source_file": source_file,
        "supplier_name": (supplier_info or {}).get("name", ""),
        "contract_limit": (contract_info or {}).get("contract_limit", 0.0),
    }