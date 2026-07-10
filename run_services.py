"""Script para iniciar servicios InvoiceFlow."""
import sys
from pathlib import Path

# Agregar la raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Cambiar el directorio actual al proyecto
import os
os.chdir(PROJECT_ROOT)

def start_supplier_service():
    """Inicia el servicio de proveedores."""
    print("[RUNNER] Iniciando Supplier Service...")
    import uvicorn
    from app.services.supplier_service.main import app
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")

def start_contract_service():
    """Inicia el servicio de contratos."""
    print("[RUNNER] Iniciando Contract Service...")
    import uvicorn
    from app.services.contract_service.main import app
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="info")

def start_backend():
    """Inicia el backend principal."""
    print("[RUNNER] Iniciando Backend...")
    import uvicorn
    from app.backend.main import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="InvoiceFlow Service Runner")
    parser.add_argument("service", choices=["supplier", "contract", "backend"], 
                        help="Servicio a iniciar")
    args = parser.parse_args()
    
    if args.service == "supplier":
        start_supplier_service()
    elif args.service == "contract":
        start_contract_service()
    elif args.service == "backend":
        start_backend()
