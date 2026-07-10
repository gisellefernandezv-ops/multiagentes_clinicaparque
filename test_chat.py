import json
import urllib.request

print("=== TEST CHAT ENDPOINTS ===\n")

# Test 1: historial
req = urllib.request.Request(
    "http://localhost:8000/chat",
    data=json.dumps({"message": "mostrame el historial"}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=10) as resp:
    r = json.loads(resp.read().decode())
    print(f"[history] intent={r['intent']}, message={r['message']}")
    print(f"  items in data: {len(r.get('data', {}).get('items', []))}")

# Test 2: listar inbox
req = urllib.request.Request(
    "http://localhost:8000/chat",
    data=json.dumps({"message": "que facturas hay en el inbox?"}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=10) as resp:
    r = json.loads(resp.read().decode())
    print(f"\n[list_inbox] intent={r['intent']}, message={r['message']}")
    items = r.get('data', {}).get('items', [])
    print(f"  items: {len(items)}")
    if items:
        print(f"  primer item: {items[0]}")

# Test 3: unknown
req = urllib.request.Request(
    "http://localhost:8000/chat",
    data=json.dumps({"message": "asdf qwerty"}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=10) as resp:
    r = json.loads(resp.read().decode())
    print(f"\n[unknown] intent={r['intent']}")
    print(f"  message: {r['message'][:100]}...")