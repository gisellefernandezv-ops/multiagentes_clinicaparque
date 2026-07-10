"""Test A2A — External Auditor."""
import json
import urllib.request

# Test A2A: auditoría de factura escalada
print("=" * 70)
print("A2A TEST: External Auditor — Audit de factura escalada")
print("=" * 70)
data = json.dumps({
    "invoice_id": "FC-2026-TEST-003",
    "supplier_id": "SUP005",
    "amount": 600000.0,
    "invoice_data": {
        "invoice_date": "2026-06-28",
        "currency": "ARS"
    }
}).encode()
req = urllib.request.Request(
    "http://localhost:8003/audit",
    data=data,
    headers={"Content-Type": "application/json"}
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode())
        print(json.dumps(result, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()}")

print()
print("=" * 70)
print("A2A TEST: External Auditor — Info del agente")
print("=" * 70)
with urllib.request.urlopen("http://localhost:8003/") as resp:
    result = json.loads(resp.read().decode())
    print(json.dumps(result, indent=2, ensure_ascii=False))