# BUG-003: `loadInbox()` espera wrapper `{files: [...]}` pero backend devuelve array directo

## Severidad: **HIGH**
## Componente: `app/frontend/app.js` función `loadInbox()`
## Detectado por: Inspección del JS contra output real del backend
## Fecha: 2026-07-09

---

## Descripción

```javascript
// línea 128-130
const resp = await fetch(`${API}/inbox`);
const data = await resp.json();
inboxFiles = data.files || [];  // ← espera {files: [...]}
renderInbox();
```

**Backend retorna** (ver `inbox_router.py` línea 60-78):

```python
@router.get("/inbox", response_model=List[InboxItem])
def list_inbox():
    items = []
    ...
    return items  # ← array directo, no envuelto en {files: ...}
```

```json
[
  {"filename": "FC-2026-SUP001-NUEVA-1.txt", "size": 2230, "invoice_id": null, "supplier_id": null, "amount": ""},
  ...
]
```

## Impacto

- `data.files` es `undefined` → `inboxFiles = []`
- `renderInbox()` muestra "No hay facturas en el inbox"
- El usuario no ve las 15 facturas que SÍ están en `app/data/inbox/`

## Fix Propuesto

```javascript
// Opción A: cambiar lectura
inboxFiles = Array.isArray(data) ? data : (data.files || []);

// Opción B (más limpia): backend envuelve la respuesta
# inbox_router.py
@router.get("/inbox")
def list_inbox():
    return {"files": [...], "count": len(items)}
```

Recomiendo **Opción A** porque es menos invasiva y mantiene la API REST estándar.

## Adicional: Mapeo de campos en `renderInbox()`

```javascript
// línea 150-159 - asume campos que no existen
tbody.innerHTML = inboxFiles.map(f => `
    <td><strong>${f.invoice || '-'}</strong></td>     // ← debería ser f.invoice_id
    <td>${f.supplier || '-'}</td>                     // ← debería ser f.supplier_id (código)
    <td class="amount">${formatCurrency(f.amount || 0)}</td>
    ...
`);
```

Backend retorna `invoice_id`, `supplier_id`, `amount`, NO `invoice`, `supplier`.

## Fix Completo

```javascript
async function loadInbox() {
    ...
    const data = await resp.json();
    inboxFiles = Array.isArray(data) ? data : (data.files || []);
    renderInbox();
}

function renderInbox() {
    ...
    tbody.innerHTML = inboxFiles.map(f => `
        <tr>
            <td>📄 ${f.filename}</td>
            <td><strong>${f.invoice_id || '-'}</strong></td>
            <td>${f.supplier_id || '-'}</td>
            <td class="amount">${formatCurrency(parseFloat(f.amount) || 0)}</td>
            <td>${(f.size / 1024).toFixed(1)} KB</td>
            <td><button class="btn-small" onclick="processInvoice('${f.filename}')">Procesar</button></td>
        </tr>
    `).join('');
}
```

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

```javascript
// app/frontend/app.js loadInbox()
- inboxFiles = data.files || [];
+ inboxFiles = Array.isArray(data) ? data : (data.files || []);
```

Además se corrigieron los nombres de campos en `renderInbox()`:
```javascript
- <td><strong>${f.invoice || '-'}</strong></td>     // ← no existe
- <td>${f.supplier || '-'}</td>                     // ← no existe
+ <td><strong>${f.invoice_id || '-'}</strong></td>
+ <td>${f.supplier_id || '-'}</td>
+ <td class="amount">${formatCurrency(parseFloat(f.amount) || 0)}</td>
+ <td>${(f.size / 1024).toFixed(1)} KB</td>
```

## Verificación

Backend `/inbox` ahora se muestra correctamente en pantalla:
- 15 archivos listados
- Cada uno con invoice_id, supplier_id, monto y tamaño