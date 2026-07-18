"""Script de inicio completo para InvoiceFlow.

Este script inicia y mantiene todos los servicios del sistema:
- Puerto 5000: MCP Toolbox Server
- Puerto 8001: Supplier Service
- Puerto 8002: Contract Service
- Puerto 8003: External Auditor A2A
- Puerto 8000: Backend FastAPI (principal)

Uso:
    python start_all.py          # Iniciar todos los servicios
    python start_all.py status  # Ver estado de los servicios
    python start_all.py stop    # Detener todos los servicios
    python start_all.py restart  # Reiniciar todos los servicios
"""

import subprocess
import sys
import time
import os
import signal
import socket
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Agregar proyecto a path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Puerto del backend (para saber si el sistema está corriendo)
BACKEND_PORT = 8000

# Configuración de servicios
SERVICES = [
    {
        "name": "MCP Toolbox",
        "port": 5000,
        "module": "app.services.toolbox_server.main:app",
        "required": False,  # Opcional - el sistema funciona sin él
        "description": "Herramientas predefinidas para validación"
    },
    {
        "name": "Supplier Service",
        "port": 8001,
        "module": "app.services.supplier_service.main:app",
        "required": True,
        "description": "ABM de proveedores y contratos"
    },
    {
        "name": "Contract Service",
        "port": 8002,
        "module": "app.services.contract_service.main:app",
        "required": True,
        "description": "RAG con ChromaDB"
    },
    {
        "name": "External Auditor",
        "port": 8003,
        "module": "a2a.external_auditor_agent.server:app",
        "required": False,  # Opcional - solo para facturas > $500k
        "description": "Auditoría A2A de facturas escaladas"
    },
    {
        "name": "Backend FastAPI",
        "port": 8000,
        "module": "app.backend.main:app",
        "required": True,
        "description": "API principal con UI"
    },
]


def is_port_in_use(port: int) -> bool:
    """Verifica si un puerto está en uso."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect(('127.0.0.1', port))
        sock.close()
        return True
    except:
        return False


def check_service_health(port: int, timeout: int = 5) -> Tuple[bool, str]:
    """Verifica si un servicio está respondiendo."""
    import httpx
    try:
        response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            return True, data.get("status", "ok")
        return False, f"HTTP {response.status_code}"
    except httpx.ConnectError:
        return False, "connection_error"
    except httpx.TimeoutException:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:50]


def get_process_on_port(port: int) -> Optional[int]:
    """Obtiene el PID del proceso en un puerto (Windows)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.split("\n"):
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                for part in reversed(parts):
                    try:
                        return int(part)
                    except:
                        continue
    except:
        pass
    return None


def kill_process_on_port(port: int) -> bool:
    """Detiene el proceso en un puerto."""
    pid = get_process_on_port(port)
    if pid:
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True)
            print(f"  [KILL] Proceso {pid} en puerto {port} detenido")
            time.sleep(1)
            return True
        except:
            pass
    return False


def stop_all_services() -> None:
    """Detiene todos los servicios."""
    print("\n" + "=" * 60)
    print("  DETENIENDO SERVICIOS")
    print("=" * 60 + "\n")
    
    for service in reversed(SERVICES):
        port = service["port"]
        if is_port_in_use(port):
            print(f"  Deteniendo {service['name']} (puerto {port})...")
            kill_process_on_port(port)
    
    print("\n  Todos los servicios detenidos.")


def start_service(service: Dict) -> Optional[subprocess.Popen]:
    """Inicia un servicio individual."""
    port = service["port"]
    name = service["name"]
    module = service["module"]
    
    # Verificar si ya está corriendo
    if is_port_in_use(port):
        return None
    
    try:
        # Cambiar al directorio del proyecto
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                module,
                "--host", "127.0.0.1",
                "--port", str(port),
            ],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
        )
        return proc
    except Exception as e:
        print(f"  [ERROR] {name}: {e}")
        return None


