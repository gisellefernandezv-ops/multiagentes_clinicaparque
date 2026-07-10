# BUG-006: Frontend pide `/tests/eval/datasets/invoiceflow-dataset.json` pero el backend no lo sirve

## Severidad: **MEDIUM**
## Componente: `app/frontend/app.js` función `loadEvaluation()`
## Detectado por: Verificación manual del filesystem
## Fecha: 2026-07-09

---

## Descripción

```javascript
// línea 416
const resp = await fetch('/tests/eval/datasets/invoiceflow-dataset.json');
const data = await resp.json();
renderEvaluation(data.test_cases || []);
```

El archivo **existe** en el filesystem:

```
tests/eval/datasets/
├── __init__.py
└── invoiceflow-dataset.json    (11.7 KB)
```

Pero el backend (`app/backend/main.py`) solo monta:
- `/static/*` → `app/frontend/`
- `/supplier/*` → `supplier_portal/`

**No hay** un mount para `/tests/*` → devuelve 404.

## Impacto

- Pantalla "Evaluación" muestra solo 3 casos hardcodeados en el fallback JS
- El usuario nunca ve los ~20 casos reales del dataset

## Fix

**Opción A (rápida):** Backend monta la carpeta `tests/eval/datasets` como static:

```python
# app/backend/main.py
EVAL_DATASETS_DIR = PROJECT_ROOT / "tests" / "eval" / "datasets"
if EVAL_DATASETS_DIR.exists():
    app.mount(
        "/tests/eval/datasets",
        StaticFiles(directory=str(EVAL_DATASETS_DIR)),
        name="eval_datasets",
    )
```

**Opción B (mejor):** Crear un endpoint dedicado en el backend que sirva los golden cases:

```python
# nuevo: app/backend/eval_router.py
@router.get("/eval/dataset")
def get_eval_dataset():
    return json.loads((PROJECT_ROOT / "tests/eval/datasets/invoiceflow-dataset.json").read_text())
```

Recomiendo **Opción A** porque es 1 línea y reutiliza StaticFiles.

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

```python
# app/backend/main.py - después del bloque del frontend estático
EVAL_DATASETS_DIR = PROJECT_ROOT / "tests" / "eval" / "datasets"
if EVAL_DATASETS_DIR.exists():
    app.mount(
        "/tests/eval/datasets",
        StaticFiles(directory=str(EVAL_DATASETS_DIR)),
        name="eval_datasets",
    )
```

## Verificación

```
GET /tests/eval/datasets/invoiceflow-dataset.json
→ 200 OK
→ 11.7 KB
→ {"dataset_name": "invoiceflow-dataset", "version": "1.0.0", "test_cases": [...20 casos...]}
```

La pantalla de Evaluación ahora muestra los 20 test cases reales del dataset, no los 3 hardcodeados.