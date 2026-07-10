"""Test del orquestador - procesar factura de prueba"""
import sys
sys.path.insert(0, '.')

from app.backend.orchestrator import process_invoice

# Factura de prueba
factura = {
    "invoice_id": "FC-2026-SUP001-TEST",
    "supplier_id": "SUP001",
    "supplier_name": "TechCorp SA",
    "amount": 50000,
    "currency": "ARS",
    "invoice_date": "2025-06-20"
}

print("=" * 60)
print("INVOICEFLOW ORCHESTRATOR - TEST E2E")
print("=" * 60)

print(f"\n📥 Input:")
print(f"   Invoice ID: {factura['invoice_id']}")
print(f"   Supplier:   {factura['supplier_id']} - {factura['supplier_name']}")
print(f"   Amount:     ARS {factura['amount']:,.2f}")
print(f"   Date:       {factura['invoice_date']}")

print("\n⏳ Procesando...")

try:
    resultado = process_invoice(factura, source_file=None)
    
    print("\n📤 Resultado:")
    print(f"   Decision:    {resultado.get('decision', 'N/A')}")
    print(f"   Status:      {resultado.get('payment_status', 'N/A')}")
    print(f"   Confirmation: {resultado.get('confirmation_id', 'N/A')}")
    
    if resultado.get('rejection_reason'):
        print(f"   Reason:      {resultado.get('rejection_reason', '')}")
    
    print("\n✅ ORCHESTRATOR E2E TEST COMPLETADO")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
