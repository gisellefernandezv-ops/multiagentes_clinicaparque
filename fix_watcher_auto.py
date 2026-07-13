"""Fix watcher to auto-process invoices."""
from pathlib import Path

content = Path('app/backend/main.py').read_text(encoding='utf-8')

# Old import
old_import = "from .watcher import InboxWatcher"
new_import = """from .watcher import InboxWatcher, parse_invoice_file, move_file
from .orchestrator import process_invoice"""

if old_import in content:
    content = content.replace(old_import, new_import)
    print("Import actualizado")
else:
    print("No se encontro import")

# Old watcher setup
old_watcher = '''    if settings.enable_watcher:
        watcher = InboxWatcher()
        watcher.start()'''

new_watcher = '''    if settings.enable_watcher:
        def auto_process_invoice(path: Path):
            """Procesa automaticamente una factura nueva en el inbox."""
            print(f"[watcher] Procesando archivo: {path.name}")
            try:
                invoice = parse_invoice_file(path)
                if not invoice:
                    print(f"[watcher] No se pudo parsear {path.name}, moviendo a rejected/")
                    move_file(path, settings.rejected_dir)
                    return
                
                result = process_invoice(invoice, source_file=str(path))
                decision = result.get("decision", "UNKNOWN")
                
                if decision in {"APPROVED", "REJECTED", "ESCALATED"}:
                    move_file(path, settings.processed_dir)
                    print(f"[watcher] Procesada: {path.name} -> {decision}")
                else:
                    print(f"[watcher] Decision desconocida: {decision} para {path.name}")
                    
            except Exception as e:
                print(f"[watcher] Error procesando {path.name}: {e}")
                move_file(path, settings.rejected_dir)
        
        watcher = InboxWatcher(on_new_file=auto_process_invoice)
        watcher.start()'''

if old_watcher in content:
    content = content.replace(old_watcher, new_watcher)
    print("Watcher actualizado con procesamiento automatico")
else:
    print("No se encontro watcher setup")

Path('app/backend/main.py').write_text(content, encoding='utf-8')
print("Archivo guardado")
