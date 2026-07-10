# BUG-002: Dashboard JS lee campos incorrectos del JSON de respuesta

## Severidad: **HIGH** (dependiente de BUG-001)
## Componente: `app/frontend/app.js` función `loadDashboard()`
## Detectado por: Inspección del JS contra output real del backend
## Fecha: 2026-07-09

---

## Descripción

`loadDashboard()` accede a campos que NO existen en la respuesta del backend.

### Campos que el JS espera (incorrectos):

```javascript
// línea 77-81
document.getElementById('stat-approved').textContent = data.approved || 0;
document.getElementById('stat-escalated').textContent = data.escalated || 0;
document.getElementById('stat-rejected').textContent = data.rejected || 0;
document.getElementById('stat-total').textContent = formatCurrency(data.total_approved);

// línea 83
renderRecentPayments(data.recent_payments || []);
```

### Estructura REAL del endpoint `/dashboard`:

```json
{
  "inbox_count": 15,
  "processed_count": 0,
  "rejected_files": 0,
  "decisions": {
    "APPROVED": 5,
    "REJECTED": 2,
    "ESCALATED": 1
  },
  "total_amount_approved": 393000.0,
  "recent": [ {...}, {...} ]
}
```

## Mapeo de campos

| JS espera        | Backend retorna            |
|------------------|----------------------------|
| `data.approved`  | `data.decisions.APPROVED`  |
| `data.rejected`  | `data.decisions.REJECTED`  |
| `data.escalated` | `data.decisions.ESCALATED` |
| `data.total_approved` | `data.total_amount_approved` |
| `data.recent_payments` | `data.recent`         |

## Impacto

Incluso arreglando BUG-001, el dashboard mostraría valores incorrectos:
- Cards siempre mostrarían `0` porque `.approved || 0` evalúa `undefined` → 0
- El total aprobado mostraría `$0` (porque `formatCurrency(undefined)` da `$ 0`)
- La tabla "Últimos pagos" mostraría "No hay pagos recientes"

## Fix Propuesto

```javascript
// loadDashboard() corregido
document.getElementById('stat-inbox').textContent = data.inbox_count || 0;
document.getElementById('stat-approved').textContent = data.decisions?.APPROVED || 0;
document.getElementById('stat-rejected').textContent = data.decisions?.REJECTED || 0;
document.getElementById('stat-escalated').textContent = data.decisions?.ESCALATED || 0;
document.getElementById('stat-total').textContent = formatCurrency(data.total_amount_approved);

renderRecentPayments(data.recent || []);
```

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

```javascript
// app/frontend/app.js loadDashboard()
- document.getElementById('stat-approved').textContent = data.approved || 0;
- document.getElementById('stat-escalated').textContent = data.escalated || 0;
- document.getElementById('stat-rejected').textContent = data.rejected || 0;
- document.getElementById('stat-total').textContent = formatCurrency(data.total_approved);
- renderRecentPayments(data.recent_payments || []);
+ const dec = data.decisions || {};
+ document.getElementById('stat-inbox').textContent = data.inbox_count ?? 0;
+ document.getElementById('stat-approved').textContent = dec.APPROVED ?? 0;
+ document.getElementById('stat-rejected').textContent = dec.REJECTED ?? 0;
+ document.getElementById('stat-escalated').textContent = dec.ESCALATED ?? 0;
+ document.getElementById('stat-total').textContent = formatCurrency(data.total_amount_approved);
+ renderRecentPayments(data.recent || []);
```

## Verificación

Backend `/dashboard` retorna:
```json
{
  "inbox_count": 15,
  "decisions": {"APPROVED": 3, "REJECTED": 8, "ESCALATED": 3},
  "total_amount_approved": 150000.0,
  "recent": [...]
}
```

Ahora el dashboard muestra correctamente:
- 📥 En Inbox: **15**
- ✅ Aprobadas: **3**
- ❌ Rechazadas: **8**
- ⏫ Escaladas: **3**
- 💰 Total Aprobado: **$ 150.000,00**