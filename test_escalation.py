"""Test del flujo A3 - Escalada con A2A."""
import json
import urllib.request

print("=" * 70)
print("TEST: Flujo A - Escalada >$500k -> deberia llamar A2A")
print("=" * 70)
data = json.dumps({
    "invoice_id": "FC-2026-ESC-001",
    "supplier_id": "SUP005",
    "amount": 600000.0,
    "currency": "ARS",
    "invoice_date": "2026-06-28",
}).encode()
req = urllib.request.Request(
    "http://localhost:8000/invoices",
    data=data,
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read().decode())
    print(json.dumps(result, indent=2, ensure_ascii=False))

print()
print("A2A audit integration check:")
if "audit" in result:
    print("  ✅ A2A integration WORKS - dictamen returned:")
    audit = result["audit"]
    print(f"     audit_id={audit.get('audit_id')}")
    print(f"     result={audit.get('audit_result')}")
    print(f"     confidence={audit.get('confidence')}")
else:
    print("  [X] A2A integration NOT working - 'audit' field missing")
    print(f"     steps: {result.get('steps', 'NO STEPS')}")