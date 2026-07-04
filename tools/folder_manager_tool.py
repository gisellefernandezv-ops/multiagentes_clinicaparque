"""Tool para gestionar facturas en carpeta new invoices.

Permite:
- Listar facturas pendientes
- Crear carpetas por CUIT
- Mover/agrupar facturas
- Ver contenido de carpetas
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict

# Rutas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INVOICES_DIR = PROJECT_ROOT / "data" / "new invoices"


def list_pending_invoices() -> dict:
    """Lista todas las facturas pendientes en la carpeta new invoices.
    
    Returns:
        dict con lista de facturas y estadísticas.
    """
    try:
        if not INVOICES_DIR.exists():
            return {
                "success": False,
                "error": f"La carpeta {INVOICES_DIR} no existe",
                "invoices": [],
                "count": 0
            }
        
        # Buscar archivos de factura (txt, pdf)
        invoices = []
        for file_path in INVOICES_DIR.iterdir():
            if file_path.is_file() and file_path.suffix in ['.txt', '.pdf']:
                # Extraer supplier_id del nombre si es posible
                filename = file_path.stem
                supplier_id = None
                if "SUP" in filename:
                    parts = filename.split("-")
                    for p in parts:
                        if p.startswith("SUP"):
                            supplier_id = p
                            break
                
                invoices.append({
                    "filename": file_path.name,
                    "supplier_id": supplier_id,
                    "path": str(file_path),
                    "size_kb": round(file_path.stat().st_size / 1024, 2)
                })
        
        return {
            "success": True,
            "invoices": invoices,
            "count": len(invoices),
            "folder": str(INVOICES_DIR)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "invoices": [],
            "count": 0
        }


def create_supplier_folder(cuit: str) -> dict:
    """Crea una carpeta para el proveedor basada en su CUIT.
    
    Args:
        cuit: Número de CUIT del proveedor (ej: "30-71234567-0")
    
    Returns:
        dict con el resultado de la operacion.
    """
    try:
        # Normalizar CUIT para nombre de carpeta
        cuit_normalized = cuit.replace("-", "").replace(" ", "")
        folder_name = f"CUIT-{cuit_normalized}"
        folder_path = INVOICES_DIR / folder_name
        
        if folder_path.exists():
            return {
                "success": True,
                "message": f"La carpeta {folder_name} ya existe",
                "folder_path": str(folder_path),
                "created": False
            }
        
        folder_path.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True,
            "message": f"Carpeta creada: {folder_name}",
            "folder_path": str(folder_path),
            "created": True
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "folder_path": ""
        }


def move_invoice_to_folder(invoice_filename: str, cuit: str) -> dict:
    """Mueve una factura a la carpeta del proveedor.
    
    Args:
        invoice_filename: Nombre del archivo de factura
        cuit: CUIT del proveedor
    
    Returns:
        dict con el resultado.
    """
    try:
        # Normalizar CUIT
        cuit_normalized = cuit.replace("-", "").replace(" ", "")
        folder_name = f"CUIT-{cuit_normalized}"
        folder_path = INVOICES_DIR / folder_name
        
        # Crear carpeta si no existe
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
        
        # Buscar archivo origen
        source_path = INVOICES_DIR / invoice_filename
        if not source_path.exists():
            # Buscar con cualquier extension
            for ext in ['.txt', '.pdf']:
                alt_path = INVOICES_DIR / f"{invoice_filename}{ext}"
                if alt_path.exists():
                    source_path = alt_path
                    break
        
        if not source_path.exists():
            return {
                "success": False,
                "error": f"Archivo {invoice_filename} no encontrado"
            }
        
        # Mover archivo
        dest_path = folder_path / source_path.name
        shutil.move(str(source_path), str(dest_path))
        
        return {
            "success": True,
            "message": f"Factura movida a {folder_name}",
            "source": str(source_path),
            "destination": str(dest_path)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def group_invoices_by_supplier(supplier_id: str = None) -> dict:
    """Agrupa facturas por proveedor automaticamente.
    
    Si se especifica supplier_id, solo procesa ese proveedor.
    Si no, procesa todas las facturas pendientes.
    
    Args:
        supplier_id: ID del proveedor (ej: "SUP001")
    
    Returns:
        dict con resultado de la operacion.
    """
    try:
        pending = list_pending_invoices()
        if not pending["success"]:
            return pending
        
        grouped = {}
        moved_count = 0
        
        for invoice in pending["invoices"]:
            # Si se especifico proveedor, solo procesar ese
            if supplier_id and invoice.get("supplier_id") != supplier_id:
                continue
            
            filename = invoice["filename"]
            
            # Extraer CUIT del contenido del archivo
            supplier_cuit = extract_cuit_from_file(invoice["path"])
            
            if supplier_cuit:
                result = move_invoice_to_folder(filename, supplier_cuit)
                if result["success"]:
                    moved_count += 1
                    if supplier_cuit not in grouped:
                        grouped[supplier_cuit] = []
                    grouped[supplier_cuit].append(filename)
        
        return {
            "success": True,
            "message": f"Se agruparon {moved_count} facturas",
            "grouped_by_cuit": grouped,
            "moved_count": moved_count
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def extract_cuit_from_file(file_path: str) -> Optional[str]:
    """Extrae el CUIT de un archivo de factura.
    
    Args:
        file_path: Ruta al archivo
    
    Returns:
        CUIT encontrado o None
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Buscar patron de CUIT (XX-XXXXXXXX-X o XXXXXXXXXXX)
        import re
        # Patrones comunes de CUIT argentino
        patterns = [
            r'\b\d{2}-\d{8}-\d{1}\b',  # XX-XXXXXXXX-X
            r'\b\d{11}\b',              # XXXXXXXXXXX
            r'CUIT[:\s]*[\d\-]+',       # CUIT: XX-XXXXXXXX-X
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0).replace("CUIT:", "").strip()
        
        return None
        
    except Exception:
        return None


def list_supplier_folders() -> dict:
    """Lista las carpetas de proveedores creadas.
    
    Returns:
        dict con carpetas y contenido.
    """
    try:
        if not INVOICES_DIR.exists():
            return {
                "success": False,
                "error": "Carpeta no existe"
            }
        
        folders = []
        for item in INVOICES_DIR.iterdir():
            if item.is_dir() and item.name.startswith("CUIT-"):
                files = [f.name for f in item.iterdir() if f.is_file()]
                folders.append({
                    "folder_name": item.name,
                    "cuit": item.name.replace("CUIT-", ""),
                    "path": str(item),
                    "invoice_count": len(files),
                    "files": files
                })
        
        return {
            "success": True,
            "folders": folders,
            "count": len(folders)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Exports
__all__ = [
    'list_pending_invoices',
    'create_supplier_folder',
    'move_invoice_to_folder',
    'group_invoices_by_supplier',
    'extract_cuit_from_file',
    'list_supplier_folders'
]