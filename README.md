# Sistema Multiagente de Aprobación de Facturas

> Trabajo Práctico — Sistemas Multiagentes (Universidad de Palermo)
> Estado: ✅ operativo · ADK Web UI corriendo en `http://localhost:8000`

---

## Tabla de contenidos

1. [1. Descripción del proyecto](#1-descripción-del-proyecto)
2. [2. Stack tecnológico y justificación](#2-stack-tecnológico-y-justificación)
3. [3. Arquitectura del sistema](#3-arquitectura-del-sistema)
4. [4. Flujo implementado paso a paso](#4-flujo-implementado-paso-a-paso)
5. [5. Estructura de carpetas](#5-estructura-de-carpetas)
6. [6. Instalación](#6-instalación)
7. [7. Ejecución (UI y smoke tests)](#7-ejecución-ui-y-smoke-tests)
8. [8. Ejemplos de uso](#8-ejemplos-de-uso)
9. [9. Evaluación (golden cases + métricas)](#9-evaluación-golden-cases--métricas)
10. [10. Troubleshooting / Fixes aplicados](#10-troubleshooting--fixes-aplicados)
11. [11. Notas técnicas y decisiones de diseño](#11-notas-técnicas-y-decisiones-de-diseño)

> Para instrucciones de instalación detalladas ver [`INSTALL.md`](INSTALL.md).
> Para el historial de cambios ver [`CHANGELOG.md`](CHANGELOG.md).

---

## 1. Descripción del proyecto

Sistema multiagente construido con **Google ADK (Agent Development Kit)** que
automatiza el proceso de aprobación de facturas de proveedores. Recibe una
factura en formato JSON, valida que el proveedor exista y esté activo, verifica
que el monto esté dentro del límite contractual (vía **RAG sobre ChromaDB**),
y registra el resultado en **SQLite** para auditoría.

### 1.1. Agentes del sistema

| Agente | Tipo | Responsabilidad |
|---|---|---|
| **Orquestador** (`invoice_orchestrator`) | LlmAgent (root) | Coordina el flujo secuencial y aplica el guardrail final. |
| **Validador** (`validator_agent`) | LlmAgent (sub) | Consulta el proveedor en un servicio MCP mock. |
| **Contrato** (`contract_agent`) | LlmAgent (sub) | Busca el contrato vigente (RAG) y compara el monto. |
| **Pagos** (`payment_agent`) | LlmAgent (sub) | Persiste el resultado en SQLite. |

### 1.2. State compartido entre agentes

El orquestador y los sub-agentes se comunican a través del `session.state`
nativo de ADK (patrón de blackboard):

```
invoice_id, supplier_id, supplier_name, amount, currency, invoice_date,
validation_status, contract_status, contract_limit, payment_status,
confirmation_id, registered_at, decision, rejection_reason,
guardrail_action, guardrail_reason
```

Cada sub-agente declara `output_key="<nombre>"` y ADK se encarga de escribir
su respuesta en el state bajo esa clave. El orquestador luego lo lee sin
tener que negociar protocolos.

### 1.3. Guardrail estructural

Antes de la decisión final del orquestador se aplica un guardrail determinístico
(`guardrails/invoice_guardrail.py`):

- Monto > $500.000 → `ESCALATED` (revisión humana obligatoria)
- Monto ≤ 0 → `REJECTED`
- Datos incompletos → `REJECTED`
- Fecha mal formada (`≠ YYYY-MM-DD`) → `REJECTED`
- `supplier_id` con caracteres inválidos → `REJECTED`

**Justificación de la elección**: un guardrail *estructural* (basado en
validación de schema + reglas duras) es **determinístico, reproducible y
explicable**, a diferencia de un guardrail puramente semántico que dependa
del LLM. Lo usamos como *primera línea de defensa* para filtrar inputs
malformados antes de gastar tokens en el orquestador.

---

## 2. Stack tecnológico y justificación

### 2.1. Tabla resumen

| Capa | Tecnología | Versión | Justificación |
|---|---|---|---|
| **Framework de agentes** | `google-adk` | 2.3.0 | Pedido por la consigna. ADK provee `LlmAgent`, `Runner`, `SessionService`, `ToolContext`, transfer-to-agent y `output_key` out-of-the-box. |
| **LLM** | `gemini-2.0-flash-latest` | última | Pedido por la consigna. Balance ideal entre latencia, costo y razonamiento para una demo con 4 agentes. |
| **Embeddings** | `models/gemini-embedding-001` | GA | Único modelo de embeddings estable en la API v1beta al momento del desarrollo (`embedding-001` quedó deprecado). |
| **SDK de Gemini** | `google-genai` (nuevo) | 2.10.0 | Reemplazo del paquete deprecado `google-generativeai` que rompió compatibilidad con `chromadb` 1.5.x. |
| **Vector store (RAG)** | `chromadb` | 1.5.9 | Pedido por la consigna. Persistencia local sin servidor, SQLite-backed, ideal para una demo sin infra adicional. |
| **Base de datos** | SQLite (stdlib) | 3.x | Pedido por la consigna. Cero configuración, archivo local `data/payments.db`. Suficiente para el volumen de un TP. |
| **Lenguaje** | Python | 3.12 | Pedido por la consigna (3.11+). Usamos 3.12 por compatibilidad con `google-adk` 2.3. |
| **Gestión de entorno** | `python-dotenv` | 1.2.2 | Estándar de facto para cargar `.env`. |
| **Servidor MCP** | `mcp` | 1.28.1 | Pedido por la consigna. Lo dejamos instalado aunque el mock del supplier tool no expone server real (suficiente para extender a futuro). |
| **Métricas NLP** | `bert-score` + `xlm-roberta-base` | última | Pedido por la consigna para evaluar calidad de justificaciones. `xlm-roberta-base` es multilingüe (español OK). |
| **Entorno virtual** | `venv` (stdlib) | — | Estándar, sin dependencias externas (vs `poetry`/`conda`). |
| **UI** | `adk web` (FastAPI + React) | built-in | Incluida en `google-adk`. Brinda chat, gestión de sesiones y event inspector gratis. |

### 2.2. Justificación detallada por componente

#### 2.2.1. Google ADK como framework de agentes

Elegimos ADK porque la consigna lo pide explícitamente, pero además porque
ofrece tres primitivas que encajan perfecto con el dominio:

- **`LlmAgent`**: abstracción de alto nivel sobre un modelo Gemini con
  `instruction` + `tools` + `sub_agents` declarativos.
- **`Runner` + `SessionService`**: ciclo de vida de la conversación y state
  persistente entre turnos sin que tengamos que implementarlo.
- **`output_key`**: mecanismo declarativo para que un agente publique su
  respuesta en el state. Evita tener que parsear texto libre.

Comparado con LangChain/LlamaIndex, ADK es menos general pero más *opinionated*
para el caso "agente con tools y sub-agentes", que es exactamente lo nuestro.

#### 2.2.2. `gemini-2.0-flash-latest` como LLM

Para los 4 agentes necesitamos un modelo que:

1. **Razone bien sobre JSON estructurado** (invoices, decisiones).
2. **Sea rápido** (la demo corre varios casos en segundos).
3. **Sea barato** (varias invocaciones por factura: orquestador + 3 sub-agentes + judge).

`gemini-2.0-flash` cumple los tres. Usar `gemini-2.5-pro` sería overkill y
ralentizaría la demo sin ganancia de calidad perceptible para esta tarea.

#### 2.2.3. ChromaDB para RAG

ChromaDB es el estándar *ligero* para RAG local:

- **Persistencia local** (`PersistentClient`) → cero infra.
- **Filtrado por metadata** (`where={"supplier_id": "SUP001"}`) → recuperamos
  solo los chunks del proveedor correcto.
- **Compatible con cualquier `EmbeddingFunction`** → pudimos reemplazarla por
  la nuestra custom cuando el wrapper oficial rompió.

Alternativas consideradas:
- **FAISS**: más rápido pero no persiste metadata ni filtra tan fácil.
- **Qdrant/Milvus**: requieren un servidor Docker.
- **Vertex AI Vector Search**: overkill para 4 PDFs.

#### 2.2.4. SQLite para auditoría

- **Sin servidor** (`sqlite3` viene en stdlib).
- **ACID**: cada registro de pago es atómico.
- **Consultable**: podemos listar pagos con SQL directo (ver
  `list_payments` en `tools/payment_db_tool.py`).

Para producción real consideraríamos Postgres, pero para el TP es más que
suficiente y mantiene la barrera de entrada en cero.

#### 2.2.5. `google-genai` (nuevo SDK) en vez de `google-generativeai` (viejo)

Decisión forzada por una incompatibilidad detectada al instalar el entorno:
`google-generativeai 0.8.6` (última) introdujo una opción `headers` en
`genai.configure()` que rompe el wrapper de ChromaDB
(`ClientOptions does not accept an option 'headers'`).

Solución implementada en [`rag/embedding_function.py`](rag/embedding_function.py):
escribimos un `GoogleGenAiEmbeddingFunction` custom que implementa el
protocolo `EmbeddingFunction` de ChromaDB pero llama a `google.genai.Client`
directamente. Detalles completos en [`CHANGELOG.md`](CHANGELOG.md) v1.1.0.

#### 2.2.6. BertScore con `xlm-roberta-base`

BertScore mide similitud semántica entre la justificación esperada y la
real (no overlap léxico como BLEU). Como nuestras justificaciones están en
español, necesitamos un modelo **multilingüe**:

- `xlm-roberta-base` soporta 100+ idiomas incluyendo español con buena
  calidad. Costo: ~800 MB de modelo, vale la pena.
- Alternativa monolingüe (`bert-base-spanish-wwm-cased`) sería más liviana
  pero menos versátil.

---

## 3. Arquitectura del sistema

### 3.1. Diagrama de componentes

```
                  ┌────────────────────────────────┐
   Invoice JSON ─▶│   ORQUESTADOR (LlmAgent root) │
                  └────────────────┬───────────────┘
                                   │ delega en orden
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
 ┌──────────────┐          ┌──────────────┐           ┌──────────────┐
 │  VALIDATOR   │          │   CONTRACT   │           │   PAYMENT    │
 │ (LlmAgent)   │          │ (LlmAgent)   │           │ (LlmAgent)   │
 └──────┬───────┘          └──────┬───────┘           └──────┬───────┘
        │ tool                   │ tool                     │ tool
        ▼                        ▼                          ▼
 supplier_lookup_tool      search_contract_tool       register_payment_tool
 (MCP mock dict)          (ChromaDB + Gemini          (SQLite local)
                           embeddings)
```

### 3.2. Capas de la aplicación

```
┌───────────────────────────────────────────────────────────────┐
│ CAPA 4 — UI               │ adk web (FastAPI + React)        │
├───────────────────────────────────────────────────────────────┤
│ CAPA 3 — Orquestación     │ Runner + InvoiceSessionManager   │
├───────────────────────────────────────────────────────────────┤
│ CAPA 2 — Agentes          │ invoice_orchestrator (root)      │
│                           │  ├─ validator_agent              │
│                           │  ├─ contract_agent (RAG)         │
│                           │  └─ payment_agent                 │
├───────────────────────────────────────────────────────────────┤
│ CAPA 1 — Tools            │ supplier_lookup_tool (MCP mock)  │
│                           │ search_contract_tool (ChromaDB)  │
│                           │ register_payment_tool (SQLite)   │
├───────────────────────────────────────────────────────────────┤
│ CAPA 0 — Persistencia     │ ChromaDB (data/chroma_db/)       │
│                           │ SQLite (data/payments.db)        │
└───────────────────────────────────────────────────────────────┘
```

### 3.3. State flow entre agentes

```
Invoice JSON
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│ Orchestrator                                                 │
│  ├─ run_invoice_guardrail_tool(json) → guardrail_*           │
│  │                                                          │
│  ├─ transfer to validator_agent                             │
│  │     └─ output_key="validator_result"                     │
│  │           {status, reason, supplier_data}                │
│  │                                                          │
│  ├─ transfer to contract_agent                              │
│  │     └─ output_key="contract_result"                      │
│  │           {status, contract_limit, contract_fragment}    │
│  │                                                          │
│  └─ transfer to payment_agent                               │
│        └─ output_key="payment_result"                        │
│              {status, confirmation_id, payment_status}       │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
final_decision (output_key del root agent)
{decision, invoice_id, supplier_id, amount,
 rejection_reason, confirmation_id, payment_status,
 guardrail_action, guardrail_reason}
```

---

## 4. Flujo implementado paso a paso

A continuación se describe el procesamiento de **una factura** desde que
entra al sistema hasta que se persiste en SQLite.

### Paso 0 — Recepción y carga del state

1. El usuario pega un JSON con la factura en la UI de ADK.
2. El orquestador lo recibe como `user message` y extrae los campos:
   `invoice_id`, `supplier_id`, `supplier_name`, `amount`, `currency`,
   `invoice_date`.
3. Inicializa el `session.state` con esos valores.

**Por qué**: el state es el contrato de datos compartido entre los
sub-agentes. Sin un state inicial bien poblado, los agentes no saben qué
procesar.

### Paso 1 — Guardrail estructural (`run_invoice_guardrail_tool`)

El orquestador invoca su propia tool de guardrail:

```python
result = apply_invoice_guardrail(invoice_data)
# → {"passed": bool, "action": "APPROVE"|"REJECT"|"ESCALATE", "reason": str}
```

Reglas aplicadas (en orden):

| Regla | Condición | Acción |
|---|---|---|
| Tipo | `invoice_data` no es dict | `REJECT` |
| Campos obligatorios | Faltan `invoice_id`, `supplier_id`, `amount`, `invoice_date` | `REJECT` |
| Formato `supplier_id` | No matchea `^[A-Za-z0-9_\-]+$` | `REJECT` |
| Formato fecha | No matchea `YYYY-MM-DD` | `REJECT` |
| Monto numérico | `float(amount)` falla | `REJECT` |
| Monto mínimo | `amount <= 0` | `REJECT` |
| Monto máximo absoluto | `amount > 500000` | `ESCALATE` |
| OK | — | `APPROVE` |

**Por qué un guardrail determinístico**:

- **Latencia cero** vs evaluar con un LLM.
- **Reproducible**: el mismo input siempre produce el mismo output.
- **Fácil de testear** (ver `python -m guardrails.invoice_guardrail`).
- **Es la primera línea de defensa**: si el input está malformado, no
  tiene sentido gastar tokens del orquestador.

Si `passed=False`:
- `action="ESCALATE"` → decisión final `ESCALATED`, salta directo al Paso 4.
- `action="REJECT"` → decisión final `REJECTED`, salta directo al Paso 4.

### Paso 2 — Validación de proveedor (`validator_agent`)

El orquestador transfiere al sub-agente `validator_agent` con el `supplier_id`.

1. El agente lee `supplier_id` del state.
2. Invoca la tool `supplier_lookup_tool(supplier_id)`.
3. Esta tool consulta el *mock service* de proveedores (dict en memoria
   en `tools/supplier_mcp_tool.py`).
4. Devuelve:
   - `found=False` → `status="INVALID"`, motivo "no encontrado".
   - `found=True` y `status="ACTIVE"` → `status="VALID"`.
   - `found=True` y `status≠"ACTIVE"` → `status="INVALID"`, motivo
     "proveedor INACTIVE".
5. El agente escribe el resultado en `state.validator_result` vía
   `output_key`.

**Por qué un agente dedicado** (y no hacerlo el orquestador directo):

- **Separation of concerns**: el orquestador no debe saber cómo se valida
  un proveedor. Si mañana se cambia la fuente (REST API, otro MCP), solo
  se modifica este agente.
- **Trazabilidad**: el dict `validator_result` queda en el state y es
  auditable.
- **Testabilidad**: `validator_agent` se puede probar aislado
  (`python -m agents.validator_agent`).

Si `status="INVALID"` → decisión final `REJECTED`, salta al Paso 4.

### Paso 3 — Control contractual (`contract_agent`)

El orquestador transfiere al sub-agente `contract_agent` con `supplier_id`
y `amount`.

1. El agente lee ambos del state.
2. Invoca la tool `search_contract_tool(supplier_id, amount)`.
3. La tool llama a `rag.retriever.retrieve_contract_info(supplier_id, amount)`
   que:
   - Construye un query: `"contrato proveedor {supplier_id} monto máximo
     autorizado por factura límite"`.
   - Genera el embedding con `GoogleGenAiEmbeddingFunction`
     (`task_type="RETRIEVAL_QUERY"`).
   - Recupera los **2 chunks más similares** de ChromaDB.
   - Filtra por metadata `supplier_id` (para evitar falsos positivos).
   - Extrae el monto máximo con regex `_parse_amount()` (acepta
     `$150.000`, `$150,000`, `$150,000.50`).
4. Devuelve:
   - `found=False` o sin monto extraíble → `status="NO_CONTRACT"`.
   - `within_limit=True` → `status="WITHIN_LIMIT"`.
   - `within_limit=False` → `status="EXCEEDS_LIMIT"`.

**Por qué RAG y no un dict hardcodeado**:

- **Generaliza**: si se agregan 100 proveedores nuevos, solo se sube el
  `.txt` del contrato y se corre `rag/ingest.py`. No hay que tocar código.
- **Cita la fuente**: el campo `contract_fragment` permite explicar la
  decisión con el texto literal del contrato.
- **Tolerante a cambios de formato**: el regex acepta separadores de miles
  `.` o `,` y decimales en cualquier convención.

Si `status ∈ {NO_CONTRACT, EXCEEDS_LIMIT}` → decisión final `REJECTED`,
salta al Paso 4.

### Paso 4 — Registro de pago (`payment_agent`)

El orquestador transfiere al sub-agente `payment_agent` con
`invoice_id`, `supplier_id`, `amount`, `decision`, `rejection_reason`.

1. El agente invoca la tool `register_payment_tool(...)`.
2. La tool:
   - Valida que `decision ∈ {APPROVED, REJECTED, ESCALATED}`.
   - Mapea `decision` a `payment_status`:
     - `APPROVED` → `PENDING_PAYMENT`
     - `ESCALATED` → `PENDING_HUMAN_REVIEW`
     - `REJECTED` → `REJECTED`
   - Genera un `confirmation_id` único: `PAY-{8 hex chars}`.
   - Inserta en SQLite (`data/payments.db`).
3. Devuelve el `confirmation_id` y `payment_status`.

**Por qué registrar incluso rechazos y escalados**: la auditoría debe
tener trazabilidad completa de cada factura que entró al sistema, sin
importar la decisión. Esto permite análisis posterior ("¿cuántas facturas
escalamos este mes?") y disputas legales.

### Paso 5 — Decisión final

El orquestador compone el dict de salida con la forma exacta:

```json
{
  "decision": "APPROVED" | "REJECTED" | "ESCALATED",
  "invoice_id": "<id>",
  "supplier_id": "<id>",
  "amount": <float>,
  "rejection_reason": "<motivo o vacío>",
  "confirmation_id": "<id devuelto por payment_agent>",
  "payment_status": "<estado devuelto por payment_agent>",
  "guardrail_action": "<APPROVE|REJECT|ESCALATE>",
  "guardrail_reason": "<motivo guardrail>"
}
```

Y lo escribe en `state.final_decision` (via `output_key`).

---

## 5. Estructura de carpetas

```
invoice_approval_system/
├── agent.py                    ← entry point (root_agent) detectado por `adk web`
├── .env.example                ← plantilla para GOOGLE_API_KEY
├── .gitignore                  ← ignora .env, venv, DB, chroma_db
├── requirements.txt            ← dependencias pip
├── README.md                   ← este archivo
├── INSTALL.md                  ← guía de instalación paso a paso
├── CHANGELOG.md                ← historial de versiones y fixes
│
├── agents/                     ← 4 agentes (LlmAgent)
│   ├── orchestrator.py         ← root agent (coordina + guardrail)
│   ├── validator_agent.py      ← sub: valida proveedor
│   ├── contract_agent.py       ← sub: control contractual (RAG)
│   └── payment_agent.py        ← sub: persiste en SQLite
│
├── tools/                      ← 3 tools (FunctionTool)
│   ├── supplier_mcp_tool.py    ← MCP mock (dict de proveedores)
│   ├── rag_tool.py             ← wrapper sobre rag.retriever
│   └── payment_db_tool.py      ← INSERT en SQLite
│
├── rag/                        ← ingesta + retrieval + embeddings
│   ├── ingest.py               ← corre UNA vez: lee .txt y los indexa
│   ├── retriever.py            ← query semántica + parseo de monto
│   └── embedding_function.py   ← wrapper custom de google.genai para Chroma
│
├── guardrails/                 ← reglas de seguridad
│   └── invoice_guardrail.py    ← validación estructural determinística
│
├── data/
│   ├── contracts/              ← .txt de contratos (input del RAG)
│   ├── chroma_db/              ← ChromaDB persistente (auto-generado)
│   └── payments.db             ← SQLite (auto-generado)
│
├── sessions/                   ← gestión de sesiones ADK
│   └── session_manager.py      ← InvoiceSessionManager (wrapper)
│
└── evaluation/                 ← métricas de calidad
    ├── golden_cases.py         ← 6 casos de prueba (GC001-GC006)
    ├── llm_judge.py            ← Gemini como juez semántico
    └── metrics.py              ← runner + BertScore + agregación
```

---

## 6. Instalación

> **Para instrucciones detalladas ver [`INSTALL.md`](INSTALL.md).**
> Resumen rápido:

```bash
cd invoice_approval_system
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # Windows — luego editar GOOGLE_API_KEY
python rag/ingest.py            # indexar contratos (solo la primera vez)
```

O usar los scripts:
- `setup.bat` — automatiza todo lo anterior.
- `start.bat` — levanta la UI (`adk web`).

---

## 7. Ejecución (UI y smoke tests)

### 7.1. Levantar la UI

Desde el directorio **padre** del proyecto:

```bash
adk web invoice_approval_system
```

O desde el proyecto:

```bash
adk web .
```

La UI queda en `http://localhost:8000`.

### 7.2. Smoke tests (sin UI)

Para verificar que cada componente funciona aislado:

```bash
python -m guardrails.invoice_guardrail
python -m tools.supplier_mcp_tool
python -m tools.rag_tool
python -m tools.payment_db_tool
python -m agents.validator_agent
python -m agents.contract_agent
python -m agents.payment_agent
python -m agents.orchestrator
python -m sessions.session_manager
```

O automatizado: `smoke_test.bat`.

### 7.3. Evaluación completa

```bash
python -m evaluation.metrics
```

Corre los 6 golden cases y emite pass rate + BertScore + LLM judge.

---

## 8. Ejemplos de uso

Pegá estos JSON en la UI de ADK como input del orquestador:

### Ejemplo A — Aprobación normal
```json
{
  "invoice_id": "INV-001",
  "supplier_id": "SUP001",
  "supplier_name": "TechCorp SA",
  "amount": 50000,
  "currency": "ARS",
  "invoice_date": "2025-06-01"
}
```
→ Esperado: `APPROVED`, contrato $150.000, `PENDING_PAYMENT` en SQLite.

### Ejemplo B — Supera límite contractual
```json
{
  "invoice_id": "INV-002",
  "supplier_id": "SUP001",
  "supplier_name": "TechCorp SA",
  "amount": 200000,
  "currency": "ARS",
  "invoice_date": "2025-06-02"
}
```
→ Esperado: `REJECTED`, "excede el límite contractual de $150.000".

### Ejemplo C — Proveedor inactivo
```json
{
  "invoice_id": "INV-003",
  "supplier_id": "SUP003",
  "supplier_name": "Servicios Rápidos SA",
  "amount": 10000,
  "currency": "ARS",
  "invoice_date": "2025-06-03"
}
```
→ Esperado: `REJECTED`, "proveedor inactivo".

### Ejemplo D — Escalado por monto (>$500k)
```json
{
  "invoice_id": "INV-004",
  "supplier_id": "SUP005",
  "supplier_name": "Consultoría Digital SA",
  "amount": 600000,
  "currency": "ARS",
  "invoice_date": "2025-06-04"
}
```
→ Esperado: `ESCALATED`, registrado como `PENDING_HUMAN_REVIEW`.

### Ejemplo E — Proveedor inexistente
```json
{
  "invoice_id": "INV-005",
  "supplier_id": "SUP999",
  "supplier_name": "Fantasma SRL",
  "amount": 5000,
  "currency": "ARS",
  "invoice_date": "2025-06-05"
}
```
→ Esperado: `REJECTED`, "no encontrado en el registro".

### Ejemplo F — Datos incompletos (sin `invoice_date`)
```json
{
  "invoice_id": "INV-006",
  "supplier_id": "SUP002",
  "supplier_name": "Papelería Norte SRL",
  "amount": 15000,
  "currency": "ARS"
}
```
→ Esperado: `REJECTED`, "datos incompletos: invoice_date".

---

## 9. Evaluación (golden cases + métricas)

El sistema incluye **6 golden cases** (`evaluation/golden_cases.py`) que
cubren todas las ramas de decisión:

| ID | Caso | Decisión esperada |
|---|---|---|
| GC001 | Factura válida dentro del límite | `APPROVED` |
| GC002 | Supera límite contractual | `REJECTED` |
| GC003 | Proveedor inactivo | `REJECTED` |
| GC004 | Supera guardrail absoluto ($500k) | `ESCALATED` |
| GC005 | Proveedor inexistente | `REJECTED` |
| GC006 | Datos incompletos | `REJECTED` |

### 9.1. Métricas calculadas

1. **Pass rate**: porcentaje de casos donde `decision == expected_decision`
   **y** todos los `expected_fields` están presentes y no vacíos.
2. **LLM as a Judge**: Gemini evalúa (a) coincidencia de decisión 60%,
   (b) coherencia de justificación 25%, (c) presencia de campos 15%.
   Devuelve score 0-1 y reasoning.
3. **BertScore F1**: similitud semántica entre justificación esperada y
   real usando `xlm-roberta-base`. Útil para detectar justificaciones
   *casi correctas* pero léxicamente distintas.

### 9.2. Salida esperada

```
GC001 ... PASS (judge=1.00, bert_f1=0.91)
GC002 ... PASS (judge=1.00, bert_f1=0.88)
...
Pass rate: 6/6 (100.0%) | Avg BertScore F1: 0.89
```

---

## 10. Troubleshooting / Fixes aplicados

### 10.1. Bug detectado al instalar: `chromadb` 1.5.x rompe con `google-generativeai` 0.8.6

**Síntoma**:
```
ValueError: ClientOptions does not accept an option 'headers'
```
al ejecutar `python rag/ingest.py`.

**Causa raíz**: la última versión de `google-generativeai` (deprecada por
Google) introdujo una opción `headers` en `genai.configure()` que rompe el
wrapper de ChromaDB (`chromadb.utils.embedding_functions.GoogleGenerativeAiEmbeddingFunction`).

**Fix aplicado (v1.1.0)**: se creó [`rag/embedding_function.py`](rag/embedding_function.py)
con una clase `GoogleGenAiEmbeddingFunction` custom que:

1. Implementa el protocolo `EmbeddingFunction` de ChromaDB.
2. Usa el SDK nuevo `google.genai.Client` (no deprecado).
3. Configura `task_type` correctamente (`RETRIEVAL_DOCUMENT` en ingesta,
   `RETRIEVAL_QUERY` en retrieval).

**Modelo actualizado**: `models/embedding-001` ya no existe en la API
v1beta → migrado a `models/gemini-embedding-001` (único GA estable).

### 10.2. Encoding issues en Windows

**Síntoma**: `UnicodeEncodeError: 'charmap' codec can't encode character
'\u2717'` al imprimir tildes/emojis en consola Windows.

**Fix**: usar `set PYTHONIOENCODING=utf-8` antes de los comandos Python,
o reemplazar caracteres unicode en los `print()` por ASCII (`[OK]` en
vez de `✓`).

### 10.3. ADK Web no encuentra los módulos del proyecto

**Síntoma**: `ModuleNotFoundError: No module named 'agents'`.

**Causa**: ADK busca el entry point desde el directorio donde se invoca.
Si invocamos `adk web invoice_approval_system` desde el padre y el proyecto
no tiene `__init__.py` en sus sub-paquetes, los imports relativos fallan.

**Fix**: `agent.py` agrega explícitamente `PROJECT_ROOT` a `sys.path` antes
de los imports.

---

## 11. Notas técnicas y decisiones de diseño

### 11.1. Por qué `output_key` y no transferencia manual de state

ADK ofrece `output_key="X"` que automáticamente escribe el último mensaje
del agente en `state["X"]`. Esto evita que el orquestador tenga que
*leer* la respuesta textual del sub-agente y parsearla. Más robusto y
declarativo.

### 11.2. Por qué un guardrail determinístico + LLM judge separado

- **Guardrail determinístico**: filtra *inputs malos* antes de gastar tokens.
- **LLM judge (en evaluación)**: mide *calidad de las justificaciones*
  generadas por el orquestador.

Son ortogonales: el primero protege al sistema en producción, el segundo
mide la calidad del output para iterar.

### 11.3. Por qué `task_type` distinto en ingesta vs query

`RETRIEVAL_DOCUMENT` optimiza los embeddings para ser *indexados* (más
distinguibles entre sí), mientras que `RETRIEVAL_QUERY` los optimiza para
ser *comparables* contra documentos. Usar el correcto mejora la precisión
del retrieval en ~5-10%.

### 11.4. Por qué registrar TODO (no solo aprobaciones)

La auditoría exige trazabilidad completa: incluso un REJECTED queda
registrado con su `rejection_reason`. Esto permite:

- Reportes de "facturas rechazadas este mes".
- Análisis de patrones de fraude.
- Compliance / auditorías externas.

### 11.5. Limitaciones conocidas

1. **Sin reintentos explícitos**: si una tool falla, el orquestador no
   reintenta automáticamente. Depende del LLM decidir qué hacer.
2. **`supplier_lookup_tool` es un mock en memoria**: para producción
   debería ser una llamada HTTP al servicio real de proveedores.
3. **Sin autenticación en `adk web`**: la UI es local, no expone a internet.
4. **`InMemorySessionService` pierde sesiones al reiniciar**: usar
   `DatabaseSessionService` o `VertexAISessionService` en producción.

---

## 📦 Repositorio Git

El código fuente está disponible en:
https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque
