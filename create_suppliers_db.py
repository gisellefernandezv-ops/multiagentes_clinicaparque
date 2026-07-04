import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'payments.db')

# Datos de proveedores
SUPPLIERS = [
    {
        "supplier_id": "SUP001",
        "name": "TechCorp SA",
        "cuit": "30-71234567-0",
        "status": "ACTIVE",
        "category": "Servicios IT",
        "registration_date": "2023-05-10",
        "email": "info@techcorp.com",
        "phone": "+54 11 4567-8900",
        "address": "Av. Corrientes 1234, CABA",
    },
    {
        "supplier_id": "SUP002",
        "name": "Papelería Norte SRL",
        "cuit": "30-69874523-1",
        "status": "ACTIVE",
        "category": "Insumos de oficina",
        "registration_date": "2022-11-22",
        "email": "ventas@papelerianorte.com",
        "phone": "+54 11 4899-1234",
        "address": "Calle Florida 567, CABA",
    },
    {
        "supplier_id": "SUP003",
        "name": "Servicios Rápidos SA",
        "cuit": "30-70111222-3",
        "status": "INACTIVE",
        "category": "Logística y mensajería",
        "registration_date": "2021-08-15",
        "email": "contacto@serviciosrapidos.com",
        "phone": "+54 11 4321-9876",
        "address": "Av. 9 de Julio 890, CABA",
    },
    {
        "supplier_id": "SUP004",
        "name": "Limpieza Total SRL",
        "cuit": "30-70555666-7",
        "status": "ACTIVE",
        "category": "Servicios de limpieza",
        "registration_date": "2024-02-01",
        "email": "admin@limpiezatotal.com",
        "phone": "+54 11 5555-6666",
        "address": "Calle Lavalle 111, CABA",
    },
    {
        "supplier_id": "SUP005",
        "name": "Consultoría Digital SA",
        "cuit": "30-71234999-2",
        "status": "ACTIVE",
        "category": "Consultoría y transformación digital",
        "registration_date": "2024-06-30",
        "email": "hola@consultoriadigital.com",
        "phone": "+54 11 7777-8888",
        "address": "Av. Santa Fe 2222, CABA",
    },
]

def setup_suppliers_table():
    """Crea la tabla suppliers y carga los datos."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Crear tabla suppliers
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            cuit TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            category TEXT,
            registration_date TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Verificar si ya hay datos
    cur.execute("SELECT COUNT(*) FROM suppliers")
    count = cur.fetchone()[0]
    
    if count == 0:
        # Insertar datos
        for supplier in SUPPLIERS:
            cur.execute("""
                INSERT INTO suppliers 
                (supplier_id, name, cuit, status, category, registration_date, email, phone, address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                supplier["supplier_id"],
                supplier["name"],
                supplier["cuit"],
                supplier["status"],
                supplier["category"],
                supplier["registration_date"],
                supplier["email"],
                supplier["phone"],
                supplier["address"],
            ))
        print(f"[OK] Insertados {len(SUPPLIERS)} proveedores")
    else:
        print(f"[OK] Tabla suppliers ya tiene {count} registros")
    
    conn.commit()
    
    # Mostrar contenido
    cur.execute("SELECT supplier_id, name, cuit, status FROM suppliers")
    print("\nProveedores registrados:")
    print("-" * 80)
    for row in cur.fetchall():
        print(f"  {row[0]:8} | {row[1]:30} | {row[2]:15} | {row[3]}")
    print("-" * 80)
    
    conn.close()
    print(f"\n[OK] Base de datos: {DB_PATH}")

if __name__ == "__main__":
    setup_suppliers_table()
