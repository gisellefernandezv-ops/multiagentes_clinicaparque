"""Carga facturas de ejemplo en el inbox simulando que llegaron por email.

Simula el escenario real: un operador de cuentas a pagar recibe 3 facturas
por email durante la mañana y las deposita en la carpeta inbox para que
el sistema las procese.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime, timedelta


# Raíz del proyecto
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
INBOX = PROJECT_ROOT / "platform" / "data" / "inbox"
INBOX.mkdir(parents=True, exist_ok=True)


# 3 facturas que llegaron "hoy por la mañana" (escenario realista)
INVOICES = [
    {
        # Escenario 1: proveedor conocido, monto válido → APROBADA
        "invoice_id": "INV-2024-001",
        "supplier_id": "SUP001",
        "supplier_name": "TechCorp SA",
        "amount": 75000.00,
        "currency": "ARS",
        "invoice_date": datetime.now().strftime("%Y-%m-%d"),
        "concept": "Servicios de consultoría - Mayo 2024",
        "received_at": "08:42",
        "email_from": "billing@techcorp.com.ar",
    },
    {
        # Escenario 2: proveedor correcto, monto excesivo → RECHAZADA
        "invoice_id": "INV-2024-002",
        "supplier_id": "SUP001",
        "supplier_name": "TechCorp SA",
        "amount": 180000.00,
        "currency": "ARS",
        "invoice_date": datetime.now().strftime("%Y-%m-%d"),
        "concept": "Servicios de consultoría - Mayo 2024 (adicional)",
        "received_at": "09:15",
        "email_from": "billing@techcorp.com.ar",
    },
    {
        # Escenario 3: monto gigante → ESCALADA a revisión humana
        "invoice_id": "INV-2024-003",
        "supplier_id": "SUP005",
        "supplier_name": "Consultoría Digital SA",
        "amount": 650000.00,
        "currency": "ARS",
        "invoice_date": datetime.now().strftime("%Y-%m-%d"),
        "concept": "Proyecto transformación digital - Hito 1",
        "received_at": "10:03",
        "email_from": "proyectos@condigital.com.ar",
    },
]


def main():
    print("=" * 70)
    print("  SIMULACIÓN: Llegan 3 facturas por email esta mañana")
    print("=" * 70)

    # Limpiar inbox primero
    for f in INBOX.glob("*"):
        if f.is_file():
            f.unlink()

    for inv in INVOICES:
        # Guardar como JSON (formato que el sistema entiende)
        path = INBOX / f"{inv['invoice_id']}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(inv, f, indent=2, ensure_ascii=False)

        print(f"\n📧 Email recibido a las {inv['received_at']}")
        print(f"   De: {inv['email_from']}")
        print(f"   Asunto: Factura {inv['invoice_id']} - {inv['concept']}")
        print(f"   💾 Guardada en inbox: {path.name}")
        print(f"   → ${inv['amount']:,.0f} ({inv['supplier_name']})")

    print("\n" + "=" * 70)
    print(f"  ✓ {len(INVOICES)} facturas depositadas en {INBOX}")
    print("=" * 70)
    print("\n💡 Próximos pasos:")
    print("   1. Watcher automático: las procesa apenas aparezcan")
    print("   2. Chat: 'procesá todo el inbox'")
    print("   3. UI: pestaña Inbox → 'Procesar todo'")
    print("   4. API: POST /inbox/process-all")


if __name__ == "__main__":
    main()