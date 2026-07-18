# InvoiceFlow — Sistema Multiagente de Aprobación de Facturas

> **Trabajo Práctico — Sistemas Multiagentes** | Universidad de Palermo
>
> **Estado**: ✅ Operativo | **Versión**: 3.1.0 | **Última actualización**: 2026-07-18
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

**InvoiceFlow** es un sistema multiagente que automatiza el proceso de aprobación de facturas de proveedores mediante inteligencia artificial, desarrollado como trabajo práctico de la materia Sistemas Multiagentes de la Universidad de Palermo.

### Objetivos Principales

- ✅ Validar proveedores activos contra registros internos
- ✅ Verificar montos contra límites contractuales (vía RAG)
- ✅ Aplicar reglas de negocio (guardrails)
- ✅ Registrar todas las decisiones para auditoría
- ✅ Proporcionar interfaces para proveedores y administradores
- ✅ Protocolo A2A para auditoría externa
- ✅ Evaluación automática con LLM as a Judge

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
| **MCP Toolbox** | Herramientas predefinidas para validación de proveedores |
| **Sesiones Persistentes** | Estado compartido entre agentes con DatabaseSessionService |

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
│                           CAPA 3: ORQUESTACIÓN ADK                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    INVOICE ORCHESTRATOR (ADK)                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │   Router    │  │  Validator  │  │  Contract   │  │   Payment   │  │  │
│  │  │   Agent     │  │   Agent     │  │   Agent     │  │   Agent     │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  │  ┌─────────────┐  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Invoice   │  │                    GUARDRAIL ENGINE           │  │  │
│  │  │  Manager   │  │  (26 reglas: VR + BR + SR + CR)            │  │  │
│  │  └─────────────┘  └─────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                             │                                              │
├─────────────────────────────┼───────────────────────────────────────────────┤
│                           CAPA 2: HERRAMIENTAS (Tools)                      │
├─────────────────────────────┼───────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Supplier    │  │    RAG       │  │   Payment    │  │   Invoice    │    │
│  │  MCP Tool    │  │   Tool       │  │   DB Tool    │  │   Status     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Folder      │  │    PDF       │  │    ML        │  │   A2A        │    │
│  │  Manager     │  │  Extractor   │  │   Risk       │  │   Audit      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│                           CAPA 1: PERSISTENCIA                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   SQLite     │  │  ChromaDB    │  │    Files     │  │    A2A       │    │
│  │ (payments)   │  │  (RAG)       │  │  (PDFs)      │  │  Server      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │   SQLite     │  │   SQLite     │  │   SQLite     │                     │
│  │ (suppliers)  │  │  (chat)      │  │  (inbox)     │                     │
│  │ app/data/    │  │  data/       │  │  app/data/   │                     │
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
│  │  Proxy ABM (evita CORS en browser)                               │   │
│  │  File Watcher (auto-proceso del inbox)                           │   │
│  │  Health Check Agregrado                                          │   │
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
│                                                                         │
│         ┌───────────────────────────────────────┐                        │
│         │            PUERTO 5000                │                        │
│         │      MCP Toolbox Server               │                        │
│         │  (tools predefinidas en YAML)         │                        │
│         └───────────────────────────────────────┘                        │
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
│ ORCHESTRATOR (ADK Pipeline)                                             │
│  1. Guardrail (validación estructural determinística)                   │
│  2. Supplier Service (validación proveedor) → HTTP GET :8001           │
│  3. Contract Service (RAG + límite) → HTTP GET :8002                   │
│  4. External Auditor (A2A si monto > $500.000) → HTTP POST :8003      │
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
| **Framework de Agentes** | Google ADK | >=1.0.0 | Abstracción de alto nivel para LlmAgent, Runner, SessionService |
| **Modelo LLM** | Gemini 2.0 Flash | latest | Balance ideal latencia/costo/razonamiento |
| **Embeddings** | Gemini Embedding | 001 | Modelo GA estable para ChromaDB |
| **Vector Store (RAG)** | ChromaDB | >=0.5.0 | Persistencia local, SQLite-backed, sin servidor |
| **Base de Datos** | SQLite | 3.x | Cero configuración, múltiples archivos |
| **Backend API** | FastAPI | 0.100+ | Alto rendimiento, documentación automática con OpenAPI |
| **Lenguaje** | Python | 3.12 | Requerido por google-adk |
| **Métricas NLP** | BertScore + XLM-RoBERTa | latest | Evaluación multilingüe de justificaciones |
| **ML** | scikit-learn | latest | Modelo de riesgo predictivo |
| **UI** | HTML/CSS/JS (Vanilla) | — | Frontend ligero sin framework |
| **MCP** | Model Context Protocol | >=1.0.0 | Herramientas predefinidas configurables |
| **ORM** | Pydantic | latest | Validación de schemas |

