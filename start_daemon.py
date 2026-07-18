"""Daemon de supervisión para InvoiceFlow.

Este script mantiene todos los servicios corriendo automáticamente.
Si un servicio se cae, lo reinicia.

Uso:
    python start_daemon.py          # Iniciar daemon de supervision
    python start_daemon.py --once   # Verificar una vez y salir
    python start_daemon.py --status # Solo mostrar estado
"""

import subprocess
import sys
import time
import os
import socket
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import argparse
import signal

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Servicios requeridos (puerto, nombre)
SERVICES_CONFIG = [
    (8001, "Supplier Service"),
    (8002, "Contract Service"),
    (8000, "Backend FastAPI"),
]

# Servicios opcionales
OPTIONAL_SERVICES = [
    (5000, "MCP Toolbox"),
    (8003, "External Auditor"),
]

# Archivos de módulo
SERVICE_MODULES = {
    8000: "app.backend.main:app",
    8001: "app.services.supplier_service.main:app",
    8002: "app.services.contract_service.main:app",
    5000: "app.services.toolbox_server.main:app",
    8003: "a2a.external_auditor_agent.server:app",
}


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


def get_process_pid(port: int) -> Optional[int]:
    """Obtiene el PID del proceso en un puerto."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
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


def check_service_health(port: int) -> Tuple[bool, str]:
    """Verifica si un servicio responde correctamente."""
    import httpx
    try:
        response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=3)
        if response.status_code == 200:
            return True, "healthy"
        return False, f"HTTP {response.status_code}"
    except httpx.ConnectError:
        return False, "connection_error"
    except httpx.TimeoutException:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:30]


def get_all_service_status() -> Dict:
    """Obtiene el estado de todos los servicios."""
    status = {}
    
    for port, name in SERVICES_CONFIG:
        in_use = is_port_in_use(port)
        pid = get_process_pid(port) if in_use else None
        healthy, health_msg = check_service_health(port) if in_use else (False, "not_running")
        
        status[port] = {
            "name": name,
            "in_use": in_use,
            "pid": pid,
            "healthy": healthy,
            "health_msg": health_msg,
            "required": True
        }
    
    for port, name in OPTIONAL_SERVICES:
        in_use = is_port_in_use(port)
        pid = get_process_pid(port) if in_use else None
        healthy, health_msg = check_service_health(port) if in_use else (False, "not_running")
        
        status[port] = {
            "name": name,
            "in_use": in_use,
            "pid": pid,
            "healthy": healthy,
            "health_msg": health_msg,
            "required": False
        }
    
    return status


def start_service(port: int) -> Optional[int]:
    """Inicia un servicio y devuelve su PID."""
    if is_port_in_use(port):
        return get_process_pid(port)
    
    module = SERVICE_MODULES.get(port)
    if not module:
        return None
    
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", module, "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        return proc.pid
    except Exception as e:
        print(f"[ERROR] No se pudo iniciar servicio en puerto {port}: {e}")
        return None


def kill_service(port: int) -> bool:
    """Detiene un servicio."""
    pid = get_process_pid(port)
    if pid:
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            time.sleep(1)
            return True
        except:
            pass
    return False


def print_status(status: Dict, compact: bool = False) -> None:
    """Imprime el estado de los servicios."""
    if compact:
        required_ok = sum(1 for s in status.values() if s["required"] and s["healthy"])
        total_required = sum(1 for s in status.values() if s["required"])
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ", end="")
        
        for port, info in sorted(status.items()):
            if info["healthy"]:
                print("🟢", end="")
            elif info["in_use"]:
                print("🟡", end="")
            else:
                print("🔴", end="")
        
        print(f" ({required_ok}/{total_required} requeridos)")
    else:
        print("\n" + "=" * 50)
        print("  ESTADO DE SERVICIOS")
        print("=" * 50)
        
        for port, info in sorted(status.items()):
            name = info["name"]
            if info["healthy"]:
                symbol = "🟢"
            elif info["in_use"]:
                symbol = "🟡"
            else:
                symbol = "🔴"
            
            required = " [REQ]" if info["required"] else ""
            pid = f" (PID:{info['pid']})" if info["pid"] else ""
            
            print(f"  {symbol} {name} - {info['health_msg']}{required}{pid}")
        
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="InvoiceFlow Service Supervisor")
    parser.add_argument("--once", action="store_true", help="Solo verificar una vez y salir")
    parser.add_argument("--status", action="store_true", help="Solo mostrar estado")
    parser.add_argument("--interval", type=int, default=30, help="Intervalo de verificacion (segundos)")
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("  InvoiceFlow Service Supervisor")
    print("=" * 50)
    
    # Modo status
    if args.status:
        status = get_all_service_status()
        print_status(status)
        return
    
    # Modo una vez
    if args.once:
        status = get_all_service_status()
        print_status(status)
        
        # Verificar y reiniciar si es necesario
        needs_restart = []
        for port, info in status.items():
            if not info["healthy"]:
                needs_restart.append(port)
        
        if needs_restart:
            print(f"\n[INFO] Servicios que necesitan reinicio: {needs_restart}")
            for port in needs_restart:
                print(f"  Iniciando puerto {port}...")
                start_service(port)
            
            time.sleep(5)
            status = get_all_service_status()
            print_status(status)
        else:
            print("\n[OK] Todos los servicios están corriendo correctamente")
        return
    
    # Modo daemon
    print("\n[INFO] Iniciando modo supervisión...")
    print(f"[INFO] Intervalo de verificación: {args.interval} segundos")
    print("[INFO] Presionar Ctrl+C para detener")
    print()
    
    # Contadores
    restart_counts = {port: 0 for port in SERVICE_MODULES.keys()}
    last_check = datetime.now()
    
    try:
        while True:
            status = get_all_service_status()
            
            # Imprimir estado compacto cada vez
            print_status(status, compact=True)
            
            # Reiniciar servicios caídos
            for port, info in status.items():
                if not info["healthy"]:
                    name = info["name"]
                    restart_counts[port] += 1
                    
                    # Detener si está colgado
                    if info["in_use"]:
                        print(f"    Reiniciando {name} (intento #{restart_counts[port]})...")
                        kill_service(port)
                        time.sleep(2)
                    
                    # Iniciar
                    pid = start_service(port)
                    if pid:
                        print(f"    {name} iniciado (PID: {pid})")
                    else:
                        print(f"    Error iniciando {name}")
            
            last_check = datetime.now()
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\n\n[INFO] Deteniendo supervisor...")
        print("[INFO] Los servicios siguen corriendo.")
        print("[INFO] Para detener servicios: python start_all.py stop")


if __name__ == "__main__":
    main()
