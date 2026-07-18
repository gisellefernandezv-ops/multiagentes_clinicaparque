# Changelog — InvoiceFlow

Historial de cambios notables del proyecto InvoiceFlow. Este documento sigue la especificación [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

## [3.0.2] — 2026-07-18

### 🐛 Fixed

**Sistema de Logging Centralizado:**
- Nuevo módulo `app/backend/logger.py` con logging configurado
- Logs guardados en `data/logs/invoiceflow.log`
- Rotación automática (10MB por archivo, 5 backups)
- Console + file handlers

**Script de Inicio Completo:**
- Nuevo `start_all.py` que inicia todos los servicios
- Incluye MCP Toolbox (5000), Backend (8000), Supplier (8001), Contract (8002), External Auditor (8003)
- Verificación de puertos y espera de disponibilidad
- Gestión de procesos (inicio/detención con Ctrl+C)

---

## [3.0.1] — 2026-07-18

### 🐛 Fixed

**Fix de paths y documentación:**
- Corrección de imports en A2A server.py
- Fix de paths de módulos en scripts de inicio
- Actualización de .gitignore
- Limpieza de archivos de test en processed/

---

## [3.0.0] — 2026-07-18

### 🎉 Release Final — Sistema Multiagente Completo

> Sistema listo para entrega del Trabajo Práctico de Sistemas Multiagentes.

---

### ✨ Added

#### Sistema Multiagente Completo (Google ADK)
- **6 Agentes implementados** con roles específicos:
  - `InvoiceOrchestrator` (root agent) — Coordina el flujo completo
  - `RouterAgent` — Clasificador de intenciones del chat
  - `ValidatorAgent` — Valida proveedores
  - `ContractAgent` — Controla límites contractuales con RAG
  - `PaymentAgent` — Registra pagos en SQLite
  - `InvoiceManagerAgent` — Gestiona archivos y extracción
- **State compartido** entre agentes via `DatabaseSessionService`
- **Sub-agentes** delegables desde el orquestador

#### MCP Toolbox Server (Puerto 5000)
- **5 herramientas predefinidas** en YAML:
  - `get_supplier_status` — Obtiene estado de proveedor
  - `check_supplier_active` — Verifica si está activo
  - `list_active_suppliers` — Lista proveedores activos
  - `get_supplier_by_cuit` — Busca por CUIT
  - `check_supplier_contract` — Verifica contrato existente
- **Configuración via YAML** (`mcp_config/tools.yaml`)
- **Solo consultas SELECT** (seguridad)

#### A2A Protocol (Agente Externo)
- **ExternalAuditorAgent** en `a2a/external_auditor_agent/`
- **Puerto 8003** — Servidor independiente
- **Auditoría de facturas** escaladas (> $500.000)
- **Dictámenes** con hallazgos categorizados

#### Guardrails Mejorados
- **26 reglas** en 4 categorías:
  - **VR** (Validación Estructural): 7 reglas
  - **BR** (Reglas de Negocio): 10 reglas
  - **SR** (Seguridad): 5 reglas
  - **CR** (Continuidad): 3 reglas
- **Templates en YAML** (`guardrails/rules.yaml`)
- **Guardrail Engine** con evaluación prioritaria

#### RAG con ChromaDB
- **Contract Service** (puerto 8002)
- **Embeddings** con Gemini Embedding 001
- **Búsqueda semántica** en contratos
- **Indexación automática** de nuevos contratos

#### Machine Learning
- **Modelo de riesgo** en `ml/risk_model.py`
- **Features**: monto, antigüedad, historial, fraccionamiento
- **scikit-learn** para clasificación
- **Tool integrada** en el flujo de validación

#### Evaluación con LLM as a Judge
- **Golden Cases** (6 casos de prueba)
- **Gemini como juez** — evaluación semántica
- **BertScore** para métricas de similitud
- **Métricas**: accuracy, precision, recall

#### Asistente IA "GI" Mejorado
- **15+ intents** reconocidos
- **Memoria conversacional** con sesiones persistentes
- **Entity extraction** automática (supplier_id, amount, mode)
- **Acciones ejecutables** sobre el sistema:
  - Modificar límites de contratos
  - Activar/desactivar proveedores
  - Procesar facturas
  - Consultar estados
- **Confirmaciones** para acciones destructivas

#### Observabilidad Completa
- **Health checks** de todos los servicios
- **Dashboard de métricas** en BackOffice
- **Tracking de logs** por nivel
- **Estado de agentes** en tiempo real
- **Integración RAG** visible

---

### 🔄 Changed

- **Backend** reorganizado en `app/backend/`
- **Servicios** en `app/services/`
- **Datos** en `app/data/` y `data/`
- **Scripts de inicio** centralizados en `start_servers.py`
- **Frontend** con auto-refresh cada 10 segundos

---

### ✅ Validación del Sistema

```
invoice_approval_system/
├── 6/6 Golden Cases PASS (100%)
├── 26 Guardrails rules
├── 4 Microservicios operativos
├── 6 Agentes ADK
├── 9 Tools
├── 5 MCP Toolbox tools
└── Pass Rate: 100%
```

---

## [2.3.1] — 2026-07-17

### 🐛 Fixed

**Fix de paths y documentación**:
- Corrección de imports en A2A server.py
- Fix de paths de módulos en scripts de inicio
- Actualización de .gitignore
- Limpieza de archivos de test en processed/

---

## [2.3.0] — 2026-07-13

### ✨ Added

**Observabilidad Completa V3** — Sistema de monitoreo integral:

- **Health Score dinámico** con cálculo ponderado (100% = healthy, 70% = degraded)
- **8 secciones de monitoreo** en la UI:
  - 🔴 Servicios: Backend, Supplier, Contract, MCP Toolbox, External Auditor
  - 🗄️ Bases de Datos: suppliers.db, payments.db, chat_sessions.db, inbox.db
  - 🔧 Integraciones MCP
  - 📚 RAG / ChromaDB
  - 📁 Sistema de Archivos
  - 📋 Logs del Sistema
  - 🤖 Agentes IA
  - 🔗 Integración A2A

---

## [2.2.0] — 2026-07-13

### ✨ Added

**Procesamiento automático de facturas (BUG-022)**:
- File watcher detecta archivos nuevos en inbox
- Procesa automáticamente con el orchestrator
- Mueve archivos a processed/ o rejected/

**Auto-refresh del Frontend**:
- Inbox y Dashboard se actualizan cada 10 segundos

---

## [2.1.0] — 2026-07-13

### 🐛 Fixed

**Parser de facturas (BUG-021)**:
- Formatos soportados: AFIP estándar, nuevo formato, simple
- Fecha de emisión corregida
- Monto parseado correctamente

---

## [2.0.0] — 2026-07-13

### 🎉 Release — Sistema 100% Operativo

> Validación: 60/60 checks PASS | 6/6 Golden Cases PASS | 100% Pass Rate

---

### ✨ Added

#### Asistente IA "GI" (SPEC_013)
- Chat conversacional con memoria
- 15+ intents con acciones ejecutables
- Entity extraction automática
- Confirmaciones para acciones destructivas

#### ABM de Proveedores (SPEC_012)
- CRUD completo de proveedores
- Gestión de contratos (EXACTO/NO_SUPERAR)
- Baja lógica con confirmación

---

## [1.0.0] — 2025-06-20

### ✨ Added

#### Sistema de Guardrails Completo
- 26 reglas en 4 categorías (VR, BR, SR, CR)
- Archivo de configuración `rules.yaml`
- Motor de evaluación `guardrail_engine.py`

#### Agentes ADK Base
- Router Agent, Invoice Manager Agent
- External Auditor Agent

#### Flujo B — Consulta de Estado
- Tool `invoice_status_tool.py`
- Endpoint para consultar estado

#### Sistema ML de Riesgo
- Tool `ml_risk_tool.py`
- Modelo entrenable con scikit-learn

#### Frontend con Sidebar
- Supplier Portal con navegación
- Back Office con tabs

---

## [0.9.0] — 2025-05-10

### ✨ Added

- Sistema multiagente base con Google ADK
- Agentes: validator, contract, payment
- Integración con ChromaDB para RAG
- Microservicios Supplier (8001) y Contract (8002)

---

## [0.8.0] — 2025-04-01

### ✨ Added

- Estructura base del proyecto
- Definición de agentes y herramientas
- Base de datos con proveedores de prueba
- API REST básica con FastAPI

---

## [0.1.0] — 2025-03-01

### ✨ Added

- Estructura inicial del repositorio
- Documento de requerimientos
- Wireframes de interfaces

---

## Convenciones de Versión

| Tipo | Cambio | Ejemplo |
|------|--------|---------|
| **MAJOR** | Cambios incompatibles en la API | 0.9.0 → 1.0.0 |
| **MINOR** | Nuevas funcionalidades compatibles | 2.2.0 → 2.3.0 |
| **PATCH** | Correcciones de bugs | 2.3.0 → 2.3.1 |

---

## Estados de Release

| Símbolo | Estado | Descripción |
|---------|--------|-------------|
| 🟢 | Stable | Funciona correctamente, listo para producción |
| 🟡 | Beta | Funcional pero con limitaciones conocidas |
| 🔴 | Alpha | En desarrollo activo |

---

## Roadmap

### [3.1.0] — Q4 2026
- [ ] Persistencia de sesiones de chat con títulos editables
- [ ] Streaming de respuestas (Server-Sent Events)
- [ ] Sugerencias de acciones (autocomplete)
- [ ] Integración real con PDF (parser de PDF con Gemini)

### [3.2.0] — Q1 2027
- [ ] Dashboard en tiempo real con WebSockets
- [ ] Notificaciones push al proveedor
- [ ] Exportación de reportes en PDF/Excel

### [4.0.0] — 2027
- [ ] Microservicios con Kubernetes
- [ ] Base de datos PostgreSQL
- [ ] Autenticación OAuth2/OIDC
- [ ] Arquitectura multi-tenant

---

## Créditos

| Rol | Descripción |
|-----|-------------|
| **Desarrollo** | Giselle Fernández |
| **Institución** | Universidad de Palermo |
| **Materia** | Sistemas Multiagentes |
| **Año** | 2025-2026 |

### Tecnologías Principales

| Tecnología | Uso |
|------------|-----|
| Google ADK | Framework de agentes |
| FastAPI | Backend API |
| ChromaDB | Vector store (RAG) |
| SQLite | Base de datos |
| Google Gemini | Modelo de lenguaje |
| scikit-learn | Machine learning |
| Model Context Protocol | MCP Toolbox |
| BertScore | Métricas de evaluación |

---

## Licencia

Este proyecto es **académico** y fue desarrollado con fines educativos para la materia de Sistemas Multiagentes de la Universidad de Palermo (2025-2026).

---

*Última actualización: 2026-07-18*
