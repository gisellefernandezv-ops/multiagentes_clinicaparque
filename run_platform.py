import os
import sys

# Cambiar al directorio del proyecto
PROJECT_DIR = r"c:\Users\gisel\OneDrive\Escritorio\tp_multiagentes\invoice_approval_system"
os.chdir(os.path.join(PROJECT_DIR, "platform", "backend"))

# Importar y ejecutar
sys.path.insert(0, os.getcwd())

from main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
