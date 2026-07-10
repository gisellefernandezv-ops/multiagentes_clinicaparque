"""Orquestador de facturas (versión producto).

Pipeline:
  1) Guardrail estructural (determinístico)
  2) Llamada HTTP a supplier-service (validación)
  3) Llamada HTTP a contract-service (RAG + límite)
  4) A2A External Auditor (si guardrail action == ESCALATE)
  5) Persistencia en SQLite (payments.db)
  6) Devolución de decisión final

Implementa el mismo flujo que el orquestador ADK pero llamando a los
microservicios reales en lugar de tools locales. Se puede usar ADK
en paralelo (decorador), pero el core es HTTP+SQL directo para
simplicidad operacional.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import httpx

from guardrails.invoice_guardrail import apply_invoice_guardrail
from .service_clients import supplier_client, contract_client
from .settings import settings


# Regex para normalizar supplier_id
SUPPLIER_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
DATE_FORMAT = "%Y-%m-%d"

# A2A: External Auditor (SPEC_009)
EXTERNAL_AUDITOR_URL = os.getenv("INV_EXTERNAL_AUDITOR_URL", "http://127.0.0.1:8003")


def _call_external_auditor(
    invoice_id: str,
    supplier_id: str,
    amount: float,
    invoice_data: Optional[dict] = None,
) -> dict:
    """Llama al agente auditor externo (A2A) para dictaminar una factura escalada.

    Returns:
        dict con {audit_id, audit_result, confidence, findings, summary, error?}
    """
    try:
        payload = {
            "invoice_id": invoice_id,
            "supplier_id": supplier_id,
            "amount": amount,
            "invoice_data": invoice_data or {},
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(f"{EXTERNAL_AUDITOR_URL}/audit", json=payload)
        if resp.status_code == 200:
            return resp.json()
        return {
            "audit_id": None,
            "audit_result": "ERROR",
            "confidence": 0.0,
            "findings": [],
            "summary": f"A2A call failed: HTTP {resp.status_code}",
            "error": resp.text,
        }
    except Exception as e:
        return {
            "audit_id": None,
            "audit_result": "ERROR",
            "confidence": 0.0,
            "findings": [],
            "summary": f"A2A call failed: {e}",
            "error": str(e),
        }


def _ensure_payments_db():
    settings.payments_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(settings.payments_db)) as conn:
        # Idempotente: crea la tabla si no existe
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
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
        CREATE INDEX IF NOT EXISTS idx_payments_supplier ON payments(supplier_id);
        CREATE INDEX IF NOT EXISTS idx_payments_decision ON payments(decision);
        """)
        # Migración: agregar columnas faltantes a tablas pre-existentes
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(payments)").fetchall()}
        if "registered_at" not in existing_cols:
            try:
                conn.execute("ALTER TABLE payments ADD COLUMN registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            except Exception:
                pass
        if "source_file" not in existing_cols:
            try:
                conn.execute("ALTER TABLE payments ADD COLUMN source_file TEXT")
            except Exception:
                pass
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
    registered_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    try:
        with sqlite3.connect(str(settings.payments_db)) as conn:
            conn.execute(
                """INSERT INTO payments
                (invoice_id, supplier_id, amount, decision,
                 rejection_reason, payment_status, confirmation_id,
                 registered_at, source_file)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (invoice_id, supplier_id, amount, decision, rejection_reason,
                 payment_status, confirmation_id, registered_at, source_file),
            )
            conn.commit()
        return {"success": True, "confirmation_id": confirmation_id,
                "payment_status": payment_status, "registered_at": registered_at}
    except Exception as e:
        return {"success": False, "confirmation_id": "", "payment_status": "ERROR",
                "registered_at": "", "error": str(e)}


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

        # SPEC_009: A2A call when guardrail action = ESCALATE
        audit = None
        if decision == "ESCALATED":
            audit = _call_external_auditor(
                invoice_id=invoice.get("invoice_id", "UNKNOWN"),
                supplier_id=invoice.get("supplier_id", "UNKNOWN"),
                amount=float(invoice.get("amount") or 0),
                invoice_data={
                    "currency": invoice.get("currency", "ARS"),
                    "invoice_date": invoice.get("invoice_date", ""),
                },
            )
            steps.append({"step": "a2a_audit", **audit})

        persist = _persist_payment(
            invoice.get("invoice_id", "UNKNOWN"),
            invoice.get("supplier_id", "UNKNOWN"),
            float(invoice.get("amount") or 0),
            decision,
            gr["reason"],
            payment_status,
            source_file,
        )
        result = {
            "decision": decision,
            "invoice_id": invoice.get("invoice_id", "UNKNOWN"),
            "supplier_id": invoice.get("supplier_id", "UNKNOWN"),
            "amount": float(invoice.get("amount") or 0),
            "rejection_reason": gr["reason"],
            "confirmation_id": persist["confirmation_id"],
            "payment_status": persist["payment_status"],
            "tipo_comprobante": invoice.get("tipo_comprobante"),
            "punto_venta": invoice.get("punto_venta"),
            "numero_comprobante": invoice.get("numero_comprobante"),
            "items": invoice.get("items", []),
            "subtotal_gravado": invoice.get("subtotal_gravado"),
            "iva_21": invoice.get("iva_21"),
            "letra_comprobante": invoice.get("letra_comprobante"),
            "guardrail_action": gr["action"],
            "guardrail_reason": gr["reason"],
            "validation": {},
            "contract": {},
            "steps": steps,
            "source_file": source_file,
        }
        if audit:
            result["audit"] = audit
        return result

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

    # ---- PASO 3: Control contractual (FIX BUG-016: ahora via supplier-service) ----
    amount = float(invoice.get("amount"))
    contract_info = supplier_client.check_contract(supplier_id, amount)
    steps.append({"step": "contract", **contract_info})

    if not contract_info.get("found"):
        return _finalize(
            invoice, "REJECTED",
            f"No se encontró contrato vigente para {supplier_id}: "
            f"{contract_info.get('error', 'sin contrato')}",
            supplier_info=supplier_info, contract_info=contract_info,
            steps=steps, source_file=source_file,
        )

    # FIX BUG-016: validar contra el modo del contrato (EXACTO o NO_SUPERAR)
    mode = contract_info.get("mode", "NO_SUPERAR")
    contract_limit = contract_info.get("contract_limit", 0.0)

    if mode == "EXACTO":
        # El monto debe ser EXACTAMENTE igual al limite
        if abs(amount - contract_limit) > 0.01:
            return _finalize(
                invoice, "REJECTED",
                f"Contrato modo EXACTO: el monto ${amount:,.0f} debe ser exactamente "
                f"${contract_limit:,.0f} (contrato de {supplier_info.get('name')})",
                supplier_info=supplier_info, contract_info=contract_info,
                steps=steps, source_file=source_file,
            )
    else:  # NO_SUPERAR (default)
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
        # FIX BUG-014: propagar campos de Factura B del parser
        "tipo_comprobante": invoice.get("tipo_comprobante"),
        "punto_venta": invoice.get("punto_venta"),
        "numero_comprobante": invoice.get("numero_comprobante"),
        "emisor_razon_social": invoice.get("emisor_razon_social"),
        "emisor_cuit": invoice.get("emisor_cuit"),
        "cae": invoice.get("cae"),
        "codigo_barras": invoice.get("codigo_barras"),
        "items": invoice.get("items", []),
        # FIX BUG-015: subtotal/IVA para Factura A
        "subtotal_gravado": invoice.get("subtotal_gravado"),
        "iva_21": invoice.get("iva_21"),
        "letra_comprobante": invoice.get("letra_comprobante"),
    }
