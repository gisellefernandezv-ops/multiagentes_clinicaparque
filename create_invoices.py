"""Genera facturas de prueba para cada proveedor.

Crea:
- 3 facturas guardadas por proveedor (con diferentes estados)
- 3 facturas PDF por proveedor (para enviar) en carpeta "new invoices"
"""

import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Rutas
PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "data" / "payments.db"
PDF_DIR = PROJECT_ROOT / "data" / "new invoices"
PDF_DIR.mkdir(parents=True, exist_ok=True)

# Proveedores
SUPPLIERS = [
    {"id": "SUP001", "name": "TechCorp SA", "cuit": "30-71234567-0", "email": "info@techcorp.com", "address": "Av. Corrientes 1234, CABA"},
    {"id": "SUP002", "name": "Papeleria Norte SRL", "cuit": "30-69874523-1", "email": "ventas@papelerianorte.com", "address": "Calle Florida 567, CABA"},
    {"id": "SUP003", "name": "Servicios Rapidos SA", "cuit": "30-70111222-3", "email": "contacto@serviciosrapidos.com", "address": "Av. 9 de Julio 890, CABA"},
    {"id": "SUP004", "name": "Limpieza Total SRL", "cuit": "30-70555666-7", "email": "admin@limpiezatotal.com", "address": "Calle Lavalle 111, CABA"},
    {"id": "SUP005", "name": "Consultoria Digital SA", "cuit": "30-71234999-2", "email": "hola@consultoriadigital.com", "address": "Av. Santa Fe 2222, CABA"},
]

# Estados posibles
STATES = ["APPROVED", "REJECTED", "PENDING"]

# Montos variados
AMOUNTS = [25000.00, 75000.00, 150000.00, 45000.50, 98000.00, 32000.00, 185000.00, 67000.00, 123000.00, 41000.00]