---

## 4. Bases de Datos

El sistema utiliza **5 archivos SQLite** para persistencia:

### 4.1 `data/payments.db` — Pagos Procesados

| Tabla | Campos | Descripción |
|-------|--------|-------------|
| `payments` | id, invoice_id, supplier_id, amount, decision, rejection_reason, payment_status, confirmation_id, registered_at, source_file | Registro de todas las facturas procesadas |

### 4.2 `app/data/suppliers.db` — Proveedores y Contratos

| Tabla | Campos | Descripción |
|-------|--------|-------------|
| `suppliers` | supplier_id, name, cuit, status, category, email, phone, registered_at | Catálogo de proveedores |
| `contracts` | id, supplier_id, contract_limit, mode, start_date, end_date, file_path, uploaded_at | Contratos vigentes |

### 4.3 `data/chat_sessions.db` — Sesiones de Chat (Asistente GI)

| Tabla | Campos | Descripción |
|-------|--------|-------------|
| `sessions` | id, title, created_at, last_active_at | Sesiones de conversación |
| `messages` | id, session_id, role, content, intent, created_at | Mensajes con roles (user/assistant/system) |

### 4.4 `app/data/inbox.db` — Cola de Facturas Pendientes

| Tabla | Campos | Descripción |
|-------|--------|-------------|
| `inbox_items` | id, filename, size, status, invoice_id, supplier_id, amount, invoice_date, decision, rejection_reason, confirmation_id, uploaded_at, processed_at | Facturas en espera de procesamiento |

### 4.5 `app/data/adk_sessions.db` — Sesiones ADK

| Tabla | Campos | Descripción |
|-------|--------|-------------|
| `sessions` | id, user_id, state, created_at, updated_at | Sesiones de agentes ADK con state persistente |

### 4.6 `app/data/chroma_db/` — Vector Store (RAG)

| Contenido | Descripción |
|-----------|-------------|
| `*.bin`, `*.sqlite` | Índices vectoriales de contratos |
| Colección: `contracts` | Embeddings de fragmentos de contratos |

---

## 5. Agentes Implementados

### 5.1 Agentes Principales (Google ADK)

| Agente | Tipo | Responsabilidad | Output Key |
|--------|------|----------------|------------|
| **InvoiceOrchestrator** | LlmAgent (root) | Coordina flujo, aplica guardrail final | `final_decision` |
| **RouterAgent** | LlmAgent (sub) | Clasifica intención del chat | `intent` |
| **ValidatorAgent** | LlmAgent (sub) | Valida proveedor (MCP) | `validator_result` |
| **ContractAgent** | LlmAgent (sub) | Controla monto vs contrato (RAG) | `contract_result` |
| **PaymentAgent** | LlmAgent (sub) | Persiste en SQLite | `payment_result` |
| **InvoiceManagerAgent** | LlmAgent (sub) | Gestiona archivos y extracción | `invoice_data` |

### 5.2 Microservicios

