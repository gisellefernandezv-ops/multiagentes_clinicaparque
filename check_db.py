import sqlite3

conn = sqlite3.connect('c:/Users/gisel/OneDrive/Escritorio/tp_multiagentes/invoice_approval_system/data/payments.db')
cur = conn.cursor()

# Listar tablas
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tablas:", cur.fetchall())

# Estructura de cada tabla
for table in ['invoices', 'suppliers']:
    try:
        cur.execute(f"PRAGMA table_info({table})")
        print(f"\nEstructura de '{table}':")
        for col in cur.fetchall():
            print(f"  {col[1]} {col[2]}")
    except:
        pass

# Ver datos de suppliers si existe
try:
    cur.execute("SELECT * FROM suppliers LIMIT 10")
    print("\nDatos de suppliers:")
    for row in cur.fetchall():
        print(f"  {row}")
except Exception as e:
    print(f"\nError o tabla suppliers no existe: {e}")

conn.close()