def wait_for_service(port: int, timeout: int = 30) -> bool:
    """Espera a que un servicio esté disponible."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(port):
            time.sleep(0.5)  # Esperar a que responda
            ok, status = check_service_health(port)
            if ok:
                return True
        time.sleep(0.5)
    return False


def check_all_services_status() -> Dict[int, Dict]:
    """Verifica el estado de todos los servicios."""
    status = {}
    for service in SERVICES:
        port = service["port"]
        in_use = is_port_in_use(port)
        if in_use:
            ok, health_status = check_service_health(port)
            status[port] = {
                "name": service["name"],
                "in_use": True,
                "healthy": ok,
                "status": health_status
            }
        else:
            status[port] = {
                "name": service["name"],
                "in_use": False,
                "healthy": False,
                "status": "not_running"
            }
    return status


def print_status(status: Dict) -> None:
    """Imprime el estado de los servicios."""
    print("\n" + "=" * 60)
    print("  ESTADO DE SERVICIOS - InvoiceFlow")
    print("=" * 60 + "\n")
    
    all_healthy = True
    required_healthy = True
    
    for service in SERVICES:
        port = service["port"]
        info = status.get(port, {})
        name = service["name"]
        required = service["required"]
        desc = service["description"]
        
        if info.get("in_use"):
            if info.get("healthy"):
                symbol = "🟢"
                status_text = info.get("status", "ok")
            else:
                symbol = "🟡"
                status_text = info.get("status", "unknown")
                all_healthy = False
                if required:
                    required_healthy = False
        else:
            symbol = "🔴"
            status_text = "No corriendo"
            all_healthy = False
            if required:
                required_healthy = False
        
        required_marker = " [REQUERIDO]" if required else ""
        print(f"  {symbol} {name} (puerto {port}){required_marker}")
        print(f"     {status_text} - {desc}")
        print()
    
    print("-" * 60)
    if required_healthy:
        print("  Estado: 🟢 Sistema OPERATIVO")
    elif all_healthy:
        print("  Estado: 🟡 Sistema DEGRADADO (algunos servicios opcionales no disponibles)")
    else:
        print("  Estado: 🔴 Sistema CON PROBLEMAS (servicios requeridos caídos)")
    print("=" * 60 + "\n")


def start_all_services() -> bool:
    """Inicia todos los servicios."""
    print("\n" + "=" * 60)
    print("  INICIANDO SERVICIOS - InvoiceFlow")
    print("=" * 60 + "\n")
    
    # Primero verificar/detener puertos en uso
    print("[1/4] Verificando puertos...")
    for service in SERVICES:
        port = service["port"]
        if is_port_in_use(port):
            print(f"  Puerto {port} ({service['name']}) en uso, deteniendo...")
            kill_process_on_port(port)
    
    time.sleep(1)
    
    # Iniciar servicios en orden (primero los microservicios, luego el backend)
    print("\n[2/4] Iniciando microservicios...")
    processes = []
    
    # Orden de inicio: primero independientes, luego el backend
    startup_order = [1, 2, 3, 0, 4]  # Índices en SERVICES
    
    for idx in startup_order:
        service = SERVICES[idx]
        port = service["port"]
        name = service["name"]
        
        print(f"  Iniciando {name} (puerto {port})...")
        
        # Verificar que el puerto esté libre
        if is_port_in_use(port):
            print(f"    [SKIP] Ya está corriendo")
            continue
        
        proc = start_service(service)
        if proc:
            processes.append((service, proc))
            print(f"    [OK] Proceso iniciado (PID: {proc.pid})")
        else:
            print(f"    [SKIP] Ya estaba corriendo o error")
    
    # Esperar a que arranquen
    print("\n[3/4] Esperando a que los servicios estén disponibles...")
    
    started = []
    for service, proc in processes:
        port = service["port"]
        name = service["name"]
        
        if wait_for_service(port, timeout=20):
            print(f"  🟢 {name} disponible")
            started.append((service, proc))
        else:
            print(f"  🔴 {name} TIMEOUT")
    
    # Verificar estado final
    print("\n[4/4] Verificando estado final...")
    time.sleep(2)
    status = check_all_services_status()
    
    print_status(status)
    
    return len(started) > 0


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="InvoiceFlow Service Manager")
    parser.add_argument("action", nargs="?", default="start",
                       choices=["start", "stop", "status", "restart"],
                       help="Acción a realizar (start, stop, status, restart)")
    args = parser.parse_args()
    
    if args.action == "stop":
        stop_all_services()
        
    elif args.action == "status":
        status = check_all_services_status()
        print_status(status)
        
    elif args.action == "restart":
        stop_all_services()
        time.sleep(2)
        start_all_services()
        
    else:  # start
        # Verificar estado actual
        status = check_all_services_status()
        
        # Contar servicios requeridos que están corriendo
        required_running = sum(
            1 for s in SERVICES 
            if s["required"] and status.get(s["port"], {}).get("in_use")
        )
        
        if required_running >= 3:  # Al menos 3 de 4 requeridos
            print("\n🟢 Los servicios principales ya están corriendo.")
            print_status(status)
            
            # Preguntar si quiere reiniciar
            response = input("\n¿Querés reiniciar los servicios? (s/n): ").strip().lower()
            if response == 's':
                stop_all_services()
                time.sleep(2)
                start_all_services()
            else:
                print("\nNo se realizó ningún cambio. Para detener usar: python start_all.py stop")
        else:
            start_all_services()


if __name__ == "__main__":
    main()
