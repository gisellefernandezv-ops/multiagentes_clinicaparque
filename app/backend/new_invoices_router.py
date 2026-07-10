"""Router para la carpeta new invoices y agente agrupador."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

# Rutas del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[2]
NEW_INVOICES_DIR = PROJECT_ROOT / "data" / "new invoices"


router = APIRouter(prefix="/new-invoices", tags=["new-invoices"])


def extract_cuit_from_file(file_path: Path) -> Optional[str]:
    """Extrae el CUIT de un archivo de factura."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Patrones de CUIT argentino
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


@router.get("")
def list_new_invoices():
    """Lista todas las facturas en la carpeta new invoices."""
    if not NEW_INVOICES_DIR.exists():
        return JSONResponse({
            "success": True,
            "files": [],
            "count": 0,
            "folder": str(NEW_INVOICES_DIR)
        })
    
    files = []
    for file_path in NEW_INVOICES_DIR.iterdir():
        if file_path.is_file() and file_path.suffix in ['.txt', '.pdf', '.json']:
            # Extraer supplier_id del nombre si existe
            filename = file_path.stem
            supplier_id = None
            if "SUP" in filename:
                parts = filename.split("-")
                for p in parts:
                    if p.startswith("SUP"):
                        supplier_id = p
                        break
            
            files.append({
                "filename": file_path.name,
                "supplier_id": supplier_id,
                "path": str(file_path),
                "size_kb": round(file_path.stat().st_size / 1024, 2)
            })
    
    return {
        "success": True,
        "files": files,
        "count": len(files),
        "folder": str(NEW_INVOICES_DIR)
    }


@router.get("/content")
def get_invoice_content(filename: str):
    """Obtiene el contenido de una factura."""
    if not NEW_INVOICES_DIR.exists():
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    
    file_path = NEW_INVOICES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return {
            "filename": filename,
            "content": content,
            "size_kb": round(file_path.stat().st_size / 1024, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/group-invoices")
def group_invoices():
    """Ejecuta el agente agrupador - crea carpetas por CUIT y mueve facturas."""
    if not NEW_INVOICES_DIR.exists():
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    
    import shutil
    
    grouped = {}
    moved_count = 0
    
    # Listar archivos sueltos (no en subcarpetas)
    for file_path in NEW_INVOICES_DIR.iterdir():
        if file_path.is_file() and file_path.suffix in ['.txt', '.pdf', '.json']:
            # Extraer CUIT del contenido
            supplier_cuit = extract_cuit_from_file(file_path)
            
            if supplier_cuit:
                # Normalizar CUIT para nombre de carpeta
                cuit_normalized = supplier_cuit.replace("-", "").replace(" ", "")
                folder_name = f"CUIT-{cuit_normalized}"
                folder_path = NEW_INVOICES_DIR / folder_name
                
                # Crear carpeta si no existe
                folder_path.mkdir(parents=True, exist_ok=True)
                
                # Mover archivo
                dest_path = folder_path / file_path.name
                shutil.move(str(file_path), str(dest_path))
                
                moved_count += 1
                
                if folder_name not in grouped:
                    grouped[folder_name] = []
                grouped[folder_name].append(file_path.name)
    
    return {
        "success": True,
        "message": f"Se movieron {moved_count} facturas",
        "moved_count": moved_count,
        "grouped_by_cuit": grouped,
        "folders_created": list(grouped.keys())
    }


@router.get("/folders")
def list_supplier_folders():
    """Lista las carpetas de proveedores ya creadas."""
    if not NEW_INVOICES_DIR.exists():
        return {"success": True, "folders": [], "count": 0}
    
    folders = []
    for item in NEW_INVOICES_DIR.iterdir():
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
