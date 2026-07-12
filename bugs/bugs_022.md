# BUG-022 — Procesamiento automático de facturas en el Inbox

## Resumen

| Campo | Valor |
|-------|-------|
| **ID** | BUG-022 |
| **Severidad** | HIGH |
| **Componente** | `app/backend/main.py` |
| **Fecha** | 2026-07-15 |
| **Estado** | ✅ RESUELTO |

## Descripción

Cuando se subía una factura al inbox (Drop Folder), se listaba pero no se procesaba automáticamente. El usuario debía apretar el botón "Procesar" manualmente.

## Solución

Se agregó un callback `auto_process_invoice()` que se ejecuta cuando el watcher detecta un archivo nuevo:

```python
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
watcher.start()
```

## Resultado

Ahora cuando se sube una factura al inbox:
1. El watcher detecta el archivo nuevo
2. Lo parsea automáticamente
3. Lo procesa con el orchestrator
4. Lo mueve a `processed/` o `rejected/`

**Ya no es necesario apretar "Procesar" manualmente.**

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `app/backend/main.py` | Callback `auto_process_invoice()` integrado al watcher |

## Verificación

```bash
# Subir una factura al inbox
cp factura.txt app/data/inbox/

# Verificar que se procesó automáticamente (aparece en invoices)
curl http://localhost:8000/invoices | grep "factura.txt"
```

## Flujo Completo

```
Proveedor sube factura
        │
        ▼
Watcher detecta archivo nuevo
        │
        ▼
parse_invoice_file() extrae datos
        │
        ▼
process_invoice() ejecuta guardrails + orchestrator
        │
        ├── APPROVED → mover a processed/
        ├── REJECTED → mover a processed/
        ├── ESCALATED → mover a processed/
        └── ERROR → mover a rejected/
```
