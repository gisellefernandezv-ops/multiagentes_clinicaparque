# BUG-011: CORS policy bloquea fetch cross-origin a 8001/8002/8003 desde el browser

## Severidad: **HIGH**
## Componente: `app/frontend/app.js` `loadAgentsStatus()`
## Detectado por: Errores CORS en consola del browser
## Fecha: 2026-07-09

---

## Descripción

El JS de `loadAgentsStatus()` hace `fetch('http://localhost:8001/health')` directamente
desde el browser. Pero el origen del browser es `http://localhost:8000` (BackOffice).

Los servicios en 8001, 8002, 8003 **no tienen** `CORSMiddleware` configurado,
por lo que el browser bloquea las requests:

```
Access to fetch at 'http://localhost:8001/health' from origin 'http://localhost:8000'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
on the requested resource.
```

## Impacto

- `loadAgentsStatus()` reporta TODOS los servicios como caídos
- El operador ve "todo en rojo" cuando en realidad todo está OK
- El `setInterval(loadAgentsStatus, 15000)` spamea errores CORS cada 15s
- Consola del browser se llena de errores

## Fix Propuesto (Opción recomendada - proxy en backend)

En lugar de hacer N fetches cross-origin desde el browser, agregar UN endpoint
en el backend que agregue todos los health checks:

```python
# app/backend/main.py - nuevo endpoint
import httpx

@app.get("/agents/health")
async def agents_health():
    """Health check agregado de todos los servicios (proxy)."""
    services = [
        ("backend",          f"http://127.0.0.1:8000/health"),
        ("supplier-service", settings.supplier_service_url + "/health"),
        ("contract-service", settings.contract_service_url + "/health"),
        ("external-auditor", "http://127.0.0.1:8003/health"),
    ]
    results = {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, url in services:
            try:
                r = await client.get(url)
                results[name] = {
                    "status": r.json().get("status", "unknown") if r.status_code == 200 else "down",
                    "url": url,
                    "ok": r.status_code == 200,
                }
            except Exception as e:
                results[name] = {"status": "down", "url": url, "ok": False, "error": str(e)}
    return results
```

Y en `app.js` cambiar:
```javascript
// Antes (CORS bloqueado)
{ name: 'supplier-service', url: 'http://localhost:8001/health' },

// Después (proxy en mismo origen)
{ name: 'supplier-service', url: '/agents/health' },
```

## Por qué esta opción es mejor que agregar CORS a cada microservicio

1. **Single point of change**: solo modificamos el backend
2. **Mejor seguridad**: no expone los puertos internos al browser
3. **Menos superficie de ataque**: el browser no necesita conocer 8001/8002/8003
4. **Más robusto**: si un microservicio está caído, el backend lo maneja

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

**1.** `app/backend/main.py` — nuevo endpoint proxy:

```python
@app.get("/agents/health")
async def agents_health():
    """Health check agregado de TODOS los servicios (proxy same-origin)."""
    import httpx
    services_config = [
        ("invoiceflow-backend", f"http://127.0.0.1:{settings.port}/health"),
        ("supplier-service",    f"{settings.supplier_service_url}/health"),
        ("contract-service",    f"{settings.contract_service_url}/health"),
        ("external-auditor",    "http://127.0.0.1:8003/health"),
    ]
    results = {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, url in services_config:
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    results[name] = {"ok": True, "status": data.get("status", "unknown"), ...}
                else:
                    results[name] = {"ok": False, "status": "down", ...}
            except Exception as e:
                results[name] = {"ok": False, "status": "down", "error": str(e)}
    return results
```

**2.** `app/frontend/app.js` — `loadAgentsStatus()` ahora hace UN solo fetch:

```javascript
const resp = await fetch(`${API}/agents/health`, { cache: 'no-store' });
const data = await resp.json();
// Iterar sobre data (dict de servicios)
```

**3.** `app/frontend/index.html` — bumpeado a `?v=2026070903`.

## Verificación

```
=== Test /agents/health proxy (BUG-011 fix) ===
[OK] invoiceflow-backend       status=ok       ok=True
[OK] supplier-service          status=ok       ok=True    ← ya no CORS
[OK] contract-service          status=ok       ok=True    ← ya no CORS
[OK] external-auditor          status=ok       ok=True    ← ya no CORS

=== JS check ===
Uses /agents/health proxy: True
NO cross-origin localhost:8001: True    ← ya no hay fetch cross-origin
NO cross-origin localhost:8002: True
NO cross-origin localhost:8003: True
```

## Beneficio extra

- El browser ya no necesita conocer los puertos internos 8001/8002/8003
- El backend maneja errores timeouts (httpx con timeout=2s)
- Si un microservicio está caído, el backend devuelve `ok: false` con `error` message
- Más seguro: no exponer puertos internos al browser