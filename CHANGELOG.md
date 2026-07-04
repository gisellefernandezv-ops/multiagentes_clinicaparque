# Changelog — Sistema Multiagente de Aprobación de Facturas

Todos los cambios notables de este proyecto se documentan acá. El formato
sigue [Keep a Changelog](https://keepachangelog.com/) y el versionado
sigue [Semantic Versioning](https://semver.org/).

---

## [1.2.0] — 2026-07-04 — Dashboard y Portal de Proveedores

### 🎉 Added

- **Portal de Proveedores** (`/supplier`):
  - Login con CUIT, ID de proveedor o nombre
  - Vista de facturas por proveedor
  - Filtros por estado (Aprobadas, Pendientes, Rechazadas, Escaladas)
  - Chat con el departamento de Cuentas a Pagar
- **Dashboard del sistema** (`/dashboard`):
  - Estadísticas en tiempo real (facturas en inbox, procesadas, rechazadas)
  - Conteo de decisiones por tipo
  - Total de montos aprobados
  - Últimos pagos procesados
- **Base de datos de facturas** (`suppliers.db`):
  - Tabla `invoices` con datos de prueba para cada proveedor
  - Historial de estados y confirmaciones

### 🐛 Fixed

- **Ruta de `payments_db`** en `settings.py`:
  - Cambiada de `platform/data/payments.db` a `data/payments.db`
- **Query SQL del dashboard**:
  - Corregido `processed_at` → `registered_at` en la tabla payments
- **Router del portal de proveedores**:
  - Corregida conexión a `suppliers.db` en lugar de `payments.db`
  - Corregido uso de `row[]` en lugar de `row.get()` para SQLite Row
- **Ruteo del portal de proveedores**:
  - Configurado StaticFiles con `html=True` para servir index.html automáticamente
  - Rutas `/supplier`, `/supplier/` y `/supplier/portal` funcionan correctamente

### 📊 Datos de prueba

Proveedores disponibles en el portal:

| ID | Nombre | CUIT | Estado |
|---|---|---|---|
| SUP001 | TechCorp SA | 30-71234567-0 | ACTIVO |
| SUP002 | Papelería Norte SRL | 30-69874523-1 | ACTIVO |
| SUP003 | Servicios Rápidos SA | 30-70111222-3 | INACTIVO |
| SUP004 | Limpieza Total SRL | 30-70555666-7 | ACTIVO |
| SUP005 | Consultoría Digital SA | 30-71234999-2 | ACTIVO |

---

## [1.1.0] — 2026-06-28 — Fix de compatibilidad `chromadb` ↔ `google-genai`

### ⚠️ Changed (breaking changes técnicas, no de API)

- **Migración de `google-generativeai` → `google-genai`** para embeddings
  RAG.
- **Cambio de modelo de embeddings** `models/embedding-001` →
  `models/gemini-embedding-001`.

### 🐛 Fixed

- **`ValueError: ClientOptions does not accept an option 'headers'`** al
  correr `python rag/ingest.py`.

### 🔍 Root cause

`google-generativeai 0.8.6` (última versión del SDK viejo, ya deprecado
por Google) introdujo una opción `headers` en `genai.configure()` que es
rechazada por `chromadb 1.5.x` al instanciar
`GoogleGenerativeAiEmbeddingFunction`. El wrapper oficial de Chroma quedó
incompatible con el SDK viejo de Google.

### ✅ Solución implementada

1. **Nueva clase `GoogleGenAiEmbeddingFunction`** en
   [`rag/embedding_function.py`](rag/embedding_function.py):
   - Implementa el protocolo `EmbeddingFunction` de ChromaDB (`__call__`).
   - Usa el SDK nuevo `google.genai.Client` (no deprecado, mantenido
     activamente).
   - Acepta parámetros `api_key`, `model_name`, `task_type`.

2. **`rag/ingest.py`** actualizado para usar la nueva clase con
   `task_type="RETRIEVAL_DOCUMENT"`.

3. **`rag/retriever.py`** actualizado para usar la nueva clase con
   `task_type="RETRIEVAL_QUERY"` (optimiza similitud para queries).

4. **Modelo migrado**: `models/gemini-embedding-001` es el único modelo
   de embeddings estable en `v1beta` al momento del fix. El wrapper
   acepta un parámetro `model_name` para permitir cambiarlo en el
   futuro sin tocar el código.

### 📊 Impacto medido

- **Ingesta RAG**: ahora completa en ~8 segundos para 21 chunks (4
  contratos). Pre-fix: fallaba al 100%.
- **Retrieval**: latencia similar a la implementación anterior (~1.2s
  por query).
- **Calidad de embeddings**: `gemini-embedding-001` tiene 3072
  dimensiones vs 768 de `embedding-001`. Más rico semánticamente.

### ⚠️ Notas de migración para devs

Si tenías el código previo con `models/embedding-001` y estás viendo
este CHANGELOG:

1. Hacé `git pull` (o equivalente) para bajar el fix.
2. **No** hace falta reinstalar nada — los paquetes `google-genai` y
   `google-generativeai` siguen ambos en `requirements.txt`.
3. Volvé a correr `python rag/ingest.py` para regenerar el índice.
4. La interfaz de `agent.py` y los agentes no cambió — el fix es
   transparente.

---

## [1.0.0] — 2026-06-15 — Release inicial

### 🎉 Added (primera versión funcional)

- **4 agentes ADK** implementados:
  - `invoice_orchestrator` (root) — coordina + guardrail.
  - `validator_agent` (sub) — valida proveedor via MCP mock.
  - `contract_agent` (sub) — control contractual via RAG.
  - `payment_agent` (sub) — persiste en SQLite.
- **3 tools (`FunctionTool`)**:
  - `supplier_lookup_tool` — consulta dict de 5 proveedores mock.
  - `search_contract_tool` — wrapper sobre `rag.retriever`.
  - `register_payment_tool` — INSERT en SQLite con `confirmation_id`.
- **RAG sobre ChromaDB**:
  - `rag/ingest.py` — chunking 500/50 chars, embeddings con
    `models/embedding-001`.
  - `rag/retriever.py` — query semántica + regex de monto.
  - 4 contratos de ejemplo en `data/contracts/` (SUP001, SUP002, SUP004,
    SUP005).
- **Guardrail estructural** (`guardrails/invoice_guardrail.py`):
  - 7 reglas (campos, formato, monto, fecha).
  - Acciones: APPROVE / REJECT / ESCALATE.
- **Persistencia en SQLite** (`tools/payment_db_tool.py`):
  - Tabla `payments` con índices por `invoice_id` y `supplier_id`.
  - `confirmation_id` único por registro (`PAY-XXXXXXXX`).
- **Gestión de sesiones** (`sessions/session_manager.py`):
  - `InvoiceSessionManager` wrapper sobre `InMemorySessionService`.
  - State inicial con todos los campos de la consigna.
- **Evaluación** (`evaluation/`):
  - 6 golden cases (GC001-GC006) cubriendo todas las ramas.
  - LLM as a Judge con `gemini-2.0-flash-latest`.
  - BertScore con `xlm-roberta-base` multilingüe.
- **UI**: `adk web` con FastAPI + React.
- **Automatización**:
  - `setup.bat` — setup completo desde cero.
  - `start.bat` — levanta la UI.
  - `smoke_test.bat` — corre los 9 smoke tests.
- **Documentación**:
  - `README.md` — descripción, arquitectura, uso.
  - `INSTALL.md` — guía de instalación.
  - `CHANGELOG.md` — este archivo.

---

## Tipos de cambios

- **🎉 Added**: nueva funcionalidad.
- **⚠️ Changed**: cambio en funcionalidad existente.
- **🐛 Fixed**: bug fix.
- **🗑️ Deprecated**: funcionalidad que se va a eliminar.
- **❌ Removed**: funcionalidad eliminada.
- **🔒 Security**: fix de seguridad.
- **📊 Performance**: mejora de performance.
- **📚 Docs**: solo cambios de documentación.
- **🧪 Test**: agregado o modificación de tests.

---

## Roadmap (ideas para versiones futuras)

### [1.3.0] — Planeado
- Migrar ChromaDB a Qdrant para soportar multi-tenancy.
- Agregar autenticación OAuth en `adk web`.
- Dashboard con métricas (pass rate, latencia, costo por factura).

### [2.0.0] — Breaking change planeado
- Reemplazar `gemini-2.0-flash` por `gemini-2.5-pro` cuando esté GA.
  Esto cambia la latencia y el costo por factura.

---

## Cómo reportar un bug

1. Buscar en [issues] si ya está reportado.
2. Si no, crear un nuevo issue con:
   - Pasos para reproducir.
   - Salida esperada vs obtenida.
   - Versión de Python, sistema operativo.
   - Logs relevantes (especialmente stack traces completos).
3. Taggear con la etiqueta apropiada (`bug`, `enhancement`, `docs`).

---

## Cómo contribuir

1. Fork del repo.
2. Crear branch desde `main`: `git checkout -b feat/mi-feature`.
3. Hacer commits con mensaje descriptivo:
   `git commit -m "feat: agregar agente de detección de fraude"`.
4. Asegurarse de que `smoke_test.bat` pasa.
5. Asegurarse de que `python -m evaluation.metrics` no baja el pass rate.
6. Abrir PR describiendo el cambio y referenciando el issue.
