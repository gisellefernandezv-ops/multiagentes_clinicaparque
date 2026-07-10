"""Analisis profundo del sistema InvoiceFlow"""
import sys
sys.path.insert(0, '.')

import sqlite3
import json
from pathlib import Path

print("=" * 80)
print("  ANALISIS PROFUNDO - INVOICEFLOW SYSTEM")
print("=" * 80)

# ========================================
# 1. BASE DE DATOS PAYMENTS
# ========================================
print("\n[1] BASE DE DATOS PAYMENTS")
print("-" * 40)

payments_db = Path('data/payments.db')
if payments_db.exists():
    conn = sqlite3.connect(str(payments_db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Tablas
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  Tablas: {tables}")
    
    # Conteos
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} registros")
    
    # Ver payments
    if 'payments' in tables:
        cur.execute("SELECT * FROM payments ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()
        if rows:
            print(f"\n  ULTIMOS PAGOS:")
            for row in rows:
                print(f"    ID:{row['id']} | {row['invoice_id']} | {row['supplier_id']} | ${row['amount']:,.0f} | {row['decision']} | {row['payment_status']}")
        else:
            print("\n  WARNING: No hay pagos registrados!")
    
    conn.close()
else:
    print("  ERROR: payments.db NO EXISTE!")

print()

# ========================================
# 2. SUPPLIERS DB
# ========================================
print("[2] BASE DE DATOS SUPPLIERS")
print("-" * 40)

suppliers_db = Path('app/data/suppliers.db')
if suppliers_db.exists():
    conn = sqlite3.connect(str(suppliers_db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM suppliers ORDER BY supplier_id")
    rows = cur.fetchall()
    print(f"  Registros: {len(rows)}")
    for row in rows:
        print(f"    {row['supplier_id']} | {row['name'][:30]:<30} | {row['status']}")
    conn.close()
else:
    print("  ERROR: suppliers.db NO EXISTE!")

print()

# ========================================
# 3. CONTRACTS (ChromaDB)
# ========================================
print("[3] CONTRACTS (ChromaDB/RAG)")
print("-" * 40)

contracts_dir = Path('data/contracts')
if contracts_dir.exists():
    contracts = list(contracts_dir.glob('*.txt'))
    print(f"  Archivos de contrato: {len(contracts)}")
    for c in contracts:
        print(f"    - {c.name}")
else:
    print("  ERROR: data/contracts NO EXISTE!")

chroma_dir = Path('app/data/chroma_db')
if chroma_dir.exists():
    contents = list(chroma_dir.iterdir())
    print(f"  ChromaDB directory: {len(contents)} archivos")
else:
    print("  ChromaDB directory: NO EXISTE (necesita indexing)")

# ========================================
# 4. TEST DE CONTRACT SERVICE
# ========================================
print("\n[4] CONTRACT SERVICE API TEST")
print("-" * 40)

try:
    import httpx
    r = httpx.get("http://localhost:8002/contracts", timeout=5)
    print(f"  /contracts: status={r.status_code}")
    data = r.json()
    print(f"  Contratos cargados: {len(data)}")
    if data:
        for c in data:
            print(f"    - {c}")
except Exception as e:
    print(f"  ERROR conectando a Contract Service: {e}")

print()

# ========================================
# 5. INBOX
# ========================================
print("[5] INBOX (Facturas Pendientes)")
print("-" * 40)

inbox_dir = Path('app/data/inbox')
if inbox_dir.exists():
    files = [f for f in inbox_dir.iterdir() if f.is_file()]
    print(f"  Archivos en inbox: {len(files)}")
    for f in files[:10]:
        print(f"    - {f.name}")
    if len(files) > 10:
        print(f"    ... y {len(files)-10} mas")
else:
    print("  ERROR: inbox NO EXISTE!")

processed_dir = Path('app/data/processed')
if processed_dir.exists():
    processed = [f for f in processed_dir.iterdir() if f.is_file()]
    print(f"  Archivos procesados: {len(processed)}")
else:
    print("  Processed dir: NO EXISTE")

rejected_dir = Path('app/data/rejected')
if rejected_dir.exists():
    rejected = [f for f in rejected_dir.iterdir() if f.is_file()]
    print(f"  Archivos rechazados: {len(rejected)}")
else:
    print("  Rejected dir: NO EXISTE")

print()

# ========================================
# 6. HEALTH CHECK COMPLETO
# ========================================
print("[6] HEALTH CHECK DE SERVICIOS")
print("-" * 40)

services = [
    ("Backend", "http://localhost:8000/health"),
    ("Supplier", "http://localhost:8001/health"),
    ("Contract", "http://localhost:8002/health"),
]

for name, url in services:
    try:
        r = httpx.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"  {name}: OK - {data.get('service', 'unknown')}")
        else:
            print(f"  {name}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  {name}: ERROR - {e}")

print()

# ========================================
# 7. EJECUTAR FLUJO COMPLETO CON REGISTRO
# ========================================
print("[7] EJECUTAR FLUJO COMPLETO (con registro)")
print("-" * 40)

from app.backend.orchestrator import process_invoice

test_cases = [
    {
        "name": "TEST-1: Factura valida $50k",
        "invoice": {
            "invoice_id": "INV-TEST-001",
            "supplier_id": "SUP001",
            "supplier_name": "TechCorp SA",
            "amount": 50000,
            "currency": "ARS",
            "invoice_date": "2025-06-20"
        }
    },
    {
        "name": "TEST-2: Proveedor inactivo",
        "invoice": {
            "invoice_id": "INV-TEST-002",
            "supplier_id": "SUP003",
            "supplier_name": "Servicios Rapidos SA",
            "amount": 10000,
            "currency": "ARS",
            "invoice_date": "2025-06-20"
        }
    },
    {
        "name": "TEST-3: Monto alto (escalado)",
        "invoice": {
            "invoice_id": "INV-TEST-003",
            "supplier_id": "SUP005",
            "supplier_name": "Consultoria Digital SA",
            "amount": 600000,
            "currency": "ARS",
            "invoice_date": "2025-06-20"
        }
    },
    {
        "name": "TEST-4: Proveedor inexistente",
        "invoice": {
            "invoice_id": "INV-TEST-004",
            "supplier_id": "SUP999",
            "supplier_name": "Fantasma SRL",
            "amount": 5000,
            "currency": "ARS",
            "invoice_date": "2025-06-20"
        }
    },
]

for tc in test_cases:
    print(f"\n  Ejecutando: {tc['name']}")
    try:
        result = process_invoice(tc["invoice"], source_file=None)
        decision = result.get("decision", "ERROR")
        confirmation = result.get("confirmation_id", "N/A")
        reason = result.get("rejection_reason", "")[:50] if result.get("rejection_reason") else ""
        
        print(f"    Decision: {decision}")
        print(f"    Confirmation: {confirmation}")
        if reason:
            print(f"    Reason: {reason}...")
    except Exception as e:
        print(f"    ERROR: {e}")

print()

# ========================================
# 8. VERIFICAR QUE SE REGISTRARON
# ========================================
print("[8] VERIFICAR REGISTROS EN DB")
print("-" * 40)

conn = sqlite3.connect(str(payments_db))
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM payments ORDER BY id DESC LIMIT 10")
rows = cur.fetchall()
print(f"  Total en payments: {len(rows)}")
for row in rows:
    print(f"    {row['invoice_id']} | {row['supplier_id']} | ${row['amount']:,.0f} | {row['decision']} | {row['confirmation_id']}")
conn.close()

print()

# ========================================
# 9. PROBLEMAS IDENTIFICADOS
# ========================================
print("[9] PROBLEMAS IDENTIFICADOS")
print("-" * 40)

problems = []

# Check ChromaDB
if not list(Path('app/data/chroma_db').glob('*')):
    problems.append("ChromaDB vacia - necesita GOOGLE_API_KEY para indexar contratos")

if len(rows) == 0:
    problems.append("No hay facturas en payments.db - el orquestador no registra")

# Check contract service
try:
    r = httpx.get("http://localhost:8002/contracts", timeout=5)
    if r.status_code == 200 and len(r.json()) == 0:
        problems.append("Contract Service tiene 0 contratos indexados")
except:
    problems.append("No se puede conectar a Contract Service")

if problems:
    print("  ISSUES ENCONTRADOS:")
    for i, p in enumerate(problems, 1):
        print(f"    {i}. {p}")
else:
    print("  TODO OK!")

print()
print("=" * 80)
print("  ANALISIS COMPLETO FINALIZADO")
print("=" * 80)
