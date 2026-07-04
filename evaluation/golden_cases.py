"""Casos de prueba dorados (golden cases) para evaluación del sistema."""

from __future__ import annotations

from typing import Dict, List

GOLDEN_CASES: List[Dict] = [
    {
        "case_id": "GC001",
        "description": "Factura válida dentro del límite",
        "input": {
            "invoice_id": "INV-001",
            "supplier_id": "SUP001",
            "supplier_name": "TechCorp SA",
            "amount": 50000.0,
            "currency": "ARS",
            "invoice_date": "2025-06-01",
        },
        "expected_decision": "APPROVED",
        "expected_fields": ["confirmation_id", "contract_limit", "payment_status"],
        "expected_contract_limit": 150000.0,
    },
    {
        "case_id": "GC002",
        "description": "Factura que supera el límite contractual",
        "input": {
            "invoice_id": "INV-002",
            "supplier_id": "SUP001",
            "supplier_name": "TechCorp SA",
            "amount": 200000.0,
            "currency": "ARS",
            "invoice_date": "2025-06-02",
        },
        "expected_decision": "REJECTED",
        "expected_fields": ["rejection_reason"],
        "expected_contract_limit": 150000.0,
    },
    {
        "case_id": "GC003",
        "description": "Proveedor inactivo",
        "input": {
            "invoice_id": "INV-003",
            "supplier_id": "SUP003",
            "supplier_name": "Servicios Rápidos SA",
            "amount": 10000.0,
            "currency": "ARS",
            "invoice_date": "2025-06-03",
        },
        "expected_decision": "REJECTED",
        "expected_fields": ["rejection_reason"],
        "expected_supplier_status": "INACTIVE",
    },
    {
        "case_id": "GC004",
        "description": "Monto que supera guardrail absoluto ($500k)",
        "input": {
            "invoice_id": "INV-004",
            "supplier_id": "SUP005",
            "supplier_name": "Consultoría Digital SA",
            "amount": 600000.0,
            "currency": "ARS",
            "invoice_date": "2025-06-04",
        },
        "expected_decision": "ESCALATED",
        "expected_fields": ["rejection_reason"],
    },
    {
        "case_id": "GC005",
        "description": "Proveedor inexistente",
        "input": {
            "invoice_id": "INV-005",
            "supplier_id": "SUP999",
            "supplier_name": "Fantasma SRL",
            "amount": 5000.0,
            "currency": "ARS",
            "invoice_date": "2025-06-05",
        },
        "expected_decision": "REJECTED",
        "expected_fields": ["rejection_reason"],
    },
    {
        "case_id": "GC006",
        "description": "Factura con datos incompletos (sin invoice_date)",
        "input": {
            "invoice_id": "INV-006",
            "supplier_id": "SUP002",
            "supplier_name": "Papelería Norte SRL",
            "amount": 15000.0,
            "currency": "ARS",
        },
        "expected_decision": "REJECTED",
        "expected_fields": ["rejection_reason"],
    },
]


def get_case_by_id(case_id: str) -> Dict:
    """Helper: devuelve un caso por ID."""
    for c in GOLDEN_CASES:
        if c["case_id"] == case_id:
            return c
    raise KeyError(f"Case not found: {case_id}")


__all__ = ["GOLDEN_CASES", "get_case_by_id"]


if __name__ == "__main__":
    print(f"Total golden cases: {len(GOLDEN_CASES)}")
    for c in GOLDEN_CASES:
        print(f"  {c['case_id']}  {c['expected_decision']:9s}  {c['description']}")