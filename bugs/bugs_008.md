# BUG-008: Browser cachea `app.js` viejo, sigue usando `/api/*`

## Severidad: **HIGH**
## Componente: `app/backend/main.py` (StaticFiles sin cache headers)
## Detectado por: Usuario reporta errores 404 con `/api/dashboard` en consola
## Fecha: 2026-07-09

---

## Descripción

Después de aplicar BUG-001 fix (cambiar `const API = '/api'` → `const API = ''`),
el browser sigue mostrando errores 404:

```
app.js:74  GET http://localhost:8000/api/dashboard 404 (Not Found)
app.js:128 GET http://localhost:8000/api/inbox 404 (Not Found)
app.js:262 GET http://localhost:8000/api/invoices 404 (Not Found)
app.js:379 GET http://localhost:8000/api/health 404 (Not Found)
```

El archivo `app/frontend/app.js` en el **servidor** ya está corregido:
```javascript
const API = '';  // línea 12
```

Pero el **browser** carga la versión vieja cacheada que tiene `const API = '/api'`.

## Causa Raíz

`StaticFiles` de FastAPI sirve los archivos con headers de cache agresivos del browser.
El browser cachea `app.js` y no lo re-descarga aunque el servidor haya cambiado.

## Fix Propuesto

**Opción A (mejor - cache control headers):** Agregar middleware que deshabilite cache
para `/static/*`:

```python
# app/backend/main.py
from starlette.middleware.base import BaseHTTPMiddleware

class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/") or \
           request.url.path.startswith("/supplier/") or \
           request.url.path.startswith("/tests/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheStaticMiddleware)
```

**Opción B (rápido - query string):** Cambiar `<script src="/static/app.js">` a
`<script src="/static/app.js?v=2">` para forzar reload.

Recomiendo **Opción A** porque es transparente y aplica a todos los assets.

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

```python
# app/backend/main.py
from starlette.middleware.base import BaseHTTPMiddleware

class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    """Fuerza no-cache en /static/, /supplier/, /tests/."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith(("/static/", "/supplier/", "/tests/")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheStaticMiddleware)
```

## Verificación

```
GET /static/app.js
  Cache-Control: no-cache, no-store, must-revalidate
  Pragma:        no-cache
  Expires:       0

GET /supplier/
  Cache-Control: no-cache, no-store, must-revalidate

GET /tests/eval/datasets/invoiceflow-dataset.json
  Cache-Control: no-cache, no-store, must-revalidate

GET /dashboard (API, should NOT have no-cache)
  Cache-Control: None
```

- ✅ Assets estáticos siempre se re-descargan
- ✅ Endpoints API mantienen comportamiento default (cacheables si procede)
- ✅ El browser va a leer el `app.js` nuevo en cada F5