| Servicio | Puerto | Responsabilidad | DB |
|---------|--------|----------------|-----|
| **Supplier Service** | 8001 | ABM de proveedores y contratos | `app/data/suppliers.db` |
| **Contract Service** | 8002 | RAG con ChromaDB | `app/data/chroma_db/` |
| **External Auditor** | 8003 | Auditoría A2A de facturas escaladas | — |
| **MCP Toolbox** | 5000 | Herramientas predefinidas (YAML) | `mcp_config/tools.yaml` |

### 5.3 State Compartido (ADK SessionService)

```python
session.state = {
    # Datos de entrada
    "invoice_id": str,
    "supplier_id": str,
    "supplier_name": str,
    "amount": float,
    "currency": str,
    "invoice_date": str,
    
    # Resultados de agentes
    "guardrail_action": str,      # APPROVE | REJECT | ESCALATE
    "guardrail_reason": str,
    "validation_status": str,
    "contract_status": str,
    "contract_limit": float,
    "payment_status": str,
    "confirmation_id": str,
    
    # Decisión final
    "final_decision": dict
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
       │   AGENT      │ ←── MCP Toolbox (HTTP :5000)
       └──────┬───────┘
              │
              ├── INVALID ──→ REJECT (proveedor inactivo/no existe)
              │
              └── VALID ──→ siguiente paso
                     │
                     ▼
              ┌──────────────┐
              │  CONTRACT    │ ←── Contract Service (HTTP :8002)
              │   AGENT      │ ←── ChromaDB (RAG)
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
├── agent.py                     # Entry point ADK
├── .env.example                 # Plantilla variables de entorno
├── .env                         # Variables reales (NO commitear)
├── requirements.txt             # Dependencias Python
├── README.md                    # Este archivo
├── CHANGELOG.md                 # Historial de versiones
├── INSTALL.md                   # Guía de instalación
│
├── agents/                      # Agentes ADK
│   ├── orchestrator.py         # Agente principal (root)
│   ├── router_agent.py         # Clasificador de intenciones (chat)
│   ├── validator_agent.py      # Validador de proveedores
│   ├── contract_agent.py        # Control contractual (RAG)
│   ├── payment_agent.py        # Registro de pagos
│   ├── invoice_manager_agent.py # Gestor de archivos
│   └── __init__.py
│
├── app/                        # Aplicación principal
│   ├── backend/
│   │   ├── main.py             # FastAPI Backend (puerto 8000)
│   │   ├── settings.py         # Configuración
│   │   ├── orchestrator.py    # Pipeline de procesamiento
│   │   ├── watcher.py         # File watcher del inbox
│   │   ├── inbox_router.py     # Endpoints de inbox
│   │   ├── chat_router.py     # Endpoints de chat (GI)
│   │   ├── new_invoices_router.py
│   │   └── supplier_portal_router.py
│   ├── frontend/               # Back Office (UI)
│   │   ├── index.html
│   │   ├── app.js
│   │   ├── style.css
│   │   └── observability.*
│   ├── services/
│   │   ├── supplier_service/   # Microservicio (puerto 8001)
│   │   │   └── main.py
│   │   ├── contract_service/   # Microservicio (puerto 8002)
│   │   │   └── main.py
│   │   └── toolbox_server/     # MCP Toolbox (puerto 5000)
│   │       └── main.py
│   └── data/
│       ├── suppliers.db         # SQLite: proveedores + contratos
│       ├── inbox.db             # SQLite: cola de facturas
│       ├── adk_sessions.db     # SQLite: sesiones ADK
│       ├── contracts/          # Archivos .txt de contratos
│       └── chroma_db/          # Vector store (RAG)
│
├── tools/                       # Herramientas (FunctionTool)
│   ├── supplier_mcp_tool.py    # Mock MCP de proveedores
│   ├── rag_tool.py             # Wrapper ChromaDB
│   ├── payment_db_tool.py     # SQLite operations
│   ├── invoice_status_tool.py  # Consulta de estado
│   ├── folder_manager_tool.py  # Gestión de archivos
│   ├── pdf_extractor_tool.py   # Extracción de PDF
│   ├── ml_risk_tool.py         # Evaluación de riesgo ML
│   ├── a2a_audit_tool.py      # Tool A2A para External Auditor
│   └── __init__.py
│
├── guardrails/                  # Sistema de guardrails
│   ├── rules.yaml              # Definición de 26 reglas
│   ├── guardrail_engine.py     # Motor de evaluación
│   ├── invoice_guardrail.py    # Validación estructural
│   └── __init__.py
│
├── rag/                         # Retrieval Augmented Generation
│   ├── ingest.py                # Indexación de contratos
│   ├── retriever.py             # Búsqueda semántica
│   ├── embedding_function.py    # Wrapper Gemini para Chroma
│   └── __init__.py
│
├── ml/                          # Machine Learning
│   ├── risk_model.py            # Modelo de riesgo
│   └── __init__.py
│
├── sessions/                    # Gestión de sesiones ADK
│   ├── session_manager.py       # DatabaseSessionService wrapper
│   └── __init__.py
│
├── evaluation/                  # Evaluación del sistema
│   ├── golden_cases.py          # 6 casos de prueba
│   ├── llm_judge.py            # Gemini como juez
│   ├── metrics.py              # Métricas (accuracy, BERTscore)
│   └── __init__.py
│
├── mcp_config/                  # Configuración MCP
│   ├── mcp_servers.json        # Servers MCP (toolbox)
│   └── tools.yaml               # Herramientas predefinidas
│
├── supplier_portal/            # Portal del Proveedor (UI separada)
│   ├── index.html
│   └── style.css
│
├── a2a/                        # Protocolo Agent-to-Agent
│   └── external_auditor_agent/
│       ├── agent.py             # Agente auditor externo
│       └── server.py           # Servidor A2A
│
├── data/                       # DATOS PERSISTENTES
│   ├── payments.db             # SQLite: facturas procesadas
│   ├── chat_sessions.db        # SQLite: sesiones de chat
│   ├── contracts/              # Contratos .txt para RAG
│   │   ├── contrato_proveedor_001.txt
│   │   └── ...
│   ├── new invoices/           # Facturas nuevas de prueba
│   └── chroma_db/              # Vector store (auto-generado)
│
├── docs/                       # Documentación adicional
│   ├── SPECS_*.md              # Especificaciones técnicas
│   ├── INSTALACION_WINDOWS.md
│   ├── INSTALACION_LINUX.md
│   ├── INSTALACION_MACOS.md
│   └── GUIA_RAPIDA.md
│
├── tests/                      # Tests
│   └── eval/
│       ├── datasets/
│       │   └── invoiceflow-dataset.json
│       └── __init__.py
│
├── start_servers.py            # Script de inicio (todos los servicios)
├── create_invoices.py          # Generador de facturas de prueba
├── create_suppliers_db.py      # Crear DB de proveedores
└── bugs/                       # Registro de bugs corregidos
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

### Scripts de Inicio (Windows)

| Script | Función |
|--------|---------|
| `INICIAR_SISTEMA.bat` | Inicia todos los servicios con menú interactivo |
| `start_all.py` | Script Python para gestionar servicios |
| `start_daemon.py` | Daemon que supervisa y reinicia servicios automáticamente |
| `setup.bat` | Instala y configura todo |
| `smoke_test.bat` | Verifica componentes |

---

## 9. Ejecución del Sistema

### 9.1 Verificar que los puertos estén libres

```bash
# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :8001
netstat -ano | findstr :8002
netstat -ano | findstr :8003

