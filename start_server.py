"""Script simple para iniciar el servidor backend."""
import sys
import os

# El directorio raíz del proyecto (tp_multiagentes)
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # De start_server.py a tp_multiagentes
backend_dir = os.path.join(root_dir, "invoice_approval_system", "platform", "backend")

# sys.path: primero backend_dir (para imports locales), luego root_dir (para invoice_approval_system)
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

os.chdir(backend_dir)

if __name__ == "__main__":
    import uvicorn
    print("Iniciando servidor en http://127.0.0.1:8005")
    uvicorn.run(
        "invoice_approval_system.platform.backend.main:app",
        host="0.0.0.0",
        port=8005,
        log_level="info",
        reload=False,
    )
