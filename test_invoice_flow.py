"""Test del flujo A completo via API."""
import json
import urllib.request

# Test 1: APROBADA (SUP001, monto bajo, dentro del límite $150k)
print("=" * 70)
print("TEST 1: Flujo A — Aprobada (SUP001, $50,000)")
print("=" * 70)
data = json.dumps({
    "invoice_id": "FC-2026-TEST-001",
    "supplier_id": "SUP001",
    "amount": 50000.0,
    "currency": "ARS",
    "invoice_date": "2026-06-28",
}).encode()
req = urllib.request.Request("http://localhost:8000/invoices", data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
        print(json.dumps(result, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()}")

# Test 2: RECHAZADA (SUP003 INACTIVE)
print()
print("=" * 70)
print("TEST 2: Flujo A — Rechazada (SUP003 INACTIVE)")
print("=" * 70)
data = json.dumps({
    "invoice_id": "FC-2026-TEST-002",
    "supplier_id": "SUP003",
    "amount": 10000.0,
    "currency": "ARS",
    "invoice_date": "2026-06-28",
}).encode()
req = urllib.request.Request("http://localhost:8000/invoices", data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
        print(json.dumps(result, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()}")

# Test 3: ESCALADA (>$500k)
print()
print("=" * 70)
print("TEST 3: Flujo A — Escalada ($600k)")
print("=" * 70)
data = json.dumps({
    "invoice_id": "FC-2026-TEST-003",
    "supplier_id": "SUP005",
    "amount": 600000.0,
    "currency": "ARS",
    "invoice_date": "2026-06-28",
}).encode()
req = urllib.request.Request("http://localhost:8000/invoices", data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
        print(json.dumps(result, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()}")