# Si hay procesos usando los puertos, detenerlos:
taskkill /PID <NUMERO_PID> /F
```

### 9.2 Inicio Automático (RECOMENDADO)

**Opción 1: Script Python**
```bash
# Ver estado actual
python start_all.py status

# Iniciar todos los servicios
python start_all.py start

# Detener todos los servicios
python start_all.py stop

# Reiniciar todos
python start_all.py restart
```

**Opción 2: Script Windows (doble clic)**
```bash
INICIAR_SISTEMA.bat
```

**Opción 3: Daemon de supervisión (automático)**
```bash
# Mantiene servicios corriendo y reinicia si se caen
python start_daemon.py

# Ver estado
python start_daemon.py --status

# Verificar una vez
python start_daemon.py --once

# Intervalo personalizado (10 segundos)
python start_daemon.py --interval 10
```

### 9.3 Servicios Incluidos

| Servicio | Puerto | Requerido | Descripción |
|----------|--------|-----------|-------------|
| Backend FastAPI | 8000 | ✅ | API principal con UI |
| Supplier Service | 8001 | ✅ | ABM de proveedores |
| Contract Service | 8002 | ✅ | RAG con ChromaDB |
| MCP Toolbox | 5000 | ❌ | Herramientas predefinidas |
| External Auditor | 8003 | ❌ | Auditoría A2A |

### 9.4 Inicio Manual (5 terminales)

```bash
# Terminal 1 - MCP Toolbox (Puerto 5000)
python -m uvicorn app.services.toolbox_server.main:app --host 127.0.0.1 --port 5000

