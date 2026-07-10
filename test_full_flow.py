"""Test completo E2E del orquestador InvoiceFlow"""
import sys
sys.path.insert(0, '.')

from app.backend.orchestrator import process_invoice

print("=" * 70)
print("  INVOICEFLOW ORCHESTRATOR - E2E TEST SUITE")
print("=" * 70)

test_cases = [
    {
        "name": "GC001 - Factura valida dentro del limite",
        "invoice": {
            "invoice_id": "FC-2026-SUP001-001",
            "supplier_id": "SUP001",
            "supplier_name": "TechCorp SA",
            "amount": 50000,
            "currency": "ARS",
            "invoice_date": "2025-06-20"
        },
        "expected": "APPROVED"
    },
    {
        "name": "GC002 - Supera limite contractual ($200k vs limite $150k)",
        "invoice": {
            "invoice_id": "FC-2026-SUP001-002",
            "supplier_id": "SUP001",
            "supplier_name": "TechCorp SA",
            "amount": 200000,
            "currency": "ARS",
            "invoice_date": "2025-06-20"
        },
        "expected": "REJECTED"
    },
    {
        "name": "GC003 - Proveedor inactivo (SUP003)",
        "invoice": {
            "invoice_id": "FC-2026-SUP003-001",
            "supplier_id": "SUP003",
            "supplier_name": "Servicios Rapidos SA",
            "amount": 10000,
            "currency": "ARS",
            "invoice_date": "2025-06-20"
        },
        "expected": "REJECTED"
    },
    {
        "name": "GC004 - Monto > $500k (escalado)",
        "invoice": {
            "invoice_id": "FC-2026-SUP005-001",
            "supplier_id": "SUP005",
            "supplier_name": "Consultoria Digital SA",
            "amount": 600000,
            "currency": "ARS",
            "invoice_date": "2025-06-20"
        },
        "expected": "ESCALATED"
    },
    {
        "name": "GC005 - Proveedor inexistente",
        "invoice": {
            "invoice_id": "FC-2026-SUP999-001",
            "supplier_id": "SUP999",
            "supplier_name": "Fantasma SRL",
            "amount": 5000,
            "currency": "ARS",
            "invoice_date": "2025-06-20"
        },
        "expected": "REJECTED"
    },
    {
        "name": "GC006 - Datos incompletos (falta invoice_date)",
        "invoice": {
            "invoice_id": "FC-2026-SUP002-001",
            "supplier_id": "SUP002",
            "supplier_name": "Papeleria Norte SRL",
            "amount": 15000,
            "currency": "ARS"
        },
        "expected": "REJECTED"
    }
]

results = []
passed = 0
failed = 0

for i, tc in enumerate(test_cases, 1):
    print(f"\n{'─' * 70}")
    print(f"TEST {i}/6: {tc['name']}")
    print(f"{'─' * 70}")
    
    try:
        result = process_invoice(tc["invoice"], source_file=None)
        
        decision = result.get("decision", "ERROR")
        status = result.get("payment_status", "N/A")
        reason = result.get("rejection_reason", "")
        confirmation = result.get("confirmation_id", "")
        
        match = "✅ PASS" if decision == tc["expected"] else "❌ FAIL"
        
        print(f"\n  Input:")
        print(f"    Invoice: {tc['invoice']['invoice_id']}")
        print(f"    Supplier: {tc['invoice']['supplier_id']}")
        print(f"    Amount: ARS {tc['invoice']['amount']:,}")
        
        print(f"\n  Result:")
        print(f"    Decision: {decision}")
        print(f"    Status: {status}")
        if confirmation:
            print(f"    Confirmation: {confirmation}")
        if reason:
            print(f"    Reason: {reason[:60]}...")
        
        print(f"\n  Expected: {tc['expected']} | Got: {decision} | {match}")
        
        if decision == tc["expected"]:
            passed += 1
            results.append({"test": tc["name"], "status": "PASS", "decision": decision})
        else:
            failed += 1
            results.append({"test": tc["name"], "status": "FAIL", "decision": decision, "expected": tc["expected"]})
            
    except Exception as e:
        print(f"\n  ❌ EXCEPTION: {e}")
        failed += 1
        results.append({"test": tc["name"], "status": "ERROR", "error": str(e)})

print(f"\n{'=' * 70}")
print("  RESULTADOS FINALES")
print(f"{'=' * 70}")
print(f"\n  ✅ Pass: {passed}/6")
print(f"  ❌ Fail: {failed}/6")
print(f"  📊 Pass Rate: {(passed/6)*100:.1f}%")

if passed == 6:
    print(f"\n  🎉 TODOS LOS TESTS PASARON!")
elif passed >= 4:
    print(f"\n  ⚠️  ALGUNOS TESTS FALLARON - Revisar ChromaDB (necesita GOOGLE_API_KEY)")
else:
    print(f"\n  ❌ DEMASIADOS FALLOS - Verificar sistema")

print(f"\n{'=' * 70}")
