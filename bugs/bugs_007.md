# BUG-007: Frontend oculta errores mostrando datos MOCK hardcodeados

## Severidad: **MEDIUM** (degrada UX y oculta bugs reales)
## Componente: `app/frontend/app.js` (múltiples catch blocks)
## Detectado por: Inspección del código
## Fecha: 2026-07-09

---

## Descripción

El JS tiene bloques `catch {}` con fallbacks hardcodeados en TODAS las funciones principales:

```javascript
// loadDashboard - línea 84-97
} catch {
    // Fallback a datos mock
    document.getElementById('stat-inbox').textContent = '5';      // ← fake
    document.getElementById('stat-approved').textContent = '12';   // ← fake
    document.getElementById('stat-escalated').textContent = '2';
    document.getElementById('stat-rejected').textContent = '3';
    document.getElementById('stat-total').textContent = '$1,250,000';  // ← fake
    renderRecentPayments([
        { invoice_id: 'FC-2026-SUP001-001', ... },  // ← fake
        ...
    ]);
}

// loadInbox - línea 132-138
} catch {
    inboxFiles = [
        { filename: 'FC-2026-SUP001-NUEVA-1.txt', ... },  // ← fake
        ...
    ];
    renderInbox();
}

// loadHistory - línea 265-272
} catch {
    renderHistory([
        { invoice_id: 'FC-2026-SUP001-001', ... },  // ← fake
        ...
    ]);
}

// sendInternalChat - línea 345-351
} catch {
    setTimeout(() => {
        const response = generateInternalResponse(text);  // ← fake
        addInternalChatMessage('system', response);
    }, 1000);
}
```

## Impacto

- Cuando hay un error real (404, 500, JSON malformado), el usuario ve datos falsos
- **Pésima UX**: el operador piensa que tiene datos cuando en realidad el backend está caído
- **Debugging imposible**: los logs no muestran nada porque no hay `console.error()`
- Los datos MOCK son antiguos (`FC-2026-...`) y desactualizados

## Fix Propuesto

```javascript
async function loadDashboard() {
    try {
        const resp = await fetch(`${API}/dashboard`);
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status} from ${API}/dashboard`);
        }
        const data = await resp.json();
        // ... render real
    } catch (err) {
        console.error('[loadDashboard] Error:', err);
        showToast(`Error cargando dashboard: ${err.message}`, 'error');
        // Mostrar UI de error, no datos falsos
        document.getElementById('stat-inbox').textContent = '?';
        // ...
    }
}
```

Aplicar el mismo patrón a todas las funciones.

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

Se eliminaron TODOS los fallbacks con datos MOCK hardcodeados y se reemplazaron por:

1. **UI de error real** que muestra el mensaje del error
2. **Console.error()** para debugging en DevTools
3. **Toast notifications** con el error específico (no genérico)
4. **Stats del dashboard** muestran `!` en lugar de números falsos

```javascript
// Antes (BUG-007)
} catch {
    document.getElementById('stat-inbox').textContent = '5';  // MOCK
    ...
}

// Después (FIX)
} catch (err) {
    console.error('[loadDashboard]', err);
    tbody.innerHTML = `<tr><td colspan="6" class="error">Error: ${err.message}</td></tr>`;
    showError('stat-inbox', 'Error dashboard');
}
```

## Beneficios

- El operador ve errores reales, no datos fake
- En DevTools hay logs claros con contexto
- Las stats muestran `!` cuando algo falla
- No más silencio engañoso