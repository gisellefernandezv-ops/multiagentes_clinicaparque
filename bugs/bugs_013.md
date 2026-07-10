# BUG-013: Modal se renderiza al final de la página en vez de overlay

## Severidad: **MEDIUM**
## Componente: `app/frontend/app.js` + `app/frontend/style.css`
## Detectado por: Usuario clickea 👁️ y ve el modal al final de la página
## Fecha: 2026-07-09

---

## Descripción

Al hacer click en el botón 👁️ de una fila, el modal:
- ❌ NO aparece como overlay fixed
- ❌ Aparece al final del documento (donde se hizo `document.body.appendChild`)
- ❌ El usuario tiene que scrollear hasta abajo para verlo

## Causa Raíz

El modal original se creaba así:

```javascript
const div = document.createElement('div');
div.id = 'invoice-modal';                    // div #1 sin estilos
div.innerHTML = `<div class="modal-overlay">  // div #2 con position:fixed
    <div class="modal-content">...</div>
</div>`;
document.body.appendChild(div);
```

Problemas:
1. **El div exterior `#invoice-modal` no tiene estilos** → su posición depende del flujo normal
2. **El CSS `.modal-overlay { position: fixed }` puede ser overridden** por reglas con mayor especificidad
3. **El browser puede estar usando CSS cacheado** sin las reglas del modal

## Fix Aplicado

**1.** El wrapper exterior AHORA tiene tanto `id="invoice-modal"` COMO `class="modal-overlay"`:

```javascript
const html = `
    <div id="invoice-modal" class="modal-overlay" onclick="closeModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            ...
        </div>
    </div>
`;
document.body.insertAdjacentHTML('beforeend', html);
```

**2.** El CSS usa `!important` y aplica también a `#invoice-modal`:

```css
#invoice-modal,
.modal-overlay {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    background: rgba(15, 23, 42, 0.7) !important;
    z-index: 99999 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
```

**3.** Cache-bust del CSS y JS:
```html
<link rel="stylesheet" href="/static/style.css?v=2026070905">
<script src="/static/app.js?v=2026070905"></script>
```

## Status: ✅ RESUELTO