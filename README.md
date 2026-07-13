# InvoiceFlow — Sistema Multiagente de Aprobación de Facturas

> **Trabajo Práctico — Sistemas Multiagentes** | Universidad de Palermo
>
> **Estado**: ✅ Operativo | **Versión**: 2.2.0 | **Última actualización**: 2026-07-15
>
> 🔗 **Repositorio**: [GitHub](https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque)

---

## 📑 Tabla de Contenidos

1. [Descripción del Proyecto](#1-descripción-del-proyecto)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Stack Tecnológico](#3-stack-tecnológico)
4. [Agentes Implementados](#4-agentes-implementados)
5. [Flujo de Negocio](#5-flujo-de-negocio)
6. [Estructura de Carpetas](#6-estructura-de-carpetas)
7. [Instalación Rápida](#7-instalación-rápida)
8. [Ejecución del Sistema](#8-ejecución-del-sistema)
9. [Ejemplos de Uso](#9-ejemplos-de-uso)
10. [Evaluación y Testing](#10-evaluación-y-testing)
11. [Troubleshooting](#11-troubleshooting)
12. [API Reference](#12-api-reference)
13. [Licencia y Créditos](#13-licencia-y-créditos)

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
│                           CAPA 4: INTERFAZ DE USUARIO                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌─────────────────────┐                   │
│  │   Back Office       │         │  Supplier Portal    │                   │
│  │   (Administración)  │         │  (Proveedores)      │                   │
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
│  │                                                                  │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │                    GUARDRAIL ENGINE                         │  │  │
│  │  │  (26 reglas: VR + BR + SR + CR)                          │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
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
│  ┌──────────────┐  ┌──────────────┐                                        │
│  │   SQLite     │  │   SQLite     │                                        │
│  │ (suppliers)  │  │  (chat)      │                                        │
│  └──────────────┘  └──────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Flujo de Datos entre Componentes

```
Solicitud HTTP
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ FASTAPI Backend (Puerto 8000)                                           │
│  ├── /invoice/new → InvoiceOrchestrator                                 │
│  ├── /invoice/status → InvoiceStatusTool                                │
│  └── /chat → RouterAgent                                               │
└─────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ INVOICE ORCHESTRATOR                                                     │
│  1. Apply Guardrail (validación estructural)                            │
│  2. Transfer → ValidatorAgent (supplier_id)                            │
│  3. Transfer → ContractAgent (RAG + monto)                             │
│  4. Transfer → PaymentAgent (persistir decisión)                       │
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
| **Framework de Agentes** | Google ADK | 2.3.0 | Requerido por la consigna. Abstracción de alto nivel para LlmAgent, Runner, SessionService |
| **Modelo LLM** | Gemini 2.0 Flash | latest | Balance ideal latencia/costo/razonamiento |
| **Embeddings** | Gemini Embedding | 001 | Modelo GA estable para ChromaDB |
| **Vector Store (RAG)** | ChromaDB | 1.5.9 | Persistencia local, SQLite-backed, sin servidor |
| **Base de Datos** | SQLite | 3.x | Cero configuración, archivo local `data/payments.db` |
| **Backend API** | FastAPI | 0.100+ | Alto rendimiento, documentación automática con OpenAPI |
| **Lenguaje** | Python | 3.12 | Requerido por consigna (3.11+) |
| **Métricas NLP** | BertScore + XLM-RoBERTa | latest | Evaluación multilingüe de justificaciones |
| **ML** | scikit-learn | latest | Modelo de riesgo predictivo |
| **UI** | HTML/CSS/JS | — | Frontend ligero sin framework |

---

## 3.5 Asistente IA "GI" 🤖

El BackOffice incluye un **chat conversacional** con el Asistente Inteligente GI que entiende lenguaje natural y puede **ejecutar acciones** sobre el sistema.

### Comandos de consulta

| Comando | Acción |
|---------|--------|
| "me podras decir los montos" | Lista montos del inbox + total |
| "mostrame el historial" | Pagos registrados |
| "cuánto suman las facturas" | Totales por estado |
| "resumen" | Overview del sistema |
| "qué facturas hay en el inbox" | Lista pendientes |
| "ayuda" | Lista de comandos |

### Comandos de acción (write)

| Comando | Acción |
|---------|--------|
| "procesá todo el inbox" | Procesa todas las pendientes |
| "procesá la factura FC-0001-00000001" | Procesa una específica |
| "cambia el límite de SUP001 a 200000" | Modifica `contracts.contract_limit` |
| "cambia el modo de SUP002 a exacto" | Modifica `contracts.mode` (EXACTO/NO_SUPERAR) |
| "activá SUP003" / "desactivá SUP003" | Cambia `suppliers.status` |
| "cambiar email de SUP001 a x@y.com" | Modifica `suppliers.email` |
| "eliminá SUP003" + "sí" | Baja lógica con confirmación |
| "ahora desactiva ese mismo" | Memoria: repite última acción |

### Memoria Conversacional

Las sesiones se persisten en `data/chat_sessions.db` (SQLite):

```sql
sessions(id, title, created_at, last_active_at)
messages(id, session_id, role, content, intent, created_at)
```

El sistema recuerda las últimas 5 interacciones para resolver referencias como "ese mismo", "ahora hacelo", "y del historial?".

### Endpoints REST

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/chat` | Enviar mensaje (body: `{message, session_id?}`) |
| GET | `/chat/sessions` | Listar sesiones |
| POST | `/chat/sessions` | Crear nueva sesión |
| GET | `/chat/sessions/{id}` | Obtener mensajes |
| DELETE | `/chat/sessions/{id}` | Eliminar sesión |

## 3.6 ABM de Proveedores 🏢

Backend completo para gestión de proveedores y sus contratos. Ver [SPECS_012](./docs/SPECS_012_PROVEEDORES.md).

### Modos de validación de contrato

- **NO_SUPERAR** (default): la factura puede ser menor o igual al límite
- **EXACTO**: la factura debe ser exactamente igual al límite

### Endpoints

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/suppliers` | Alta (con contrato opcional) |
| PUT | `/suppliers/{id}` | Modificar |
| DELETE | `/suppliers/{id}` | Baja lógica |
| POST | `/suppliers/{id}/contract` | Asignar contrato |
| GET | `/suppliers/{id}/check?amount=N` | Validar factura |

## 4. Agentes Implementados

### 4.1 Agentes Principales (ADK)

| Agente | Tipo | Responsabilidad | Output Key |
|--------|------|----------------|------------|
| **InvoiceOrchestrator** | LlmAgent (root) | Coordina flujo, aplica guardrail final | `final_decision` |
| **RouterAgent** | LlmAgent (sub) | Clasifica intención del chat | `intent` |
| **ValidatorAgent** | LlmAgent (sub) | Valida proveedor (MCP mock) | `validator_result` |
| **ContractAgent** | LlmAgent (sub) | Controla monto vs contrato (RAG) | `contract_result` |
| **PaymentAgent** | LlmAgent (sub) | Persiste en SQLite | `payment_result` |
| **InvoiceManagerAgent** | LlmAgent (sub) | Gestiona archivos y extracción | `invoice_data` |

### 4.2 Agente Externo (A2A)

| Agente | Puerto | Responsabilidad |
|--------|--------|-----------------|
| **ExternalAuditorAgent** | 8003 | Auditoría de facturas escaladas |

### 4.3 State Compartido

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
    "payment_result": dict,      # {status, confirmation_id, payment_status}
    
    # Decisión final
    "final_decision": dict       # {decision, rejection_reason, ...}
}
```

---

## 5. Flujo de Negocio

### 5.1 Flujo A — Alta de Factura

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
│  │ SR (5 reglas) — Seguridad                               │    │
│  │ CR (3 reglas) — Continuidad                            │    │
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
       │  VALIDATOR   │ ←── MCP mock (suppliers dict)
       │   AGENT      │
       └──────┬───────┘
              │
              ├── INVALID ──→ REJECT (proveedor inactivo/no existe)
              │
              └── VALID ──→ siguiente paso
                     │
                     ▼
              ┌──────────────┐
              │  CONTRACT    │ ←── ChromaDB RAG
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
                     │   PAYMENT    │ ←── SQLite
                     │   AGENT      │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   SQLite     │
                     │   payments.db│
                     └──────────────┘
                            │
                            ▼
                     ┌─────────────────┐
                     │  APROBADO ✓    │
                     │  (PENDING)      │
                     └─────────────────┘
```

### 5.2 Flujo B — Consulta de Estado

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

## 6. Estructura de Carpetas

```
invoice_approval_system/
│
├── agent.py                     # Entry point ADK
├── .env.example                 # Plantilla variables de entorno
├── requirements.txt             # Dependencias Python
├── README.md                    # Este archivo
├── CHANGELOG.md                 # Historial de versiones
├── INSTALL.md                   # Guía de instalación
│
├── agents/                      # Agentes ADK
│   ├── orchestrator.py          # Agente principal
│   ├── router_agent.py          # Clasificador de intenciones
│   ├── validator_agent.py       # Validador de proveedores
│   ├── contract_agent.py        # Control contractual (RAG)
│   ├── payment_agent.py         # Registro de pagos
│   ├── invoice_manager_agent.py # Gestor de archivos
│   └── __init__.py
│
├── tools/                       # Herramientas (FunctionTool)
│   ├── supplier_mcp_tool.py     # Mock MCP de proveedores
│   ├── rag_tool.py             # Wrapper ChromaDB
│   ├── payment_db_tool.py      # SQLite operations
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
├── platform/                    # Backend y Frontend
│   ├── backend/
│   │   ├── main.py             # Servidor FastAPI
│   │   ├── settings.py         # Configuración
│   │   └── routers/            # Endpoints API
│   ├── frontend/               # Back Office
│   │   ├── index.html
│   │   ├── app.js
│   │   └── style.css
│   └── services/               # Microservicios
│       ├── supplier_service/
│       └── contract_service/
│
├── supplier_portal/            # Portal del Proveedor
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── a2a/                        # Protocolo Agent-to-Agent
│   └── external_auditor_agent/ # Agente auditor externo
│
├── data/                       # Datos persistentes
│   ├── payments.db            # SQLite (auto-generado)
│   ├── chroma_db/            # Vector store (auto-generado)
│   ├── contracts/            # Contratos .txt para RAG
│   └── new_invoices/         # Facturas pendientes
│
├── tests/                      # Tests
│   └── eval/                  # Evaluación
│       ├── datasets/
│       │   └── invoiceflow-dataset.json
│       └── eval_config.yaml
│
└── docs/                      # Documentación adicional
    ├── especificacion_sistema_invoiceflow.md
    ├── documento_guardrails_invoiceflow.md
    ├── INSTALACION_WINDOWS.md
    ├── INSTALACION_LINUX.md
    └── INSTALACION_MACOS.md
```

---

## 7. Instalación Rápida

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

### Scripts Automatizados

| Script | Plataforma | Función |
|--------|-----------|---------|
| `INICIAR.bat` | Windows | Inicia los 3 servicios automáticamente |
| `setup.bat` | Windows | Instala y configura todo |
| `smoke_test.bat` | Windows | Verifica componentes |

---

## 8. Ejecución del Sistema

### 8.1 Inicio Completo (3 terminales)

```bash
# Terminal 1 - Supplier Service
python -m platform.services.supplier_service.main
# Puerto: 8001

# Terminal 2 - Contract Service
python -m platform.services.contract_service.main
# Puerto: 8002

# Terminal 3 - Backend
cd platform/backend
python main.py
# Puerto: 8000
```

### 8.2 URLs del Sistema

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Back Office** | http://localhost:8000/ | Panel de administración |
| **Supplier Portal** | http://localhost:8000/supplier/ | Portal del proveedor |
| **API Docs (Backend)** | http://localhost:8000/docs | Documentación Swagger |
| **API Docs (Supplier)** | http://localhost:8001/docs | API de proveedores |
| **API Docs (Contract)** | http://localhost:8002/docs | API de contratos |

### 8.3 Verificación de Salud

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

---

## 9. Ejemplos de Uso

### 9.1 Ejemplo A — Factura Aprobada

**Input:**
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

**Resultado Esperado:**
```json
{
  "decision": "APPROVED",
  "confirmation_id": "PAY-a3f8b2c1",
  "payment_status": "PENDING_PAYMENT",
  "rejection_reason": null
}
```

### 9.2 Ejemplo B — Supera Límite Contractual

**Input:**
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

**Resultado:** `REJECTED` — "Monto $200,000 excede el límite contractual de $150,000"

### 9.3 Ejemplo C — Proveedor Inactivo

**Input:**
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

**Resultado:** `REJECTED` — "Proveedor inactivo"

### 9.4 Ejemplo D — Escalado por Monto

**Input:**
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

**Resultado:** `ESCALATED` → `PENDING_HUMAN_REVIEW`

### 9.5 Ejemplo E — Datos Incompletos

**Input:**
```json
{
  "invoice_id": "INV-006",
  "supplier_id": "SUP002",
  "supplier_name": "Papelería Norte SRL",
  "amount": 15000,
  "currency": "ARS"
}
```

**Resultado:** `REJECTED` — "Datos incompletos: invoice_date"

---

## 10. Evaluación y Testing

### 10.1 Golden Cases (20 casos)

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

### 10.2 Smoke Tests (componentes individuales)

```bash
python -m guardrails.invoice_guardrail
python -m tools.supplier_mcp_tool
python -m tools.rag_tool
python -m tools.payment_db_tool
python -m agents.validator_agent
python -m agents.contract_agent
python -m agents.payment_agent
python -m agents.orchestrator
```

---

## 11. Troubleshooting

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

## 12. API Reference

### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/invoices/new` | Procesar nueva factura |
| GET | `/api/invoices/{id}/status` | Consultar estado |
| POST | `/api/chat` | Chat con router agent |
| GET | `/health` | Health check |
| GET | `/api/suppliers/{id}` | Datos de proveedor |

### Esquema de Factura

```json
{
  "invoice_id": "string (único)",
  "supplier_id": "string (formato: SUP###)",
  "supplier_name": "string",
  "amount": "number (positivo)",
  "currency": "string (3 letras, ej: ARS)",
  "invoice_date": "string (YYYY-MM-DD)"
}
```

---

## 13. Licencia y Créditos

### Licencia

Este proyecto es **académico** y fue desarrollado con fines educativos para la materia de Sistemas Multiagentes de la Universidad de Palermo (2025).

### Autores

- Equipo de desarrollo InvoiceFlow

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

---

*InvoiceFlow v2.2.0 — Universidad de Palermo 2026*

## 📦 Repositorio Git
- El código fuente está disponible en: https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque

### GITHUB
- or create a new repository on the command line echo "# multiagentes_clinicaparque" >> README.md

- - git init
- - git add README.md
- - git commit -m "first commit"
- - git branch -M main
- - git remote add origin https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git
- - git push -u origin main

- or push an existing repository from the command line

- - git remote add origin https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git
- - git branch -M main
- - git push -u origin main

#### credenciales git

usr: giselle.fernandezv@gmail.com pwd: Calitamendoza1603
Probando