# Frontend React — Sistema de Aprobación de Facturas

Este directorio ahora contiene DOS frontends:

- **`index.html` + `app.js` + `style.css`** → versión vieja (vanilla JS, la "InvoiceFlow" original).
- **`InvoiceApprovalSystem.jsx` + `preview.html`** → versión nueva (React, single-file, según spec).

## Cómo previsualizar la versión nueva

### Opción A — Con el backend FastAPI ya corriendo

Si ya tenés el backend en `http://localhost:8000`, los archivos estáticos se sirven
en `/static/`. Entonces visitá:

```
http://localhost:8000/static/preview.html
```

### Opción B — Servidor estático independiente

Desde esta carpeta (`platform/frontend/`):

```bash
python -m http.server 8000
```

Y abrí `http://localhost:8000/preview.html` en el browser.

> Requiere conexión a internet (carga React, ReactDOM, Babel-standalone y
> Google Fonts desde CDN).

### Opción C — Integración real con bundler

Si querés usarlo en un proyecto React real:

1. `npm create vite@latest my-app -- --template react`
2. Copiá `InvoiceApprovalSystem.jsx` a `src/`.
3. En `src/App.jsx`: `import InvoiceApprovalSystem from './InvoiceApprovalSystem'`
4. Render: `<InvoiceApprovalSystem />`
5. `npm run dev`

## Proveedores de prueba

| ID         | Estado   | Límite    | Notas                                |
|------------|----------|-----------|--------------------------------------|
| `SUP001`   | Activo   | $150.000  | TechCorp SA                          |
| `SUP002`   | Activo   | $30.000   | LogiPack SRL                         |
| `SUP003`   | Inactivo | —         | Falla validación                     |
| `SUP004`   | Activo   | $80.000   | MarketingPro                         |
| `SUP005`   | Activo   | $200.000  | Consultores Asociados                |
| `SUP999`   | —        | —         | Falla validación (no encontrado)     |

Monto > $500.000 → guardrail escala a revisión humana.
