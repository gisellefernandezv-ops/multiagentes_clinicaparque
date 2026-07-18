"""Script para iniciar todos los servicios de InvoiceFlow.

Ejecuta en paralelo:
- Puerto 5000: MCP Toolbox Server
- Puerto 8000: Backend FastAPI
- Puerto 8001: Supplier Service
- Puerto 8002: Contract Service
- Puerto 8003: External Auditor A2A
"""

import subprocess
import sys
import time
import os
from pathlib import Path

# Agregar proyecto a path
PROJECT_ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(PROJECT_ROOT))

def print_banner():
    print("=" * 60)
    print("  InvoiceFlow - Sistema Multiagente de Aprobacion")
    print("=" * 60)
    print()

def check_port(port: int) -> bool:
    """Verifica si un puerto esta disponible."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def wait_for_service(port: int, name: str, timeout: int = 30):
    """Espera a que un servicio este disponible."""
    import httpx
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
            if r.status_code == 200:
                print(f"  [{name}] OK - http://127.0.0.1:{port}")
                return True
        except:
            pass
        time.sleep(1)
    print(f"  [{name}] TIMEOUT - No respondio en {timeout}s")
    return False

def main():
    print_banner()
    
    services = [
        {
            "name": "MCP Toolbox",
            "port": 5000,
            "command": [sys.executable, "-m", "uvicorn", "app.services.toolbox_server.main:app", "--host", "127.0.0.1", "--port", "5000"],
            "required": False,
        },
        {
            "name": "Supplier Service",
            "port": 8001,
            "command": [sys.executable, "-m", "uvicorn", "app.services.supplier_service.main:app", "--host", "127.0.0.1", "--port", "8001"],
            "required": True,
        },
        {
            "name": "Contract Service",
            "port": 8002,
            "command": [sys.executable, "-m", "uvicorn", "app.services.contract_service.main:app", "--host", "127.0.0.1", "--port", "8002"],
            "required": True,
        },
        {
            "name": "External Auditor A2A",
            "port": 8003,
            "command": [sys.executable, "-m", "uvicorn", "a2a.external_auditor_agent.server:app", "--host", "127.0.0.1", "--port", "8003"],
            "required": False,
        },
        {
            "name": "Backend FastAPI",
            "port": 8000,
            "command": [sys.executable, "-m", "uvicorn", "app.backend.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
            "required": True,
        },
    ]
    
    processes = []
    
    print("Verificando puertos...")
    for svc in services:
        if check_port(svc["port"]):
            print(f"  [!] Puerto {svc['port']} ya esta en uso ({svc['name']})")
        else:
            print(f"  [+] Puerto {svc['port']} disponible ({svc['name']})")
    
    print("\nIniciando servicios...\n")
    
    for svc in services:
        if check_port(svc["port"]):
            print(f"  [SKIP] {svc['name']} ya esta corriendo en puerto {svc['port']}")
            continue
            
        print(f"  [STARTING] {svc['name']} (puerto {svc['port']})...")
        
        try:
            # Cambiar al directorio del proyecto
            proc = subprocess.Popen(
                svc["command"],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            processes.append((svc["name"], svc["port"], proc))
            time.sleep(0.5)  # Pequeno delay entre inicio de servicios
        except Exception as e:
            print(f"  [ERROR] {svc['name']}: {e}")
    
    print("\nEsperando a que los servicios esten disponibles...\n")
    
    time.sleep(3)  # Esperar a que arranquen
    
    all_ok = True
    for name, port, proc in processes:
        if proc.poll() is not None:
            # El proceso murio
            stdout, stderr = proc.communicate()
            print(f"  [CRASH] {name} murio. Stdout: {stdout.decode()[:200]}")
            print(f"           Stderr: {stderr.decode()[:200]}")
            all_ok = False
        else:
            if wait_for_service(port, name):
                print(f"  [OK] {name} iniciado")
            else:
                print(f"  [WARN] {name} no respondio a tiempo")
    
    print("\n" + "=" * 60)
    print("Servicios iniciados:")
    print("=" * 60)
    print("  Backend:        http://127.0.0.1:8000/")
    print("  Swagger API:    http://127.0.0.1:8000/docs")
    print("  Supplier:       http://127.0.0.1:8001")
    print("  Contract:      http://127.0.0.1:8002")
    print("  MCP Toolbox:   http://127.0.0.1:5000")
    print("  External Aud:  http://127.0.0.1:8003")
    print("=" * 60)
    print("\nPresiona Ctrl+C para detener todos los servicios.\n")
    
    try:
        # Mantener el script corriendo
        while True:
            time.sleep(1)
            # Verificar que los procesos sigan vivos
            for name, port, proc in processes[:]:
                if proc.poll() is not None:
                    print(f"[!] {name} se detuvo unexpectedly")
                    processes.remove((name, port, proc))
    except KeyboardInterrupt:
        print("\nDeteniendo servicios...")
        for name, port, proc in processes:
            print(f"  Deteniendo {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("Todos los servicios detenidos.")

if __name__ == "__main__":
    main()
