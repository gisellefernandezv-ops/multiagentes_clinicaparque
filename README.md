# Sistema Multiagente de Aprobación de Facturas

> Trabajo Práctico — Sistemas Multiagentes (Universidad de Palermo)
> Estado: ✅ operativo · Backend API corriendo en `http://localhost:8000`

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
10. [10. Dashboard del Sistema](#10-dashboard-del-sistema)
11. [11. Portal de Proveedores](#11-portal-de-proveedores)
12. [12. Troubleshooting / Fixes aplicados](#12-troubleshooting--fixes-aplicados)
13. [13. Notas técnicas y decisiones de diseño](#13-notas-técnicas-y-decisiones-de-diseño)

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
| **UI** | FastAPI + React | built-in | Backend API con dashboard y portal de proveedores incluido. |

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
│ CAPA 4 — UI               │ FastAPI + React (Dashboard +    │
│                           │ Supplier Portal)                  │
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

### 4.1. Input

El usuario (o un sistema externo) envía un JSON con la factura al orquestador:

```json
{
  "invoice_id": "INV-2025-001",
  "supplier_id": "SUP001",
  "supplier_name": "TechCorp SA",
  "amount": 45000,
  "currency": "ARS",
  "invoice_date": "2025-06-15"
}
```

### 4.2. Secuencia de pasos

1. **Guardrail estructural**: valida que los campos obligatorios estén
   presentes y en formato correcto. Si falla → `REJECTED` inmediato.

2. **Validator Agent**: consulta `supplier_lookup_tool` para verificar que
   el proveedor exista y esté `ACTIVE`. Si no → `REJECTED`.

3. **Contract Agent**: consulta `search_contract_tool` (RAG) para obtener
   el contrato vigente del proveedor. Extrae el límite contractual.
   Si `amount > contract_limit` → `REJECTED`.

4. **Guardrail absoluto**: si `amount > $500.000` → `ESCALATED`
   (revisión humana obligatoria).

5. **Payment Agent**: si todo OK, persiste en SQLite con
   `register_payment_tool`. Devuelve `confirmation_id`.

### 4.3. Output

```json
{
  "decision": "APPROVED",
  "invoice_id": "INV-2025-001",
  "supplier_id": "SUP001",
  "amount": 45000,
  "guardrail_action": "APPROVED",
  "validation_status": "completed",
  "contract_status": "within_limit",
  "payment_status": "PENDING_PAYMENT",
  "confirmation_id": "PAY-A1B2C3D4",
  "guardrail_reason": ""
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
├── start_server.py             ← script para levantar el backend
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
│   ├── payments.db             ← SQLite (auto-generado)
│   └── new invoices/           ← facturas pendientes de procesar
│
├── sessions/                   ← gestión de sesiones ADK
│   └── session_manager.py      ← InvoiceSessionManager (wrapper)
│
├── platform/                   ← Backend API + Frontend
│   ├── backend/
│   │   ├── main.py            ← FastAPI app principal
│   │   ├── settings.py        ← configuración
│   │   ├── inbox_router.py    ← endpoints de inbox y dashboard
│   │   ├── supplier_portal_router.py ← endpoints del portal
│   │   └── watcher.py         ← file watcher del inbox
│   ├── frontend/              ← UI del sistema
│   │   ├── index.html         ← página principal
│   │   ├── app.js             ← lógica JavaScript
│   │   └── InvoiceApprovalSystem.jsx ← componente React
│   ├── data/                  ← datos del platform
│   │   ├── inbox/             ← facturas pendientes
│   │   ├── processed/         ← facturas procesadas
│   │   ├── rejected/          ← facturas rechazadas
│   │   └── suppliers.db       ← base de datos de proveedores
│   └── services/              ← microservicios
│       ├── supplier_service/   ← servicio de proveedores
│       └── contract_service/   ← servicio de contratos
│
├── supplier_portal/            ← Portal de Proveedores
│   ├── index.html             ← página principal
│   └── style.css              ← estilos
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

### 7.1. Levantar el Backend API

```bash
cd invoice_approval_system
python start_server.py
```

El servidor queda en `http://localhost:8000` con:
- Dashboard del sistema
- Portal de proveedores (`/supplier`)
- Endpoints de inbox y procesamiento

### 7.2. Levantar la UI de ADK (alternativa)

Desde el directorio **padre** del proyecto:

```bash
adk web invoice_approval_system
```

La UI queda en `http://localhost:8000`.

### 7.3. Smoke tests (sin UI)

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

### 7.4. Evaluación completa

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

## 10. Dashboard del Sistema

El sistema incluye un **Dashboard** que muestra estadísticas en tiempo real
sobre el procesamiento de facturas.

### 10.1. Endpoints disponibles

| Endpoint | Método | Descripción |
|---|---|---|
| `/dashboard` | GET | Estadísticas generales |
| `/inbox` | GET | Lista de facturas pendientes |
| `/inbox/process/{filename}` | POST | Procesar una factura |
| `/inbox/process-all` | POST | Procesar todas las facturas |

### 10.2. Métricas del Dashboard

- **Facturas en inbox**: archivos pendientes de procesar
- **Facturas procesadas**: aprobadas + rechazadas + escaladas
- **Decisiones por tipo**: conteo de cada estado
- **Total aprobado**: suma de montos de facturas aprobadas
- **Últimos pagos**: listado de las facturas procesadas más recientes

### 10.3. Ejemplo de respuesta

```json
{
  "inbox_count": 15,
  "processed_count": 8,
  "rejected_files": 2,
  "decisions": {
    "APPROVED": 5,
    "REJECTED": 2,
    "ESCALATED": 1
  },
  "total_amount_approved": 393000.0,
  "recent": [...]
}
```

---

## 11. Portal de Proveedores

El **Portal de Proveedores** permite a los proveedores consultar el estado
de sus facturas directamente.

### 11.1. Acceso

```
http://localhost:8000/supplier
```

### 11.2. Login

Los proveedores pueden identificarse con:
- **CUIT**: `30-71234567-0`
- **ID de proveedor**: `SUP001`
- **Nombre**: `TechCorp SA`

### 11.3. Proveedores de prueba

| ID | Nombre | CUIT | Estado | Facturas |
|---|---|---|---|---|
| SUP001 | TechCorp SA | 30-71234567-0 | ACTIVO | 3 |
| SUP002 | Papelería Norte SRL | 30-69874523-1 | ACTIVO | 2 |
| SUP003 | Servicios Rápidos SA | 30-70111222-3 | INACTIVO | 1 |
| SUP004 | Limpieza Total SRL | 30-70555666-7 | ACTIVO | 2 |
| SUP005 | Consultoría Digital SA | 30-71234999-2 | ACTIVO | 2 |

### 11.4. Funcionalidades

- **Vista de facturas**: lista todas las facturas del proveedor
- **Filtros**: por estado (Aprobadas, Pendientes, Rechazadas, Escaladas)
- **Detalle**: al hacer clic en una factura se ve el detalle completo
- **Chat**: comunicación con el departamento de Cuentas a Pagar

### 11.5. Endpoints del API

| Endpoint | Método | Descripción |
|---|---|---|
| `/supplier/validate` | POST | Validar proveedor |
| `/supplier/invoices/{id}` | GET | Obtener facturas de un proveedor |

---

## 12. Troubleshooting / Fixes aplicados

### 12.1. Bug detectado al instalar: `chromadb` 1.5.x rompe con `google-generativeai` 0.8.6

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

### 12.2. Encoding issues en Windows

**Síntoma**: `UnicodeEncodeError: 'charmap' codec can't encode character
'\u2717'` al imprimir tildes/emojis en consola Windows.

**Fix**: usar `set PYTHONIOENCODING=utf-8` antes de los comandos Python,
o reemplazar caracteres unicode en los `print()` por ASCII (`[OK]` en
vez de `✓`).

### 12.3. ADK Web no encuentra los módulos del proyecto

**Síntoma**: `ModuleNotFoundError: No module named 'agents'`.

**Causa**: ADK busca el entry point desde el directorio donde se invoca.
Si invocamos `adk web invoice_approval_system` desde el padre y el proyecto
no tiene `__init__.py` en sus sub-paquetes, los imports relativos fallan.

**Fix**: `agent.py` agrega explícitamente `PROJECT_ROOT` a `sys.path` antes
de los imports.

### 12.4. Dashboard no muestra datos reales

**Síntoma**: El dashboard muestra `0` en todas las estadísticas.

**Causa**: La ruta de `payments_db` apuntaba a `platform/data/payments.db`
en lugar de `data/payments.db`.

**Fix**: Corregida la ruta en `platform/backend/settings.py`.

### 12.5. Portal de proveedores no encuentra proveedores

**Síntoma**: Error "no such table: suppliers" al hacer login.

**Causa**: El router buscaba la tabla `suppliers` en `payments.db` en lugar
de `suppliers.db`.

**Fix**: Corregida la conexión a `SUPPLIERS_DB` en
`platform/backend/supplier_portal_router.py`.

---

## 13. Notas técnicas y decisiones de diseño

### 13.1. Por qué `output_key` y no transferencia manual de state

ADK ofrece `output_key="X"` que automáticamente escribe el último mensaje
del agente en `state["X"]`. Esto evita que el orquestador tenga que
*leer* la respuesta textual del sub-agente y parsearla. Más robusto y
declarativo.

### 13.2. Por qué un guardrail determinístico + LLM judge separado

- **Guardrail determinístico**: filtra *inputs malos* antes de gastar tokens.
- **LLM judge (en evaluación)**: mide *calidad de las justificaciones*
  generadas por el orquestador.

Son ortogonales: el primero protege al sistema en producción, el segundo
mide la calidad del output para iterar.

### 13.3. Por qué `task_type` distinto en ingesta vs query

`RETRIEVAL_DOCUMENT` optimiza los embeddings para ser *indexados* (más
distinguibles entre sí), mientras que `RETRIEVAL_QUERY` los optimiza para
ser *comparables* contra documentos. Usar el correcto mejora la precisión
del retrieval en ~5-10%.

### 13.4. Por qué registrar TODO (no solo aprobaciones)

La auditoría exige trazabilidad completa: incluso un REJECTED queda
registrado con su `rejection_reason`. Esto permite:

- Reportes de "facturas rechazadas este mes".
- Análisis de patrones de fraude.
- Compliance / auditorías externas.

### 13.5. Limitaciones conocidas

1. **Sin reintentos explícitos**: si una tool falla, el orquestador no
   reintenta automáticamente. Depende del LLM decidir qué hacer.
2. **`supplier_lookup_tool` es un mock en memoria**: para producción
   debería ser una llamada HTTP al servicio real de proveedores.
3. **Sin autenticación en la API**: la UI es local, no expone a internet.
4. **`InMemorySessionService` pierde sesiones al reiniciar**: usar
   `DatabaseSessionService` o `VertexAISessionService` en producción.