# Terminal 2 - Supplier Service (Puerto 8001)
python -m uvicorn app.services.supplier_service.main:app --host 127.0.0.1 --port 8001

# Terminal 3 - Contract Service (Puerto 8002)
python -m uvicorn app.services.contract_service.main:app --host 127.0.0.1 --port 8002

# Terminal 4 - External Auditor A2A (Puerto 8003)
python -m uvicorn a2a.external_auditor_agent.server:app --host 127.0.0.1 --port 8003

# Terminal 5 - Backend (Puerto 8000)
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 9.4 URLs del Sistema

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Back Office** | http://localhost:8000/ | Panel de administración con dashboard, inbox, historial, chat IA |
| **Supplier Portal** | http://localhost:8000/supplier/ | Portal del proveedor para consultar estado de facturas |
| **Swagger API** | http://localhost:8000/docs | Documentación interactiva de la API |
| **Health Check** | http://localhost:8000/health | Estado del sistema |
| **Agentes Health** | http://localhost:8000/agents/health | Estado de todos los agentes |
| **Observabilidad** | http://localhost:8000/ | Pestaña de observabilidad en BackOffice |
| **MCP Toolbox** | http://localhost:5000/ | Herramientas predefinidas |
| **External Auditor** | http://localhost:8003/ | Auditoría A2A |

### 9.5 Verificación Post-Inicio

```bash
# 1. Health check del backend
curl http://localhost:8000/health

# 2. Health check de microservicios
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:5000/health

# 3. Verificar agentes
curl http://localhost:8000/agents/health

# 4. Verificar logs
type data\logs\invoiceflow.log
```

### 9.6 Logging

Los logs se guardan automáticamente en:
```
data/logs/invoiceflow.log
```

Con rotación automática (10MB por archivo, 5 backups). Para ver logs en tiempo real:
```bash
# Windows
type data\logs\invoiceflow.log

# Linux/macOS
cat data/logs/invoiceflow.log
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

### 10.4 Ejemplo D — Factura > $500.000 (Escalada)

**Input:** `amount: 600000`

**Resultado:** `ESCALATED` — Requiere auditoría externa via A2A

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
| "listar facturas" | Lista todas las facturas procesadas |
| "cuantas facturas aprobadas tengo" | Cuenta facturas por estado |

---

## 11. Evaluación y Testing

### 11.1 Golden Cases (6 casos)

```bash
python -m evaluation.metrics
```

**Salida esperada:**
```
GC001 ... PASS (judge=1.00, bert_f1=0.91)
GC002 ... PASS (judge=1.00, bert_f1=0.88)
GC003 ... PASS (judge=1.00, bert_f1=0.90)
GC004 ... PASS (judge=1.00, bert_f1=0.87)
GC005 ... PASS (judge=1.00, bert_f1=0.89)
GC006 ... PASS (judge=1.00, bert_f1=0.85)
Pass rate: 6/6 (100.0%) | Avg BertScore F1: 0.88
```

### 11.2 LLM as a Judge

El sistema usa **Gemini como juez** para evaluar semanticamente las respuestas:

- **Criterio 1**: Decisión final (peso 60%)
- **Criterio 2**: Justificación coherente (peso 25%)
- **Criterio 3**: Campos requeridos presentes (peso 15%)

### 11.3 Smoke Tests

```bash
# Verificar imports
python -c "from agents.orchestrator import create_orchestrator; print('OK')"

