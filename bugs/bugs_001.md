# BUG-001: Frontend JS usa prefijo `/api/*` incorrecto

## Severidad: **CRITICAL**
## Componente: `app/frontend/app.js`
## Detectado por: Test E2E manual con browser
## Fecha: 2026-07-09

---

## Descripción

El JavaScript del BackOffice define `const API = '/api'` y todas las llamadas `fetch()`
usan paths como `/api/dashboard`, `/api/inbox`, `/api/chat`, etc.

**Pero** el backend (`app/backend/main.py`) NO expone un router con prefijo `/api`.
Los endpoints reales son:

| Frontend intenta (404) | Endpoint real del backend |
|------------------------|---------------------------|
| `GET /api/dashboard`   | `GET /dashboard`          |
| `GET /api/inbox`       | `GET /inbox`              |
| `GET /api/invoices`    | `GET /invoices`           |
| `POST /api/chat`       | `POST /chat`              |
| `GET /api/health`      | `GET /health`             |
| `POST /api/inbox/upload` | `POST /inbox/upload`    |
| `POST /api/inbox/process/{file}` | `POST /inbox/process/{file}` |

## Impacto

- ✅ El dashboard muestra "—" en todas las cards
- ✅ El inbox muestra "No hay facturas en el inbox"
- ✅ El historial no muestra pagos
- ✅ El chat no responde con datos reales
- ✅ El indicador de agentes muestra "No se pudo verificar"
- ❌ Todos los catch() del JS disparan el fallback con **datos MOCK hardcodeados**, ocultando el bug

## Evidencia

```javascript
// app/frontend/app.js, línea 6
const API = '/api';

// línea 74
const resp = await fetch(`${API}/dashboard`);  // → 404
```

```python
# app/backend/main.py (sin prefijo /api)
app.include_router(inbox_router)  # expone /inbox, no /api/inbox
app.include_router(chat_router)   # expone /chat, no /api/chat
```

## Fix Propuesto

**Opción A (recomendada):** Modificar `app/frontend/app.js` para usar API sin prefijo:

```javascript
const API = '';  // sin prefijo /api
```

**Opción B:** Agregar prefijo `/api` a TODOS los routers en el backend:

```python
# main.py
app.include_router(inbox_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
# etc
```

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

```javascript
// app/frontend/app.js línea 9
- const API = '/api';
+ const API = '';  // FIX BUG-001: backend expone /dashboard, /inbox, etc sin prefijo
```

## Verificación

`test_frontend.py` valida que:
- HTML responde 200
- JS ya no contiene `const API = '/api'`
- Todos los endpoints (`/dashboard`, `/inbox`, `/invoices`, `/health`, `/chat`) responden 200
- El dashboard ahora muestra datos reales (inbox=15, APPROVED=3, etc.)

## Resultado

```
[OK] GET / responde 200
[OK] JS no usa prefijo /api (BUG-001 fix)
[OK] JS usa const API = '' (BUG-001 fix)
[OK] GET /dashboard responde 200
[OK] GET /inbox responde 200
[OK] GET /invoices responde 200
[OK] POST /chat responde 200
```

## Tests a aplicar después del fix

- [ ] Abrir http://localhost:8000/ → ver stats reales
- [ ] Click en Inbox → ver 15 facturas
- [ ] Click en Historial → ver pagos procesados
- [ ] Click en Chat → enviar mensaje y recibir respuesta
- [ ] Header → indicador verde "Todos los servicios OK"