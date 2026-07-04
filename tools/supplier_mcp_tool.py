"""Tool MCP — consulta de proveedores via SQLite.

Consulta la base de datos payments.db para verificar proveedores.
Soporta búsqueda por ID, CUIT o nombre.
"""

from __future__ import annotations

import sqlite3
import os
from typing import Optional

# Ruta a la base de datos
DB_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'payments.db'
)


def supplier_lookup_tool(
    supplier_id: str = None,
    name: str = None,
    cuit: str = None
) -> dict:
    """Consulta los datos de un proveedor por ID, CUIT o nombre.

    Busca en la base de datos SQLite (payments.db) en la tabla suppliers.
    
    Args:
        supplier_id: Identificador del proveedor (ej. "SUP001").
        name: Nombre o parte del nombre de la empresa.
        cuit: Número de CUIT/RUC del proveedor (ej. "30-71234567-0").

    Returns:
        dict con:
            - found: bool
            - supplier_id, name, cuit, status, category, email, phone, address
              (solo si found=True)
            - lookup_by: indica qué campo se usó para la búsqueda
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        # Búsqueda por supplier_id
        if supplier_id:
            cur.execute(
                "SELECT * FROM suppliers WHERE UPPER(supplier_id) = UPPER(?)",
                (supplier_id.strip(),)
            )
            row = cur.fetchone()
            if row:
                result = dict(row)
                result["found"] = True
                result["lookup_by"] = "supplier_id"
                return result
        
        # Búsqueda por CUIT
        if cuit:
            # Normalizar CUIT (quitar guiones)
            cuit_norm = cuit.strip().replace("-", "").replace(" ", "")
            cur.execute(
                "SELECT * FROM suppliers WHERE REPLACE(cuit, '-', '') = ?",
                (cuit_norm,)
            )
            row = cur.fetchone()
            if row:
                result = dict(row)
                result["found"] = True
                result["lookup_by"] = "cuit"
                return result
        
        # Búsqueda por nombre (búsqueda parcial, case-insensitive)
        if name:
            cur.execute(
                "SELECT * FROM suppliers WHERE UPPER(name) LIKE UPPER(?)",
                (f"%{name.strip()}%",)
            )
            row = cur.fetchone()
            if row:
                result = dict(row)
                result["found"] = True
                result["lookup_by"] = "name"
                return result
        
        # Si no se proporcionó ningún parámetro
        if not supplier_id and not name and not cuit:
            return {
                "found": False,
                "error": "Debe proporcionar supplier_id, name o cuit"
            }
        
        # No se encontró
        return {
            "found": False,
            "error": f"Proveedor no encontrado para: {supplier_id or name or cuit}"
        }
        
    except sqlite3.OperationalError as e:
        return {
            "found": False,
            "error": f"Error de base de datos: {str(e)}"
        }
    finally:
        conn.close()


if __name__ == "__main__":
    # Test rápido
    for sid in ["SUP001", "SUP003", "SUP999"]:
        r = supplier_lookup_tool(sid)
        print(f"{sid} → {r}")