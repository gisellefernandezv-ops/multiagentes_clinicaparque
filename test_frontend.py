"""Test E2E del Frontend (BackOffice)
Valida que:
- HTML del BackOffice carga
- app.js se sirve sin errores
- Todos los endpoints referenciados por app.js existen y devuelven datos reales
- Los campos del JSON son los esperados por el JS (post-fix BUG-001..005)
"""
import json
import re
import urllib.request


def http_get(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.status, resp.read().decode(errors="ignore")


def http_get_json(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode())


PASS = 0
FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    icon = "[OK]" if ok else "[X]"
    print(f"  {icon} {name:60s} {detail}")
    if ok:
        PASS += 1
    else:
        FAIL += 1


print("=" * 78)
print("  FRONTEND E2E TESTS - BackOffice")
print("=" * 78)


# 1. HTML root
print("\n[1] HTML del BackOffice")
status, html = http_get("http://localhost:8000/")
check("GET / responde 200", status == 200, f"status={status}")
check("HTML contiene 'InvoiceFlow'", "InvoiceFlow" in html)
check("HTML referencia /static/app.js", "/static/app.js" in html)
check("HTML referencia /static/style.css", "/static/style.css" in html)
check("HTML tiene #stat-inbox (dashboard)", 'id="stat-inbox"' in html)
check("HTML tiene #stat-approved", 'id="stat-approved"' in html)
check("HTML tiene #stat-rejected", 'id="stat-rejected"' in html)
check("HTML tiene #stat-escalated", 'id="stat-escalated"' in html)
check("HTML tiene #stat-total", 'id="stat-total"' in html)
check("HTML tiene sidebar nav", "sidebar-item" in html)
check("HTML tiene internal-chat-input", "internal-chat-input" in html)


# 2. JS file
print("\n[2] JavaScript del BackOffice")
status, js = http_get("http://localhost:8000/static/app.js")
check("GET /static/app.js responde 200", status == 200, f"status={status}, size={len(js)}")
check("JS no usa prefijo /api (BUG-001 fix)", "const API = '/api'" not in js)
check("JS usa const API = '' (BUG-001 fix)", "const API = ''" in js)
check("JS lee decisions.APPROVED (BUG-002 fix)", "decisions" in js and "APPROVED" in js)
check("JS lee total_amount_approved (BUG-002 fix)", "total_amount_approved" in js)
check("JS maneja array directo en inbox (BUG-003 fix)", "Array.isArray(data)" in js)
check("JS maneja array directo en invoices (BUG-004 fix)", "Array.isArray(data) ? data : (data.invoices" in js)
check("JS lee data.message en chat (BUG-005 fix)", "data.message" in js and "data.response" not in js.replace("data.response || 'Sin respuesta'", "data.message || 'Sin respuesta'") or "data.message || 'Sin respuesta'" in js)


# 3. Endpoints consumidos por el JS
print("\n[3] Endpoints consumidos por el JS")
endpoints = [
    ("GET", "/dashboard"),
    ("GET", "/inbox"),
    ("GET", "/invoices"),
    ("GET", "/health"),
    ("POST", "/chat"),
]
for method, path in endpoints:
    try:
        if method == "GET":
            status, data = http_get_json(f"http://localhost:8000{path}")
            check(f"{method} {path} responde 200", status == 200, f"status={status}")
        else:
            # POST test
            req = urllib.request.Request(
                f"http://localhost:8000{path}",
                data=json.dumps({"message": "test"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
            check(f"{method} {path} responde 200", status == 200, f"status={status}")
    except Exception as e:
        check(f"{method} {path}", False, str(e)[:40])


# 4. Estructura de las respuestas
print("\n[4] Estructura de respuestas JSON (post-fix)")
status, dash = http_get_json("http://localhost:8000/dashboard")
check("dashboard.inbox_count existe", "inbox_count" in dash, f"value={dash.get('inbox_count')}")
check("dashboard.decisions existe", "decisions" in dash, f"keys={list(dash.get('decisions', {}).keys())}")
check("dashboard.decisions.APPROVED existe", "APPROVED" in dash.get("decisions", {}), f"value={dash.get('decisions', {}).get('APPROVED')}")
check("dashboard.decisions.REJECTED existe", "REJECTED" in dash.get("decisions", {}))
check("dashboard.decisions.ESCALATED existe", "ESCALATED" in dash.get("decisions", {}))
check("dashboard.total_amount_approved existe", "total_amount_approved" in dash, f"value={dash.get('total_amount_approved')}")
check("dashboard.recent existe", "recent" in dash, f"len={len(dash.get('recent', []))}")

status, inbox = http_get_json("http://localhost:8000/inbox")
check("inbox es array", isinstance(inbox, list), f"type={type(inbox).__name__}, len={len(inbox) if isinstance(inbox, list) else 'N/A'}")
if isinstance(inbox, list) and inbox:
    check("inbox[0] tiene filename", "filename" in inbox[0])
    check("inbox[0] tiene invoice_id", "invoice_id" in inbox[0])

status, hist = http_get_json("http://localhost:8000/invoices")
check("invoices es array", isinstance(hist, list), f"type={type(hist).__name__}, len={len(hist) if isinstance(hist, list) else 'N/A'}")
if isinstance(hist, list) and hist:
    check("invoices[0] tiene invoice_id", "invoice_id" in hist[0])
    check("invoices[0] tiene decision", "decision" in hist[0])
    check("invoices[0] tiene confirmation_id", "confirmation_id" in hist[0])

# Chat
req = urllib.request.Request(
    "http://localhost:8000/chat",
    data=json.dumps({"message": "mostrame el historial"}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=10) as resp:
    chat = json.loads(resp.read().decode())
check("chat.intent existe", "intent" in chat, f"intent={chat.get('intent')}")
check("chat.message existe", "message" in chat, f"message={chat.get('message')[:50]}")
check("chat NO usa 'response' field", "response" not in chat)


# 5. Endpoint del eval dataset (BUG-006 fix)
print("\n[5] Endpoint del eval dataset (BUG-006 fix)")
try:
    status, ds = http_get_json("http://localhost:8000/tests/eval/datasets/invoiceflow-dataset.json")
    check("GET /tests/eval/datasets/*.json responde 200", status == 200)
    check("dataset tiene test_cases", "test_cases" in ds, f"len={len(ds.get('test_cases', []))}")
except Exception as e:
    check("GET /tests/eval/datasets/*.json", False, str(e))


# 6. Supplier Portal
print("\n[6] Supplier Portal")
status, html = http_get("http://localhost:8000/supplier/")
check("GET /supplier/ responde 200", status == 200, f"size={len(html)}")
check("Supplier Portal HTML", "SupplierPortal" in html or "supplier" in html.lower())


# 7. Swagger docs
print("\n[7] Swagger API Docs")
for port, name in [(8001, "supplier"), (8002, "contract")]:
    try:
        status, html = http_get(f"http://localhost:{port}/docs")
        check(f"GET :{port}/docs responde 200", status == 200, f"({name})")
        check(f":{port}/docs tiene Swagger", "swagger" in html.lower(), f"({name})")
    except Exception as e:
        check(f":{port}/docs", False, str(e))


# Resumen
print()
print("=" * 78)
print(f"  FRONTEND TESTS: {PASS} PASS / {FAIL} FAIL")
print("=" * 78)

import sys
sys.exit(0 if FAIL == 0 else 1)