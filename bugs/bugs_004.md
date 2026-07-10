# BUG-004: `loadHistory()` espera `{invoices: [...]}` pero backend devuelve array

## Severidad: **HIGH**
## Componente: `app/frontend/app.js` función `loadHistory()`
## Detectado por: Inspección del JS contra output real
## Fecha: 2026-07-09

---

## Descripción

```javascript
// línea 261-264
const resp = await fetch(`${API}/invoices`);
const data = await resp.json();
renderHistory(data.invoices || []);  // ← espera wrapper
```

**Backend retorna** (ver `inbox_router.py` línea 158-176):

```python
@router.get("/invoices")
def list_processed_invoices(limit: int = 50, decision: Optional[str] = None):
    ...
    return [dict(r) for r in rows]  # ← array directo
```

## Estructura devuelta por SQLite (tabla `payments`)

```json
[
  {
    "id": 1,
    "invoice_id": "INV-2025-001",
    "supplier_id": "SUP001",
    "amount": 45000.0,
    "decision": "APPROVED",
    "rejection_reason": "",
    "payment_status": "PENDING_PAYMENT",
    "confirmation_id": "PAY-001",
    "registered_at": "2026-07-04T22:59:00.200280Z"
  },
  ...
]
```

## Fix

```javascript
async function loadHistory() {
    ...
    const data = await resp.json();
    renderHistory(Array.isArray(data) ? data : (data.invoices || []));
}
```

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

```javascript
// app/frontend/app.js loadHistory()
- renderHistory(data.invoices || []);
+ const list = Array.isArray(data) ? data : (data.invoices || []);
+ renderHistory(list);
```

## Verificación

Backend `/invoices` ahora se muestra correctamente en la pantalla de Historial:
- 14 pagos registrados visibles
- Cada uno con invoice_id, supplier_id, monto, decisión, confirmation_id, payment_status, rejection_reason