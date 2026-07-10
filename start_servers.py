"""
Script para iniciar todos los servicios de InvoiceFlow.
Ejecutar con: python start_servers.py
"""
import subprocess
import sys
import os
import time
import signal

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    print("=" * 60)
    print("InvoiceFlow — Iniciando Sistema")
    print("=" * 60)
    print(f"Directorio: {os.getcwd()}")
    print()
    
    processes = []
    
    # Servicios a iniciar
    services = [
        ("Supplier Service (8001)", [sys.executable, "-m", "app.services.supplier_service.main"]),
        ("Contract Service (8002)", [sys.executable, "-m", "app.services.contract_service.main"]),
        ("Backend (8000)", [sys.executable, "-m", "uvicorn", "app.backend.main:app", "--host", "127.0.0.1", "--port", "8000"]),
    ]
    
    for name, cmd in services:
        print(f"Iniciando {name}...")
        try:
            p = subprocess.Popen(
                cmd,
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            processes.append((name, p))
            print(f"  ✓ {name} iniciado (PID: {p.pid})")
        except Exception as e:
            print(f"  ✗ Error iniciando {name}: {e}")
    
    print()
    print("=" * 60)
    print("Sistema iniciado")
    print("=" * 60)
    print()
    print("URLs de acceso:")
    print("  - Back Office:     http://localhost:8000/")
    print("  - Supplier Portal: http://localhost:8000/supplier/")
    print("  - Supplier API:    http://localhost:8001/docs")
    print("  - Contract API:    http://localhost:8002/docs")
    print()
    print("Presiona Ctrl+C para detener...")
    print()
    
    try:
        # Mantener el script corriendo
        while True:
            time.sleep(1)
            # Verificar que los procesos sigan vivos
            for name, p in processes[:]:
                if p.poll() is not None:
                    print(f"  ⚠ {name} se detuvo inesperadamente")
                    processes.remove((name, p))
    except KeyboardInterrupt:
        print("\nDeteniendo servicios...")
        for name, p in processes:
            try:
                p.terminate()
                p.wait(timeout=5)
                print(f"  ✓ {name} detenido")
            except:
                try:
                    p.kill()
                    print(f"  ✓ {name} matado")
                except:
                    pass
        print("\nSistema detenido.")

if __name__ == "__main__":
    main()
