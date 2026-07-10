# BUG-009: HTML root (`/`) e index.html también se cachean, browser no recarga el `<script>` tag

## Severidad: **HIGH**
## Componente: `app/backend/main.py` + `app/frontend/index.html`
## Detectado por: Usuario reporta errores 404 con `/api/dashboard` después de BUG-008
## Fecha: 2026-07-09

---

## Descripción

Después de aplicar BUG-008 (no-cache en `/static/*`), el browser **seguía cargando
la versión vieja** de `app.js` porque:

1. El browser cachea el `index.html` (servido desde `/` por FileResponse)
2. El `index.html` cacheado dice `<script src="/static/app.js">` (sin query string)
3. El browser ni siquiera pregunta por `/static/app.js` porque ya lo tiene cacheado

## Solución Aplicada

**1. Agregar query string de versión al script tag:**

```html
<!-- app/frontend/index.html línea 497 -->
- <script src="/static/app.js"></script>
+ <script src="/static/app.js?v=2026070901"></script>
```

**2. Extender el middleware no-cache al HTML root:**

```python
# app/backend/main.py
class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith(("/static/", "/supplier/", "/tests/")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        elif path in ("/", "/supplier", "/supplier/", "/index.html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
```

## Verificación

```
GET /  (status=200)
  Cache-Control: no-cache, no-store, must-revalidate
  Has app.js?v=2026070901: True
  Has OLD /static/app.js (no version): False

GET /static/app.js?v=2026070901  (status=200)
  Cache-Control: no-cache, no-store, must-revalidate
  Has const API = '' (NEW): True
  Has OLD const API = '/api': False
```

## Status: ✅ RESUELTO

## Lección

Después de aplicar no-cache a assets estáticos, **siempre** hay que:
1. Bumpear la versión en el script tag (`?v=N`)
2. Aplicar no-cache también al HTML que referencia esos assets
3. De lo contrario el browser tiene "memoria cache" del HTML que apunta a URLs viejas