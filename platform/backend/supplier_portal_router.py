"""Router para el portal de proveedores."""

from __future__ import annotations

import sqlite3
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

# Rutas
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "payments.db"
SUPPLIER_PORTAL_DIR = PROJECT_ROOT / "supplier_portal"


router = APIRouter(prefix="/supplier", tags=["supplier-portal"])


@router.get("/portal")
def get_supplier_portal():
    """Sirve la página principal del portal de proveedores."""
    index_path = SUPPLIER_PORTAL_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Portal no encontrado")
    return FileResponse(str(index_path))


@router.post("/validate")
def validate_supplier(identifier: dict = None):
    """Valida un proveedor y devuelve sus datos."""
    if not identifier or 'identifier' not in identifier:
        return {"valid": False, "message": "Identificador requerido"}
    
    ident = identifier['identifier'].strip()
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Buscar por supplier_id
        cur.execute("""
            SELECT supplier_id, name, cuit, status, email, phone
            FROM suppliers
            WHERE UPPER(supplier_id) = UPPER(?)
        """, (ident,))
        
        row = cur.fetchone()
        
        # Si no encuentra, buscar por nombre
        if not row:
            cur.execute("""
                SELECT supplier_id, name, cuit, status, email, phone
                FROM suppliers
                WHERE UPPER(name) LIKE UPPER(?)
            """, (f"%{ident}%",))
            row = cur.fetchone()
        
        # Si no encuentra, buscar por CUIT
        if not row:
            cuit_norm = ident.replace('-', '').replace(' ', '')
            cur.execute("""
                SELECT supplier_id, name, cuit, status, email, phone
                FROM suppliers
                WHERE REPLACE(cuit, '-', '') = ?
            """, (cuit_norm,))
            row = cur.fetchone()
        
        conn.close()
        
        if row:
            if row['status'] != 'ACTIVE':
                return {
                    "valid": False,
                    "message": f"Tu cuenta está {row['status']}. Contactá a soporte."
                }
            
            return {
                "valid": True,
                "supplier": {
                    "id": row['supplier_id'],
                    "name": row['name'],
                    "cuit": row['cuit'],
                    "status": row['status'],
                    "email": row.get('email', ''),
                    "phone": row.get('phone', '')
                }
            }
        else:
            return {
                "valid": False,
                "message": "Proveedor no encontrado. Verificá el CUIT o nombre."
            }
            
    except Exception as e:
        return {
            "valid": False,
            "message": f"Error al buscar proveedor: {str(e)}"
        }


@router.get("/invoices/{supplier_id}")
def get_supplier_invoices(supplier_id: str):
    """Obtiene las facturas de un proveedor."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                invoice_id, supplier_id, amount, currency, invoice_date,
                state, rejection_reason, confirmation_id, registered_at
            FROM invoices
            WHERE UPPER(supplier_id) = UPPER(?)
            ORDER BY invoice_date DESC
        """, (supplier_id,))
        
        rows = cur.fetchall()
        conn.close()
        
        invoices = []
        for row in rows:
            invoices.append({
                "invoice_id": row['invoice_id'],
                "supplier_id": row['supplier_id'],
                "amount": row['amount'],
                "currency": row['currency'] or 'ARS',
                "invoice_date": row['invoice_date'],
                "state": row['state'],
                "rejection_reason": row['rejection_reason'] or '',
                "confirmation_id": row['confirmation_id'] or '',
                "registered_at": row['registered_at']
            })
        
        return {
            "supplier_id": supplier_id,
            "invoices": invoices,
            "count": len(invoices)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