def create_invoices_table():
    """Crea la tabla invoices si no existe."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT UNIQUE NOT NULL,
            supplier_id TEXT NOT NULL,
            supplier_name TEXT,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'ARS',
            invoice_date TEXT NOT NULL,
            state TEXT NOT NULL,
            rejection_reason TEXT,
            confirmation_id TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("[OK] Tabla invoices creada/verificada")

def generate_invoice_number(supplier_id, index):
    """Genera un numero de factura unico."""
    year = datetime.now().year
    return f"FC-{year}-{supplier_id}-{index:03d}"

def insert_historical_invoices():
    """Inserta 3 facturas por proveedor con estados variados."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Verificar si ya hay facturas historicas
    cur.execute("SELECT COUNT(*) FROM invoices WHERE invoice_id LIKE 'FC-%'")
    count = cur.fetchone()[0]
    
    if count > 0:
        print(f"[OK] Ya existen {count} facturas historicas")
        conn.close()
        return
    
    all_invoices = []
    base_date = datetime.now() - timedelta(days=90)
    
    for supplier in SUPPLIERS:
        for i in range(3):
            state = STATES[i]
            amount = AMOUNTS[len(all_invoices) % len(AMOUNTS)]
            invoice_date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            invoice_id = generate_invoice_number(supplier["id"], i+1)
            confirmation_id = f"PAY-{uuid.uuid4().hex[:8].upper()}" if state != "PENDING" else None
            registered_at = (base_date + timedelta(days=i*30, hours=10)).strftime('%Y-%m-%d %H:%M:%S')
            
            rejection_reason = ""
            if state == "REJECTED":
                reasons = [
                    "Excede limite contractual maximo",
                    "Proveedor con cuenta inactiva",
                    "Monto no coincide con orden de compra",
                ]
                rejection_reason = reasons[i % len(reasons)]
            
            all_invoices.append((
                invoice_id,
                supplier["id"],
                supplier["name"],
                amount,
                "ARS",
                invoice_date,
                state,
                rejection_reason,
                confirmation_id,
                registered_at
            ))
    
    cur.executemany("""
        INSERT INTO invoices 
        (invoice_id, supplier_id, supplier_name, amount, currency, invoice_date, 
         state, rejection_reason, confirmation_id, registered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, all_invoices)
    
    conn.commit()
    
    print(f"\n[OK] Insertadas {len(all_invoices)} facturas historicas")
    print("-" * 90)
    print(f"{'Nro Factura':<22} | {'Proveedor':<8} | {'Monto':>12} | {'Estado':<10}")
    print("-" * 90)
    for inv in all_invoices:
        print(f"{inv[0]:<22} | {inv[1]:<8} | ${inv[3]:>10,.2f} | {inv[6]:<10}")
    print("-" * 90)
    
    conn.close()

def generate_pdf_invoices():
    """Genera 3 facturas PDF por proveedor para enviar en carpeta 'new invoices'."""
    
    files_created = []
    year = datetime.now().year
    
    for supplier in SUPPLIERS:
        for i in range(3):
            amount = AMOUNTS[(len(SUPPLIERS) * i + SUPPLIERS.index(supplier)) % len(AMOUNTS)]
            invoice_number = f"FC-{year}-{supplier['id']}-NUEVA-{i+1}"
            invoice_date = datetime.now().strftime('%d/%m/%Y')
            due_date = (datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y')
            iva = amount * 0.21
            subtotal = amount - iva
            
            # Contenido del PDF
            pdf_content = f"""
================================================================================
                              FACTURA A
================================================================================

Numero: {invoice_number}
Fecha: {invoice_date}
Vencimiento: {due_date}

--------------------------------------------------------------------------------
EMPRESA EMISORA                         PROVEEDOR
--------------------------------------------------------------------------------
TechCorp Argentina SA                   {supplier['name']:<30}
Av. Libertador 5000                     CUIT: {supplier['cuit']}
CABA, Argentina                         {supplier['address']:<30}
                                        {supplier['email']:<30}

--------------------------------------------------------------------------------
DETALLE DE LA FACTURA
--------------------------------------------------------------------------------
Item                                      Subtotal              IVA            Importe
--------------------------------------------------------------------------------
Servicio de consultoria mensual         ${subtotal:>14,.2f}    ${iva:>10,.2f}    ${amount:>12,.2f}
                                                                                           
                                                                                           
                                                                                           

--------------------------------------------------------------------------------
                              SUBTOTAL: ${subtotal:>14,.2f}
                              IVA 21%:  ${iva:>14,.2f}
================================================================================
                              TOTAL: ARS ${amount:>14,.2f}
================================================================================

Forma de pago: Transferencia bancaria a 30 dias
Condicion: IVA incluido

--------------------------------------------------------------------------------
Generado automaticamente - Sistema de Facturacion de Proveedores
--------------------------------------------------------------------------------
"""
            
            filename = f"{invoice_number}.txt"
            filepath = PDF_DIR / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(pdf_content.strip())
            
            files_created.append(filename)
    
    print(f"\n[OK] Generadas {len(files_created)} facturas en carpeta 'new invoices':")
    print(f"Ruta: {PDF_DIR}")
    print("-" * 60)
    for f in sorted(files_created):
        print(f"  - {f}")
    print("-" * 60)

def show_summary():
    """Muestra resumen de facturas por proveedor y estado."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("\n" + "=" * 70)
    print("RESUMEN DE FACTURAS HISTORICAS POR PROVEEDOR")
    print("=" * 70)
    
    for supplier in SUPPLIERS:
        cur.execute("""
            SELECT state, COUNT(*) as count
            FROM invoices 
            WHERE supplier_id = ?
            GROUP BY state
        """, (supplier["id"],))
        
        rows = cur.fetchall()
        if rows:
            states_info = ", ".join([f"{r[0]}: {r[1]}" for r in rows])
            print(f"\n{supplier['id']} - {supplier['name']}")
            print(f"  Estados: {states_info}")
    
    print("\n" + "=" * 70)
    
    # Mostrar facturas PDF generadas
    pdf_files = list(PDF_DIR.glob("*.txt"))
    print(f"\nFacturas nuevas disponibles para enviar: {len(pdf_files)}")
    
    conn.close()

if __name__ == "__main__":
    print("=" * 70)
    print("GENERACION DE FACTURAS DE PRUEBA")
    print("=" * 70)
    
    create_invoices_table()
    insert_historical_invoices()
    generate_pdf_invoices()
    show_summary()
    
    print("\n[OK] Proceso completado!")