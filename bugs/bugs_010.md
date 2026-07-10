# BUG-010: Pantalla "Estado de Agentes" muestra datos MOCK hardcodeados

## Severidad: **MEDIUM**
## Componente: `app/frontend/index.html` + `app/frontend/app.js`
## Detectado por: Usuario reporta "supplier-service 🔴 Caído" cuando el servicio ESTÁ corriendo
## Fecha: 2026-07-09

---

## Descripción

La página "Estado de Agentes" (`#page-observabilidad`) tiene **6 cards de agentes
hardcodeadas** en el HTML:

```html
<!-- app/frontend/index.html líneas 263-396 -->
<div class="agents-grid" id="agents-grid">
    <!-- Generado dinámicamente -->      <!-- ← MENTIRA: NO se genera dinámicamente -->
    <div class="agent-card">...invoice_orchestrator...🟢 Online...</div>
    <div class="agent-card">...validator_agent...🟢 Online...</div>
    <div class="agent-card">...contract_agent...🟢 Online...</div>
    <div class="agent-card">...router_agent...🟢 Online...</div>
    <div class="agent-card warning">...supplier-service...🔴 Caído...</div>  <!-- ← INCORRECTO -->
    <div class="agent-card">...contract-service...🟢 Online...</div>
</div>
```

Todos los stats (Invocaciones 24h, Tasa de error, Última ejecución) son **strings
hardcodeados** que el operador ve aunque no correspondan al estado real.

## Impacto

- El operador **ve información falsa** sobre el estado del sistema
- El supplier-service está marcado como "Caído" cuando en realidad está respondiendo:
  ```
  $ curl http://localhost:8001/health
  {"service":"supplier-service","status":"ok",...}
  ```
- Decisiones operativas se pueden tomar sobre datos incorrectos
- El HTML dice `<!-- Generado dinámicamente -->` pero en realidad es estático

## Fix Propuesto

**1.** Eliminar TODOS los `<div class="agent-card">...` hardcodeados del HTML.

**2.** Agregar función `loadAgentsStatus()` en `app.js` que:

```javascript
async function loadAgentsStatus() {
    try {
        const resp = await fetch(`${API}/health`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        const services = [
            { name: 'Backend',            icon: '🧠', status: 'ok', port: 8000 },
            { name: 'supplier-service',   icon: '📦', status: data.microservices?.['supplier-service']?.status || 'unknown', port: 8001 },
            { name: 'contract-service',   icon: '📋', status: data.microservices?.['contract-service']?.status || 'unknown', port: 8002 },
            { name: 'external-auditor',   icon: '🔍', status: 'check-port', port: 8003 },
        ];

        // Render
        const grid = document.getElementById('agents-grid');
        grid.innerHTML = services.map(s => {
            const isOnline = s.status === 'ok';
            return `
                <div class="agent-card ${isOnline ? '' : 'warning'}">
                    <div class="agent-header">
                        <span class="agent-icon">${s.icon}</span>
                        <span class="agent-name">${s.name}</span>
                        <span class="agent-status ${isOnline ? 'online' : 'offline'}">
                            ${isOnline ? '🟢 Online' : '🔴 Caído'}
                        </span>
                    </div>
                    ...
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('[loadAgentsStatus]', err);
    }
}
```

**3.** Llamar `loadAgentsStatus()` al cargar la página de Observabilidad
(via MutationObserver igual que `loadEvaluation()`).

**4.** Polling cada 30s para refresh.

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

**1.** `app/frontend/index.html` — eliminadas las 6 cards hardcodeadas, ahora hay
solo un placeholder:

```html
<div class="agents-grid" id="agents-grid">
    <div class="agent-card" style="...">
        <span>Cargando estado de agentes…</span>
    </div>
</div>
```

**2.** `app/frontend/app.js` — agregada función `loadAgentsStatus()` que:
- Hace ping a los 4 servicios en paralelo (`/health` en cada puerto)
- Calcula "Última verificación" dinámicamente con `agentLastSeen` map
- Renderiza cards con el estado REAL
- Auto-refresh cada 15 segundos
- Se dispara via `MutationObserver` cuando el usuario abre la pestaña Observabilidad

**3.** `app/frontend/index.html` — bumpeada versión del script tag:
```html
<script src="/static/app.js?v=2026070902"></script>
```

## Verificación

```
HTML root checks:
  Has hardcoded 'Caido': False  ✅
  Has 'Cargando estado' placeholder: True
  Has app.js?v=2026070902 (NEW version): True
  Old version (2026070901) gone: True

JS checks (BUG-010 fix):
  Has loadAgentsStatus(): True
  Has pingService(): True
  Has 'supplier-service' literal: True
  Has 'external-auditor' literal: True
  Has MutationObserver for observabilidad: True

Service health checks (todos OK):
  Backend    (:8000): status=ok
  Supplier   (:8001): status=ok    ← antes mostraba "Caído", ahora mostrará "Online"
  Contract   (:8002): status=ok
  Auditor    (:8003): status=ok
```

## Tests a aplicar después del fix

- [ ] Backend (8000) → 🟢 Online
- [ ] supplier-service (8001) → 🟢 Online (NO 🔴 Caído)
- [ ] contract-service (8002) → 🟢 Online
- [ ] external-auditor (8003) → check via ping
- [ ] Matar supplier-service → debe cambiar a 🔴 Caído en menos de 30s
- [ ] Levantarlo de nuevo → debe volver a 🟢 Online