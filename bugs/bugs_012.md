# BUG-012: Dashboard no concuerda con listas + Inbox incompleto + falta modal de detalle

## Severidad: **HIGH**
## Componente: `app/frontend/app.js` + `app/backend/watcher.py` + `app/frontend/index.html`
## Detectado por: Usuario ve "3 aprobadas" en stats pero solo 1 en el listado
## Fecha: 2026-07-09

---

## Descripción

El usuario reporta **3 problemas relacionados** en el BackOffice:

### 1. Discrepancia dashboard ↔ listado
- Stats dicen: `Aprobadas: 3, Rechazadas: 8, Escaladas: 3`
- "Últimos pagos" muestra solo top 10
- Solo 1 de los 10 visibles es APPROVED
- **El usuario piensa que hay un bug** porque los números no concuerdan visualmente

**Causa**: El endpoint `/dashboard` muestra `recent = top 10 ORDER BY id DESC`,
mientras que los contadores son sobre TODA la tabla. Las decisiones viejas
quedan fuera del top 10.

### 2. Inbox incompleto
- 15 archivos en `app/data/inbox/`
- Frontend muestra `invoice_id: null, supplier_id: null, amount: ""`
- **El parser TXT no soporta el formato FACTURA** que usan los archivos

**Causa**: `parse_invoice_file()` en `watcher.py` solo busca formato `key: value`,
pero los archivos reales tienen formato seccionado:
```
Numero: FC-2026-SUP001-NUEVA-1
Fecha: 28/06/2026
CUIT: 30-71234567-0
TOTAL: ARS $     25,000.00
```

### 3. Sin modal para ver factura
- El usuario pide un **ojito (eye icon)** en cada fila del inbox/historial
- Al hacer click debe abrir un modal con el detalle completo de la factura

## Fix Aplicado

### Fix 1: Dashboard con distribución balanceada
Cambiar `recent` para incluir muestra de TODAS las decisiones (no solo top 10):

```python
# inbox_router.py - /dashboard
# Top 3 de cada decision (APPROVED, REJECTED, ESCALATED)
recent_balanced = []
for d in ["APPROVED", "REJECTED", "ESCALATED"]:
    c.execute("SELECT ... WHERE decision = ? ORDER BY id DESC LIMIT 3", (d,))
    recent_balanced.extend(c.fetchall())
# Ordenar todo por id DESC para tener vista cronológica
recent_balanced.sort(key=lambda r: r["id"], reverse=True)
```

### Fix 2: Parser de inbox para formato FACTURA
Detectar y parsear tanto `key: value` simple como FACTURA seccionado:

```python
# watcher.py - parse_invoice_file() ampliado
if path.suffix.lower() == ".txt":
    # Detectar formato FACTURA
    if "FACTURA" in text.upper() and "TOTAL: ARS" in text.upper():
        return _parse_factura_format(text)
    # Formato key: value
    ...
```

### Fix 3: Modal de detalle con eye icon
- Agregar columna `Acción` con botón 👁️ en tablas de inbox e historial
- Click abre modal con todos los campos de la factura

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

### Fix 1: Dashboard con `recent_balanced`
`app/backend/inbox_router.py` `/dashboard` ahora incluye 3 pagos de cada decisión:

```python
recent_balanced = []
for d in ("APPROVED", "REJECTED", "ESCALATED"):
    rows = conn.execute(
        "SELECT ... FROM payments WHERE decision = ? ORDER BY id DESC LIMIT 3",
        (d,),
    ).fetchall()
    recent_balanced.extend([dict(r) for r in rows])
```

### Fix 2: Parser de FACTURA TXT
`app/backend/watcher.py` nueva función `_parse_factura_txt()`:

```python
def _parse_factura_txt(text, filename):
    import re
    result = {}
    m = re.search(r"[Nn]umero[:\s]+([A-Z0-9\-]+)", text)
    if m: result["invoice_id"] = m.group(1).strip()
    m = re.search(r"[Ff]echa[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m: result["invoice_date"] = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    # ... vencimiento, CUIT, total
    m = re.search(r"\bTOTAL\b[:\s]+(?:ARS\s+)?\$\s*([\d,\.]+)", text)  # \b evita SUBTOTAL
    if m: result["amount"] = parse_amount(m.group(1))
    fname_match = re.search(r"SUP(\d{3})", filename)
    if fname_match: result["supplier_id"] = f"SUP{fname_match.group(1)}"
    return result
```

### Fix 3: Modal de detalle con ojo
`app/frontend/app.js` agregó:
- `openInvoiceModal(invoice)` - modal con todos los campos + audit del A2A si hay
- `openInboxFileModal(file)` - modal del archivo del inbox
- `closeModal()` - cierra con ESC o click fuera
- Botón `👁️` en cada fila de Dashboard / Inbox / Historial

`app/frontend/style.css` agregó CSS para `.modal-overlay`, `.modal-content`, `.btn-icon`, animaciones.

`app/frontend/index.html` bumpeado a `?v=2026070904`.

## Verificación

```
=== DASHBOARD ===
Decisions: {'APPROVED': 3, 'REJECTED': 23, 'ESCALATED': 3}
Recent balanced count: 9  (3 de cada decision)
  REJECTED   UNKNOWN                   $0
  REJECTED   UNKNOWN                   $0
  REJECTED   UNKNOWN                   $0
  ESCALATED  GC-GC004-RUN              $600,000
  APPROVED   GC-GC001-RUN              $50,000
  ESCALATED  A2A-INTEGRATION-TEST      $700,000
  ESCALATED  BR07-TEST                 $600,000
  APPROVED   FLOW-A-TEST               $50,000
  APPROVED   GC001-AUTO-TEST           $50,000     ← ahora se ven los 3 APPROVED

=== INBOX ===
Inbox count: 15
  FC-2026-SUP001-NUEVA-1.txt  inv=FC-2026-SUP001-NUEVA-1 sup=SUP001 amt=25000.0
  FC-2026-SUP001-NUEVA-2.txt  inv=FC-2026-SUP001-NUEVA-2 sup=SUP001 amt=32000.0
  ... (15 con todos los campos completos)

=== JS check ===
  Has recent_balanced: True
  Has openInvoiceModal: True
  Has openInboxFileModal: True
  Has closeModal: True
  Has btn-icon: True

=== CSS check ===
  Has .modal-overlay: True
  Has .modal-content: True
  Has .btn-icon: True
  Has @keyframes slideUp: True
```