# InvoiceFlow — Sistema Multiagente de Aprobación de Facturas

> **Trabajo Práctico — Sistemas Multiagentes** | Universidad de Palermo
>
> **Estado**: ✅ Operativo | **Versión**: 2.3.0 | **Última actualización**: 2026-07-17
>
> 🔗 **Repositorio**: [GitHub](https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque)

---

## 📑 Tabla de Contenidos

1. [Descripción del Proyecto](#1-descripción-del-proyecto)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Stack Tecnológico](#3-stack-tecnológico)
4. [Bases de Datos](#4-bases-de-datos)
5. [Agentes Implementados](#5-agentes-implementados)
6. [Flujo de Negocio](#6-flujo-de-negocio)
7. [Estructura de Carpetas](#7-estructura-de-carpetas)
8. [Instalación Rápida](#8-instalación-rápida)
9. [Ejecución del Sistema](#9-ejecución-del-sistema)
10. [Ejemplos de Uso](#10-ejemplos-de-uso)
11. [Evaluación y Testing](#11-evaluación-y-testing)
12. [API Reference](#12-api-reference)
13. [Troubleshooting](#13-troubleshooting)
14. [Licencia y Créditos](#14-licencia-y-créditos)

---

## 1. Descripción del Proyecto

**InvoiceFlow** es un sistema multiagente que automatiza el proceso de aprobación de facturas de proveedores mediante inteligencia artificial.

### Objetivos Principales

- ✅ Validar proveedores activos contra registros internos
- ✅ Verificar montos contra límites contractuales (vía RAG)
- ✅ Aplicar reglas de negocio (guardrails)
- ✅ Registrar todas las decisiones para auditoría
- ✅ Proporcionar interfaces para proveedores y administradores

### Funcionalidades Clave

| Funcionalidad | Descripción |
|--------------|-------------|
| **Flujo A** | Alta de nuevas facturas con validación completa |
| **Auto-proceso** | Las facturas se procesan automáticamente al subirse al inbox |
| **Flujo B** | Consulta de estado de facturas existentes |
| **Guardrails** | 26 reglas de validación (estructurales, negocio, seguridad) |
| **RAG** | Búsqueda semántica en contratos con ChromaDB |
| **A2A** | Protocolo Agent-to-Agent para auditoría externa |
| **ML** | Modelo de riesgo con scikit-learn |
| **🏢 Proveedores (ABM)** | CRUD completo + contratos con modo EXACTO/NO_SUPERAR |
| **🤖 Asistente IA "GI"** | Chat con memoria y acciones sobre el sistema |

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAPA 4: INTERFAZ DE USUARIO                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌─────────────────────┐                   │
│  │   Back Office       │         │  Supplier Portal    │                   │
│  │   (Administración)  │         │  (Proveedores)      │                   │
│  │   app/frontend/     │         │  supplier_portal/   │                   │
│  └──────────┬──────────┘         └──────────┬──────────┘                   │
│             │                               │                              │
│             └───────────────┬───────────────┘                              │
│                             ▼                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           CAPA 3: ORQUESTACIÓN                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    INVOICE ORCHESTRATOR (ADK)                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │   Router    │  │  Validator  │  │  Contract   │  │   Payment   │  │  │
│  │  │   Agent     │  │   Agent     │  │   Agent     │  │   Agent     │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  │                                                                  │  │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │  │
│  │  │                    GUARDRAIL ENGINE                         │  │  │  │
│  │  │  (26 reglas: VR + BR + SR + CR)                          │  │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                             │                                              │
├─────────────────────────────┼───────────────────────────────────────────────┤
│                           CAPA 2: HERRAMIENTAS (Tools)                      │
├─────────────────────────────┼───────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Supplier    │  │    RAG       │  │   Payment    │  │   Invoice    │    │
│  │  MCP Tool    │  │   Tool       │  │   DB Tool    │  │   Status     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │  Folder      │  │    PDF       │  │    ML        │                      │
│  │  Manager     │  │  Extractor   │  │   Risk       │                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                           CAPA 1: PERSISTENCIA                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   SQLite     │  │  ChromaDB    │  │    Files     │  │    A2A       │    │
│  │ (payments)   │  │  (RAG)       │  │  (PDFs)      │  │  Server      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │   SQLite     │  │   SQLite     │  │   SQLite     │                     │
│  │ (suppliers)  │  │  (chat)      │  │  (inbox)     │                     │
│  │ app/data/    │  │  data/       │  │  data/       │                     │
│  └──────────────┘  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Arquitectura de Microservicios

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           PUERTO 8000                                     │
│                     BACKEND (FastAPI + Uvicorn)                          │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │  Routers: inbox, chat, new_invoices, supplier_portal              │   │
│  │  Orchestrator (pipeline HTTP+SQL directo)                         │   │
│  │  File Watcher (auto-proceso del inbox)                           │   │
│  │  Proxy ABM (evita CORS en browser)                               │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                             │                                              │
│         ┌───────────────────┼───────────────────┐                        │
│         ▼                   ▼                   ▼                        │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                │
│  │  Puerto     │     │  Puerto     │     │  Puerto     │                │
│  │  8001       │     │  8002       │     │  8003       │                │
│  │  Supplier   │     │  Contract   │     │  External   │                │
│  │  Service    │     │  Service    │     │  Auditor    │                │
│  │  (ABM)      │     │  (RAG)      │     │  (A2A)      │                │
│  └─────────────┘     └─────────────┘     └─────────────┘                │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Flujo de Datos entre Componentes

```
Solicitud HTTP
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ FASTAPI Backend (Puerto 8000)                                           │
│  ├── /invoice/new → Orchestrator (pipeline)                             │
│  ├── /invoice/status → InvoiceStatusTool                               │
│  ├── /chat → RouterAgent (ADK)                                         │
│  └── /suppliers/* → Supplier Service Proxy                             │
└─────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (Pipeline producto)                                       │
│  1. Guardrail (validación estructural determinística)                   │
│  2. Supplier Service (validación proveedor) → HTTP GET :8001           │
│  3. Contract Service (RAG + límite) → HTTP GET :8002                   │
│  4. External Auditor (A2A si ESCALATE) → HTTP POST :8003               │
│  5. Persistir → SQLite (payments.db)                                   │
└─────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ RESULTADO                                                               │
│  { decision, confirmation_id, payment_status, rejection_reason }        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Stack Tecnológico

| Componente | Tecnología | Versión | Justificación |
|-----------|------------|---------|---------------|
| **Framework de Agentes** | Google ADK | 2.3.0 | Abstracción de alto nivel para LlmAgent, Runner, SessionService |
| **Modelo LLM** | Gemini 2.0 Flash | latest | Balance ideal latencia/costo/razonamiento |
| **Embeddings** | Gemini Embedding | 001 | Modelo GA estable para ChromaDB |
| **Vector Store (RAG)** | ChromaDB | 1.5.9 | Persistencia local, SQLite-backed, sin servidor |
| **Base de Datos** | SQLite | 3.x | Cero configuración, múltiples archivos |
| **Backend API** | FastAPI | 0.100+ | Alto rendimiento, documentación automática con OpenAPI |
| **Lenguaje** | Python | 3.12 | Requerido (3.11+) |
| **Métricas NLP** | BertScore + XLM-RoBERTa | latest | Evaluación multilingüe de justificaciones |
| **ML** | scikit-learn | latest | Modelo de riesgo predictivo |
| **UI** | HTML/CSS/JS (Vanilla) | — | Frontend ligero sin framework |

---

## 4. Bases de Datos

El sistema utiliza **4 archivos SQLite** para persistencia:

### 4.1 `data/payments.db` — Pagos Procesados

| Tabla | Campos | Descripción |
|-------|--------|-------------|
| `payments` | id, invoice_id, supplier_id, amount, decision, rejection_reason, payment_status, confirmation_id, registered_at, source_file | Registro de todas las facturas procesadas |

**Estructura:**
```sql
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    amount REAL NOT NULL,
    decision TEXT NOT NULL,           -- APPROVED | REJECTED | ESCALATED
    rejection_reason TEXT,
    payment_status TEXT NOT NULL,     -- PENDING_PAYMENT | REJECTED | PENDING_HUMAN_REVIEW
    confirmation_id TEXT NOT NULL,     -- PAY-XXXXXXXX
    registered_at TIMESTAMP,
    source_file TEXT
);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_payments_supplier ON payments(supplier_id);
CREATE INDEX idx_payments_decision ON payments(decision);
```

### 4.2 `app/data/suppliers.db` — Proveedores y Contratos

| Tabla | Campos | Descripción |
|-------|--------|-------------|
| `suppliers` | supplier_id, name, cuit, status, category, email, phone, registered_at | Catálogo de proveedores |
| `contracts` | id, supplier_id, contract_limit, mode, start_date, end_date, file_path, uploaded_at | Contratos vigentes |
| `invoices` | id, invoice_id, supplier_id, amount, currency, invoice_date, state, rejection_reason, confirmation_id, registered_at | Historial de facturas |

**Estructura:**
```sql
CREATE TABLE suppliers (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cuit TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE','INACTIVE','SUSPENDED')),
    category TEXT,
    email TEXT,
    phone TEXT,
    registered_at TEXT NOT NULL
);

CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id TEXT NOT NULL,
    contract_limit REAL NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('EXACTO','NO_SUPERAR')),
    start_date TEXT,
    end_date TEXT,
    file_path TEXT,
    uploaded_at TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT,
    invoice_date TEXT,
    state TEXT,
    rejection_reason TEXT,
    confirmation_id TEXT,
    registered_at TEXT
);
```

### 4.3 `data/chat_sessions.db` — Sesiones de Chat (Asistente GI)

| Tabla | Campos | Descripción |
|-------|--------|-------------|
| `sessions` | id, title, created_at, last_active_at | Sesiones de conversación |
| `messages` | id, session_id, role, content, intent, created_at | Mensajes con roles (user/assistant/system) |

**Estructura:**
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT NOT NULL,
    last_active_at TEXT NOT NULL
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,          -- user | assistant | system
    content TEXT NOT NULL,
    intent TEXT,
    created_at TEXT NOT NULL
);
```

### 4.4 `data/inbox.db` — Cola de Facturas Pendientes

| Tabla | Campos | Descripción |
|-------|--------|-------------|
| `inbox_items` | id, filename, size, status, invoice_id, supplier_id, supplier_name, amount, punto_venta, numero_comprobante, emisor_razon_social, emisor_cuit, tipo_comprobante, cae, codigo_barras, items_count, invoice_date, decision, rejection_reason, confirmation_id, uploaded_at, processed_at, file_path | Facturas en espera de procesamiento |

### 4.5 `data/chroma_db/` — Vector Store (RAG)

| Contenido | Descripción |
|-----------|-------------|
| `*.bin`, `*.sqlite` | Índices vectoriales de contratos |
| Colección: `contracts` | Embeddings de fragmentos de contratos |

---

## 5. Agentes Implementados

### 5.1 Agentes Principales (ADK)

| Agente | Tipo | Responsabilidad | Output Key |
|--------|------|----------------|------------|
| **InvoiceOrchestrator** | LlmAgent (root) | Coordina flujo, aplica guardrail final | `final_decision` |
| **RouterAgent** | LlmAgent (sub) | Clasifica intención del chat | `intent` |
| **ValidatorAgent** | LlmAgent (sub) | Valida proveedor (MCP mock) | `validator_result` |
| **ContractAgent** | LlmAgent (sub) | Controla monto vs contrato (RAG) | `contract_result` |
| **PaymentAgent** | LlmAgent (sub) | Persiste en SQLite | `payment_result` |
| **InvoiceManagerAgent** | LlmAgent (sub) | Gestiona archivos y extracción | `invoice_data` |

### 5.2 Microservicios

| Servicio | Puerto | Responsabilidad | DB |
|---------|--------|-----------------|-----|
| **Supplier Service** | 8001 | ABM de proveedores y contratos | `app/data/suppliers.db` |
| **Contract Service** | 8002 | RAG con ChromaDB | `data/chroma_db/` |
| **External Auditor** | 8003 | Auditoría A2A de facturas escaladas | — |

### 5.3 State Compartido

```python
session.state = {
    # Datos de entrada
    "invoice_id": str,
    "supplier_id": str,
    "supplier_name": str,
    "amount": float,
    "currency": str,
    "invoice_date": str,  # YYYY-MM-DD
    
    # Resultados de agentes
    "guardrail_action": str,      # APPROVE | REJECT | ESCALATE
    "guardrail_reason": str,
    "validator_result": dict,    # {status, reason, supplier_data}
    "contract_result": dict,      # {status, contract_limit, fragment}
    "payment_result": dict,       # {status, confirmation_id, payment_status}
    
    # Decisión final
    "final_decision": dict       # {decision, rejection_reason, ...}
}
```

---

## 6. Flujo de Negocio

### 6.1 Flujo A — Alta de Factura

```
┌─────────────┐
│ Proveedor   │
│ sube PDF    │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ GUARDRAIL (26 reglas)                                            │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ VR (7 reglas) — Validación Estructural                   │    │
│  │ BR (10 reglas) — Reglas de Negocio                       │    │
│  │ SR (5 reglas) — Seguridad                                │    │
│  │ CR (3 reglas) — Continuidad                             │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────┬─────────────────────────────────────────────────────────┘
       │
       ├── REJECT ──→ mensaje de error
       │
       ├── ESCALATE ──→ A2A → ExternalAuditorAgent → revisión humana
       │
       └── APPROVE ──→ siguiente paso
              │
              ▼
       ┌──────────────┐
       │  VALIDATOR   │ ←── Supplier Service (HTTP :8001)
       │   AGENT      │
       └──────┬───────┘
              │
              ├── INVALID ──→ REJECT (proveedor inactivo/no existe)
              │
              └── VALID ──→ siguiente paso
                     │
                     ▼
              ┌──────────────┐
              │  CONTRACT    │ ←── Contract Service (HTTP :8002)
              │   AGENT      │
              └──────┬───────┘
                     │
                     ├── NO_CONTRACT ──→ REJECT
                     ├── EXCEEDS_LIMIT ──→ REJECT
                     │
                     └── WITHIN_LIMIT ──→ siguiente paso
                            │
                            ▼
                     ┌──────────────┐
                     │   PAYMENT    │ ←── SQLite (payments.db)
                     │   AGENT      │
                     └──────┬───────┘
                            │
                            ▼
                     ┌─────────────────┐
                     │  APROBADO ✓    │
                     │  (PENDING)      │
                     └─────────────────┘
```

### 6.2 Flujo B — Consulta de Estado

```
┌─────────────┐
│ Proveedor   │
│ consulta    │
│ estado      │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│ INVOICE STATUS TOOL                   │
│  1. Buscar por invoice_id o supplier │
│  2. Retornar estado actual           │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ RESPUESTA                             │
│  { status, date, amount, reason?,     │
│    payment_info?, auditor_result? }  │
└──────────────────────────────────────┘
```

---

## 7. Estructura de Carpetas

```
invoice_approval_system/
│
├── agent.py                     # Entry point ADK (legacy)
├── .env.example                 # Plantilla variables de entorno
├── .env                         # Variables reales (NO commitear)
├── requirements.txt             # Dependencias Python
├── README.md                    # Este archivo
├── CHANGELOG.md                 # Historial de versiones
├── INSTALL.md                   # Guía de instalación
│
├── agents/                      # Agentes ADK
│   ├── orchestrator.py          # Agente principal (root)
│   ├── router_agent.py          # Clasificador de intenciones (chat)
│   ├── validator_agent.py       # Validador de proveedores
│   ├── contract_agent.py        # Control contractual (RAG)
│   ├── payment_agent.py         # Registro de pagos
│   ├── invoice_manager_agent.py # Gestor de archivos
│   └── __init__.py
│
├── app/                        # APLICAÇÃO PRINCIPAL (NO CORRIGIR)
│   ├── backend/
│   │   ├── main.py             # FastAPI Backend (puerto 8000)
│   │   ├── settings.py         # Configuración
│   │   ├── orchestrator.py     # Pipeline de procesamiento
│   │   ├── service_clients.py  # Clientes HTTP a microservicios
│   │   ├── watcher.py          # File watcher del inbox
│   │   ├── inbox_router.py     # Endpoints de inbox
│   │   ├── chat_router.py      # Endpoints de chat (GI)
│   │   ├── new_invoices_router.py
│   │   └── supplier_portal_router.py
│   ├── frontend/               # Back Office (UI)
│   │   ├── index.html
│   │   ├── app.js
│   │   ├── style.css
│   │   └── InvoiceApprovalSystem.jsx
│   ├── services/
│   │   ├── supplier_service/   # Microservicio (puerto 8001)
│   │   │   └── main.py
│   │   └── contract_service/   # Microservicio (puerto 8002)
│   │       └── main.py
│   ├── scripts/
│   │   ├── demo_real_workflow.py
│   │   └── seed_inbox.py
│   └── data/
│       ├── suppliers.db         # SQLite: proveedores + contratos
│       ├── contracts/           # Archivos .txt de contratos
│       └── chroma_db/          # Vector store (RAG)
│
├── tools/                       # Herramientas (FunctionTool)
│   ├── supplier_mcp_tool.py    # Mock MCP de proveedores
│   ├── rag_tool.py            # Wrapper ChromaDB
│   ├── payment_db_tool.py     # SQLite operations
│   ├── invoice_status_tool.py  # Consulta de estado
│   ├── folder_manager_tool.py  # Gestión de archivos
│   ├── pdf_extractor_tool.py   # Extracción de PDF
│   ├── ml_risk_tool.py        # Evaluación de riesgo ML
│   └── __init__.py
│
├── guardrails/                  # Sistema de guardrails
│   ├── rules.yaml              # Definición de 26 reglas
│   ├── guardrail_engine.py     # Motor de evaluación
│   ├── invoice_guardrail.py    # Validación estructural
│   └── __init__.py
│
├── rag/                         # Retrieval Augmented Generation
│   ├── ingest.py               # Indexación de contratos
│   ├── retriever.py            # Búsqueda semántica
│   ├── embedding_function.py   # Wrapper Gemini para Chroma
│   └── __init__.py
│
├── ml/                          # Machine Learning
│   ├── risk_model.py           # Modelo de riesgo
│   └── __init__.py
│
├── sessions/                    # Gestión de sesiones ADK
│   └── session_manager.py
│
├── evaluation/                  # Evaluación del sistema
│   ├── golden_cases.py         # 20 casos de prueba
│   ├── llm_judge.py           # Gemini como juez
│   ├── metrics.py             # Métricas (accuracy, BERTscore)
│   └── __init__.py
│
├── supplier_portal/            # Portal del Proveedor (UI separada)
│   ├── index.html
│   ├── style.css
│   └── *.js
│
├── a2a/                        # Protocolo Agent-to-Agent
│   └── external_auditor_agent/
│       ├── agent.py
│       └── server.py           # Puerto 8003
│
├── data/                       # DATOS PERSISTENTES
│   ├── payments.db             # SQLite: facturas procesadas (114 registros)
│   ├── chat_sessions.db        # SQLite: sesiones de chat (50 sesiones)
│   ├── inbox.db                # SQLite: cola de facturas pendientes
│   ├── contracts/              # Contratos .txt para RAG
│   │   ├── contrato_proveedor_001.txt
│   │   ├── contrato_proveedor_002.txt
│   │   └── ...
│   └── chroma_db/             # Vector store (auto-generado)
│       ├── *.bin
│       └── *.sqlite
│
├── tests/                      # Tests
│   └── eval/
│       ├── datasets/
│       │   └── invoiceflow-dataset.json
│       └── __init__.py
│
├── docs/                      # Documentación adicional
│   ├── especificacion_sistema_invoiceflow.md
│   ├── documento_guardrails_invoiceflow.md
│   ├── GUIA_RAPIDA.md
│   ├── INSTALACION_WINDOWS.md
│   ├── INSTALACION_LINUX.md
│   ├── INSTALACION_MACOS.md
│   └── SPECS_*.md
│
├── start_servers.py            # Script de inicio (3 servicios)
├── create_invoices.py          # Generador de facturas de prueba
├── create_suppliers_db.py      # Crear DB de proveedores
└── bugs/                        # Registro de bugs corregidos
    ├── bugs_001.md ... bugs_022.md
    └── README.md
```

---

## 8. Instalación Rápida

### Requisitos Previos

- Python 3.12+
- Git (opcional)
- Windows 10/11, Linux, o macOS

### Pasos (3 minutos)

```bash
# 1. Clonar o descargar el proyecto
git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git
cd invoice_approval_system

# 2. Crear entorno virtual
python -m venv .venv

# 3. Activar entorno
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar API Key
cp .env.example .env
# Editar .env y agregar GOOGLE_API_KEY

# 6. Indexar contratos (solo primera vez)
python rag/ingest.py
```

### Scripts Automatizados (Windows)

| Script | Función |
|--------|---------|
| `start_servers.py` | Inicia los 3 servicios automáticamente |
| `INICIAR.bat` | Atajo para iniciar |
| `setup.bat` | Instala y configura todo |
| `smoke_test.bat` | Verifica componentes |

---

## 9. Ejecución del Sistema

### 9.1 Inicio Completo (3 servicios)

```bash
# Ejecutar desde invoice_approval_system/
python start_servers.py
```

O manualmente:

```bash
# Terminal 1 - Supplier Service
python -m app.services.supplier_service.main
# Puerto: 8001

# Terminal 2 - Contract Service
python -m app.services.contract_service.main
# Puerto: 8002

# Terminal 3 - Backend
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

### 9.2 URLs del Sistema

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Back Office** | http://localhost:8000/ | Panel de administración |
| **Supplier Portal** | http://localhost:8000/supplier/ | Portal del proveedor |
| **API Docs (Backend)** | http://localhost:8000/docs | Documentación Swagger |
| **API Docs (Supplier)** | http://localhost:8001/docs | API de proveedores |
| **API Docs (Contract)** | http://localhost:8002/docs | API de contratos |

### 9.3 Verificación de Salud

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8000/agents/health  # Todos los servicios
```

---

## 10. Ejemplos de Uso

### 10.1 Ejemplo A — Factura Aprobada

**Input:**
```json
{
  "invoice_id": "FC-0001-00000001",
  "supplier_id": "SUP001",
  "supplier_name": "TechCorp SA",
  "amount": 50000,
  "currency": "ARS",
  "invoice_date": "2025-06-01"
}
```

**Resultado Esperado:**
```json
{
  "decision": "APPROVED",
  "confirmation_id": "PAY-a3f8b2c1",
  "payment_status": "PENDING_PAYMENT",
  "rejection_reason": null
}
```

### 10.2 Ejemplo B — Supera Límite Contractual

**Input:** `amount: 200000` para SUP001 (límite: $150,000)

**Resultado:** `REJECTED` — "Monto $200,000 excede el límite contractual de $150,000"

### 10.3 Ejemplo C — Proveedor Inactivo

**Input:** `supplier_id: "SUP003"` (status: INACTIVE)

**Resultado:** `REJECTED` — "Proveedor SUP003 está INACTIVE (no activo)"

### 10.4 Ejemplo D — Contrato Modo EXACTO

**Input:** `amount: 50000` para SUP007 (contrato modo EXACTO: $100,000)

**Resultado:** `REJECTED` — "Contrato modo EXACTO: el monto $50,000 debe ser exactamente $100,000"

### 10.5 Asistente GI — Comandos

| Comando | Acción |
|---------|--------|
| "resumen" | Overview del sistema |
| "me podés decir los montos" | Lista montos del inbox + total |
| "mostrame el historial" | Pagos registrados |
| "procesá la factura FC-0001-00000001" | Procesa una específica |
| "cambia el límite de SUP001 a 200000" | Modifica `contracts.contract_limit` |
| "activá SUP003" / "desactivá SUP003" | Cambia `suppliers.status` |
| "eliminá SUP003" + "sí" | Baja lógica con confirmación |

---

## 11. Evaluación y Testing

### 11.1 Golden Cases (20 casos)

```bash
python -m evaluation.metrics
```

**Salida esperada:**
```
GC001 ... PASS (judge=1.00, bert_f1=0.91)
GC002 ... PASS (judge=1.00, bert_f1=0.88)
...
Pass rate: 20/20 (100.0%) | Avg BertScore F1: 0.89
```

### 11.2 Smoke Tests

```bash
# Verificar imports
python test_imports.py

# Verificar DB
python check_db.py

# Probar flujo completo
python test_full_flow.py
```

---

## 12. API Reference

### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/invoices/new` | Procesar nueva factura |
| GET | `/api/invoices/{id}/status` | Consultar estado |
| POST | `/chat` | Chat con router agent |
| GET | `/health` | Health check |
| GET | `/agents/health` | Health de todos los servicios |
| GET | `/suppliers/proxy-list` | Lista proveedores (proxy) |
| POST | `/suppliers/proxy-create` | Crear proveedor (proxy) |
| PUT | `/suppliers/proxy-update/{id}` | Modificar proveedor (proxy) |
| DELETE | `/suppliers/proxy-delete/{id}` | Eliminar proveedor (proxy) |
| GET | `/suppliers/proxy-contracts` | Lista contratos (proxy) |

### Esquema de Factura

```json
{
  "invoice_id": "string (único, ej: FC-0001-00000001)",
  "supplier_id": "string (formato: SUP###)",
  "supplier_name": "string",
  "amount": "number (positivo)",
  "currency": "string (3 letras, ej: ARS)",
  "invoice_date": "string (YYYY-MM-DD)"
}
```

---

## 13. Troubleshooting

### Error: "ModuleNotFoundError: No module named 'agents'"

**Causa:** ADK no encuentra los módulos desde el directorio de ejecución.

**Solución:** `agent.py` ya incluye la corrección con `sys.path.insert(0, PROJECT_ROOT)`.

---

### Error: "ValueError: ClientOptions does not accept an option 'headers'"

**Causa:** Incompatibilidad entre `chromadb` 1.5.x y `google-generativeai` 0.8.6.

**Solución:** Usar el wrapper custom en `rag/embedding_function.py` con `google.genai.Client`.

---

### Error: "Port already in use" (Windows)

```bash
netstat -ano | findstr :8000
taskkill /PID <NUMERO> /F
```

---

### Encoding Issues en Windows

Agregar al inicio de scripts `.bat`:
```batch
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
```

---

## 14. Licencia y Créditos

### Licencia

Este proyecto es **académico** y fue desarrollado con fines educativos para la materia de Sistemas Multiagentes de la Universidad de Palermo (2025).

### Tecnologías Utilizadas

- [Google ADK](https://google.github.io/adk-docs/) — Agent Development Kit
- [Gemini AI](https://ai.google.dev/) — Modelos de lenguaje
- [ChromaDB](https://www.trychroma.com/) — Vector database
- [FastAPI](https://fastapi.tiangolo.com/) — Backend framework
- [scikit-learn](https://scikit-learn.org/) — Machine learning

### Repositorio

🔗 https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque

---

## 📚 Documentación Relacionada

| Archivo | Descripción |
|---------|------------|
| [`INSTALL.md`](INSTALL.md) | Guía de instalación detallada |
| [`CHANGELOG.md`](CHANGELOG.md) | Historial de cambios |
| [`docs/especificacion_sistema_invoiceflow.md`](docs/especificacion_sistema_invoiceflow.md) | Especificación técnica completa |
| [`docs/documento_guardrails_invoiceflow.md`](docs/documento_guardrails_invoiceflow.md) | Sistema de guardrails |
| [`docs/INSTALACION_WINDOWS.md`](docs/INSTALACION_WINDOWS.md) | Guía para Windows |
| [`docs/INSTALACION_LINUX.md`](docs/INSTALACION_LINUX.md) | Guía para Linux |
| [`docs/INSTALACION_MACOS.md`](docs/INSTALACION_MACOS.md) | Guía para macOS |
| [`bugs/README.md`](bugs/README.md) | Registro de bugs corregidos |

---

*InvoiceFlow v2.3.0 — Universidad de Palermo 2026*