# Verificar DB
python -c "import sqlite3; c=sqlite3.connect('data/payments.db'); print(c.execute('SELECT COUNT(*) FROM payments').fetchone()[0], 'registros')"

# Verificar RAG
python -c "import chromadb; c=chromadb.PersistentClient('app/data/chroma_db'); print('ChromaDB OK:', len(c.list_collections()), 'collections')"
```

---

## 12. API Reference

### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/invoice/new` | Procesar nueva factura |
| GET | `/invoice/status/{id}` | Consultar estado |
| POST | `/chat` | Chat con asistente GI |
| GET | `/chat/sessions` | Listar sesiones de chat |
| GET | `/health` | Health check |
| GET | `/agents/health` | Health de todos los servicios |
| GET | `/suppliers/proxy-list` | Lista proveedores (proxy) |
| POST | `/suppliers/proxy-create` | Crear proveedor (proxy) |
| PUT | `/suppliers/proxy-update/{id}` | Modificar proveedor (proxy) |
| DELETE | `/suppliers/proxy-delete/{id}` | Eliminar proveedor (proxy) |
| GET | `/suppliers/proxy-contracts` | Lista contratos (proxy) |
| GET | `/inbox` | Listar facturas pendientes |
| POST | `/inbox/{filename}/process` | Procesar factura específica |

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

**Solución:** Verificar que `agent.py` incluye `sys.path.insert(0, PROJECT_ROOT)`.

### Error: "ValueError: ClientOptions does not accept an option 'headers'"

**Causa:** Incompatibilidad entre `chromadb` y `google-generativeai`.

**Solución:** Usar el wrapper custom en `rag/embedding_function.py`.

### Error: "Port already in use" (Windows)

```bash
netstat -ano | findstr :8000
taskkill /PID <NUMERO> /F
```

### Encoding Issues en Windows

Agregar al inicio de scripts `.bat`:
```batch
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
```

---

## 14. Licencia y Créditos

### Licencia

Este proyecto es **académico** y fue desarrollado con fines educativos para la materia de Sistemas Multiagentes de la Universidad de Palermo (2025-2026).

### Tecnologías Utilizadas

- [Google ADK](https://google.github.io/adk-docs/) — Agent Development Kit
- [Gemini AI](https://ai.google.dev/) — Modelos de lenguaje
- [ChromaDB](https://www.trychroma.com/) — Vector database
- [FastAPI](https://fastapi.tiangolo.com/) — Backend framework
- [scikit-learn](https://scikit-learn.org/) — Machine learning
- [Model Context Protocol](https://modelcontextprotocol.io/) — MCP

### Repositorio

🔗 https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque

---

## 📚 Documentación Relacionada

| Archivo | Descripción |
|---------|-------------|
| [`INSTALL.md`](INSTALL.md) | Guía de instalación detallada |
| [`CHANGELOG.md`](CHANGELOG.md) | Historial de cambios |
| [`docs/SPECS_*.md`](docs/) | Especificaciones técnicas completas |
| [`docs/documento_guardrails_invoiceflow.md`](docs/) | Sistema de guardrails |
| [`bugs/README.md`](bugs/) | Registro de bugs corregidos |

---

*InvoiceFlow v3.0.0 — Universidad de Palermo 2026*
