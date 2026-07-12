# Bugs — InvoiceFlow

Tracking de bugs del sistema. Cada bug tiene un archivo `bugs_NNN.md`.

## Indice

| ID | Severidad | Componente | Titulo | Status |
|----|-----------|------------|--------|--------|
| [BUG-001](./bugs_001.md) | CRITICAL | `app/frontend/app.js` | API path mismatch (`/api/*` vs `/*`) | ✅ RESUELTO |
| [BUG-002](./bugs_002.md) | HIGH     | `app/frontend/app.js` | Dashboard lee campos incorrectos (`approved` vs `decisions.APPROVED`) | ✅ RESUELTO |
| [BUG-003](./bugs_003.md) | HIGH     | `app/frontend/app.js` | `loadInbox()` espera `{files: [...]}` pero backend devuelve array | ✅ RESUELTO |
| [BUG-004](./bugs_004.md) | HIGH     | `app/frontend/app.js` | `loadHistory()` espera `{invoices: [...]}` pero backend devuelve array | ✅ RESUELTO |
| [BUG-005](./bugs_005.md) | HIGH     | `app/frontend/app.js` | Chat lee `data.response` pero backend devuelve `data.message` | ✅ RESUELTO |
| [BUG-006](./bugs_006.md) | MEDIUM   | `app/backend/main.py` | Frontend pide `/tests/eval/datasets/*.json` no servido | ✅ RESUELTO |
| [BUG-007](./bugs_007.md) | MEDIUM   | `app/frontend/app.js` | Frontend oculta errores con datos MOCK hardcodeados | ✅ RESUELTO |
| [BUG-008](./bugs_008.md) | HIGH     | `app/backend/main.py` | Browser cachea `app.js` viejo, sigue usando `/api/*` | ✅ RESUELTO |
| [BUG-009](./bugs_009.md) | HIGH     | `index.html` + middleware | HTML root se cachea y no recarga nuevo `<script>` tag | ✅ RESUELTO |
| [BUG-010](./bugs_010.md) | MEDIUM   | `index.html` + `app.js`   | Pantalla "Estado de Agentes" muestra datos MOCK hardcodeados | ✅ RESUELTO |
| [BUG-011](./bugs_011.md) | HIGH     | `app.js` + `main.py`     | CORS policy bloquea fetch cross-origin a 8001/8002/8003 | ✅ RESUELTO |
| [BUG-012](./bugs_012.md) | HIGH     | `app.js` + `watcher.py`  | Dashboard no concuerda con listas + Inbox incompleto + falta modal | ✅ RESUELTO |
| [BUG-013](./bugs_013.md) | MEDIUM   | `app.js` + `style.css`   | Modal se renderiza al final de la página en vez de overlay | ✅ RESUELTO |
| [BUG-014](./bugs_014.md) | MEDIUM   | `data/` + `watcher.py`   | Sistema usa formato simplificado, no Factura B real | ✅ RESUELTO |
| [BUG-015](./bugs_015.md) | MEDIUM   | `data/` + `watcher.py` + `app.js` | Nomenclatura FC-PV-NRO + soporte A/B/C + modal con 2 secciones | ✅ RESUELTO |
| [BUG-016](./bugs_016.md) | HIGH     | `supplier_service/` + `app.js` | ABM de Proveedores + fecha emisión + validación de contrato con modo | ✅ RESUELTO |
| [BUG-017](./bugs_017.md) | MEDIUM   | `app.js` `renderSuppliers` + `index.html` | Columna Categoria muestra email + alinear headers + lapiz editar | ✅ RESUELTO |
| [BUG-018](./bugs_018.md) | HIGH     | `main.py` + `style.css`   | 500 al editar proveedor + falta responsive design | ✅ RESUELTO |
| [BUG-019](./bugs_019.md) | MEDIUM   | `chat_router.py` + `app.js` | Chat no entiende "montos" + debe llamarse "Asistente IA" + presentación | ✅ RESUELTO |
| [BUG-020](./bugs_020.md) | HIGH     | `chat_router.py` | Chat no entiende "modificar el monto" → va a inbox_amounts | ✅ RESUELTO |
| [BUG-021](./bugs_021.md) | HIGH     | `watcher.py` | Parser facturas no extrae invoice_id, fecha y monto | ✅ RESUELTO |

## Resumen Ejecutivo

**Síntoma reportado por usuario:** "En el backoffice no veo ningún resultado, está vacío. No hay datos en el dashboard como en el resto de pantallas. Además el chat no me da ninguna información."

**Causa raíz:** El frontend tenía **7 bugs** que combinados hacían que la UI mostrara datos vacíos o fake:
1. Las llamadas HTTP apuntaban a `/api/*` pero el backend sirve en `/*` → **404 en TODO**
2. Cuando había error, el catch() mostraba datos hardcodeados (mocks) → usuario veía números falsos o vacío
3. Los nombres de campos JSON no coincidían con lo que devuelve el backend

**Impacto original:** BackOffice 100% no funcional. Solo el Supplier Portal (que es HTML estático) funcionaba.

## Resultado del Fix (2026-07-09)

✅ **TODOS LOS 7 BUGS RESUELTOS**

| Validación | Resultado |
|------------|-----------|
| `test_frontend.py` | **49/49 PASS** |
| HTML estructura | OK (11 elementos verificados) |
| JS fix aplicado | OK (8 patrones verificados) |
| Endpoints JSON | OK (5/5 responden 200) |
| Estructura JSON | OK (16 campos verificados) |
| Supplier Portal | OK |
| Swagger docs | OK (2/2) |
| Eval dataset | OK (20 casos accesibles) |

## Pantallas ahora funcionales

- ✅ **Dashboard** muestra: 15 inbox, 3 aprobadas, 8 rechazadas, 3 escaladas, $150.000 total
- ✅ **Inbox** lista las 15 facturas pendientes
- ✅ **Historial** muestra los 14 pagos procesados
- ✅ **Chat interno** responde con `[intent] mensaje` del backend
- ✅ **Evaluación** carga los 20 test cases del dataset
- ✅ **Estado de Agentes** muestra "Todos los servicios OK"

## Tests disponibles

- `test_frontend.py` — Validación automatizada del frontend
- `FULL_ANALYSIS.py` — Validación de las 11 SPECs del SYSTEM_PROMPT
- `verify_full.py` — Smoke tests básicos