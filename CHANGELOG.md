# Changelog — InvoiceFlow

Historial de cambios notables del proyecto InvoiceFlow. Este documento sigue la especificación [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

## [2.0.0] — 2026-07-15

### 🎉 Release Final — Sistema 100% Operativo

> **Validación**: 60/60 checks PASS | 6/6 Golden Cases PASS | 100% Pass Rate

---

### ✨ Added

#### Asistente IA "GI" con Memoria y Acciones (SPEC_013)
- **Chat conversacional** integrado en BackOffice
- **Memoria de sesión**: las últimas 5 interacciones se persisten en `chat_sessions.db`
- **Acciones ejecutables** (15+ intents):
  - `set_contract_limit`: cambiar límite de contrato
  - `set_contract_mode`: cambiar modo EXACTO/NO_SUPERAR
  - `activate_supplier` / `deactivate_supplier`
  - `update_supplier_field`: cambiar email, teléfono, nombre, etc.
  - `delete_supplier` con confirmación
  - `memory_action`: "ahora desactiva ese mismo"
- **Entity extraction**: detecta supplier_id, amount, mode, field automáticamente
- **Confirmaciones** para acciones destructivas
- **Mensaje de bienvenida** al entrar a la pestaña
- Endpoints REST: `POST /chat`, `GET/POST/DELETE /chat/sessions/{id}`

#### ABM de Proveedores y Contratos (SPEC_012)
- **CRUD completo** de proveedores (POST/PUT/DELETE/GET)
- **Gestión de contratos** con `mode` (EXACTO o NO_SUPERAR)
- **Auto-generación** de `supplier_id` (SUP00X)
- **Validación de CUIT** único
- **Baja lógica** (`status = INACTIVE`)
- **Nueva tabla `contracts`** en `suppliers.db`
- **Integración con orchestrator**: validación según `mode`
- Endpoints proxy en backend (same-origin para evitar CORS)
- UI completa: modal alta/edición, búsqueda, tabla responsive

#### Especificaciones Nuevas
- `docs/SPECS_012_PROVEEDORES.md`
- `docs/SPECS_013_CHAT_IA.md`
- `docs/SPECS_000_INDICE.md` actualizado

### 🐛 Fixed

**20 bugs resueltos** (ver `bugs/`):

| Componente | Bugs | Descripción |
|------------|------|-------------|
| Frontend API | BUG-001 | API path mismatch (`/api/*` vs `/*`) |
| Dashboard | BUG-002 | Campos incorrectos (`approved` vs `decisions.APPROVED`) |
| Inbox/History | BUG-003, BUG-004 | Formato JSON incorrecto |
| Chat | BUG-005 | Campo `response` vs `message` |
| Cache | BUG-008, BUG-009 | Browser cachea archivos antiguos |
| CORS | BUG-011 | Cross-origin bloqueado |
| Modal | BUG-013 | Modal no superpone correctamente |
| Factura B | BUG-014, BUG-015 | Formato real FC-PV-NRO + tipos A/B/C |
| Proveedores | BUG-016, BUG-017, BUG-018 | ABM completo + UI responsive |
| Chat IA | BUG-019, BUG-020 | Entendimiento de "montos" + acciones |

### ✅ Validación Completa del Sistema

```
FULL_ANALYSIS_REPORT.json — 2026-07-15
├── 60/60 checks PASS (100%)
├── 6/6 Golden Cases PASS (100%)
├── Pass Rate: 100.0%
└── Todos los servicios operativos
```

| Servicio | Puerto | Estado |
|----------|--------|--------|
| Backend | 8000 | ✅ Operativo |
| Supplier Service | 8001 | ✅ Operativo |
| Contract Service | 8002 | ✅ Operativo |
| External Auditor | 8003 | ✅ Operativo |

### 🔄 Changed

- **Chat backend** (`chat_router.py`) reescrito completamente (350+ líneas)
- **Supplier service** v2.0.0 con tabla `contracts`
- **Frontend** responsive design (mobile/tablet/desktop)
- **Listings** del inbox muestran fecha de emisión
- **Facturas** con formato real: `FC-2026-SUP001-NUEVA-1.txt`
- **Orchestrator** usa `supplier_client.check_contract()` integrado

---

> ℹ️ **Nota**: La versión 1.1.0 fue skippeada. Toda la funcionalidad planeada se integró en v2.0.0.

## [1.1.0] — 2025-07-15

### 🎯 Características Planned

- [ ] Integración completa con Google ADK Eval
- [ ] Dashboard en tiempo real con WebSockets
- [ ] Notificaciones push al proveedor
- [ ] Exportación de reportes en PDF/Excel
- [ ] Integración con sistema contable externo
- [ ] Módulo de reporting avanzado
- [ ] API GraphQL como alternativa a REST

---

## [1.0.0] — 2025-06-20

### ✨ Added

#### Sistema de Guardrails Completo
- **26 reglas de guardrail** implementadas en 4 categorías:
  - **VR (Validación Estructural)**: 7 reglas para validar formato de archivos y datos
  - **BR (Reglas de Negocio)**: 10 reglas para control de aprobación
  - **SR (Seguridad)**: 5 reglas para protección contra accesos indebidos
  - **CR (Continuidad)**: 3 reglas para manejo de fallas
- Archivo de configuración `rules.yaml` como fuente única de verdad
- Motor `guardrail_engine.py` que procesa las reglas en orden de prioridad

#### Agentes ADK
- **Router Agent**: Clasificador de intención para canal de chat
  - Detecta: `new_invoice`, `check_status`, `chitchat`, `technical_support`
  - Implementa reglas SR-03, SR-04, SR-05
- **Invoice Manager Agent**: Gestor de facturas con herramientas de carpeta
- **External Auditor Agent**: Agente A2A para revisión de facturas escaladas

#### Flujo B — Consulta de Estado
- Nueva tool `invoice_status_tool.py`
- Endpoint para consultar estado de facturas existentes
- Resumen de estados por proveedor (5 badges)

#### Sistema ML de Riesgo
- Tool `ml_risk_tool.py` para evaluación de riesgo
- Modelo entrenable con scikit-learn
- Features: monto, antigüedad, historial de rechazos, fraccionamiento
- Recomendaciones: aprobar, revisar, escalar

#### Frontend Actualizado

**Supplier Portal (Con Sidebar)**:
- Header global con logo y datos del proveedor
- Sidebar de navegación: Inicio, Subir factura, Mis facturas, Chat
- Dashboard con 5 badges de estado
- Upload de PDF con drag & drop
- Historial filtrable
- Modal de detalle contextual
- Chat flotante

**Back Office (Con Sidebar)**:
- Sidebar de navegación: Dashboard, Inbox, Historial, Chat interno, Estado de Agentes, Evaluación, Docs
- Dashboard con tarjetas de estados
- Panel de Inbox con upload
- Chat interno
- Página de Observabilidad
- Página de Evaluación
- Documentación técnica

#### Evaluación y Testing
- **20 Golden Cases** en `invoiceflow-dataset.json`
- Configuración de evaluación `eval_config.yaml`
- Métricas: accuracy, precision, recall, latency, coverage

#### A2A External Auditor
- Servidor independiente en puerto 8003
- Agente auditor externo para revisión de facturas escaladas
- Dictámenes con hallazgos categorizados

### 🔄 Changed

- Backend con imports relativos
- Frontend: navegación por sidebar (vs tabs originales)
- CSS y JS actualizados para sidebar

### 🐛 Fixed

- Module Not Found Errors (imports platform/ vs módulo platform)
- Path Issues en Windows (rutas con espacios)

---

## [0.9.0] — 2025-05-10

### ✨ Added

#### Sistema Multiagente ADK
- Implementación base del orquestador con Google ADK
- Agentes: `validator_agent`, `contract_agent`, `payment_agent`
- Integración con ChromaDB para búsqueda RAG
- Guardrails básicos (versión inicial)

#### Microservicios
- Supplier Service (puerto 8001) para validación de proveedores
- Contract Service (puerto 8002) para control contractual
- Base de datos SQLite para persistencia

#### Frontend
- Back Office con tabs para navegación
- Supplier Portal con login básico
- Dashboard con estadísticas de facturas

#### Documentación
- README.md con descripción del sistema
- Especificaciones técnicas en docs/
- Documento de guardrails

---

## [0.8.0] — 2025-04-01

### ✨ Added

- Estructura base del proyecto
- Definición de agentes y herramientas
- Base de datos con proveedores y contratos de prueba
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
| **MINOR** | Nuevas funcionalidades compatibles | 0.8.0 → 0.9.0 |
| **PATCH** | Correcciones de bugs | 0.8.0 → 0.8.1 |

## Estados de Release

| Símbolo | Estado | Descripción |
|---------|--------|-------------|
| 🟢 | Stable | Funciona correctamente, listo para producción |
| 🟡 | Beta | Funcional pero con limitaciones conocidas |
| 🔴 | Alpha | En desarrollo activo |

---

## Migración entre Versiones

### De 0.9.x a 1.0.0

```bash
# 1. Actualizar dependencias
pip install -r requirements.txt

# 2. Limpiar caché de Python
rmdir /s /q __pycache__
rmdir /s /q platform\__pycache__
rmdir /s /q agents\__pycache__

# 3. Re-iniciar servicios
python INICIAR.bat
```

### Configuración Requerida

El archivo `rules.yaml` es nuevo en 1.0.0. Asegúrate de que exista en:
```
guardrails/rules.yaml
```

---

## Roadmap

### [2.1.0] — Q3 2026
- [ ] Persistencia de sesiones de chat con títulos editables
- [ ] Streaming de respuestas (Server-Sent Events)
- [ ] Sugerencias de acciones (autocomplete)
- [ ] Integración real con PDF (parser de PDF con Gemini)
- [ ] Subida de archivos al modal de contratos
- [ ] Multi-idioma (i18n)

### [2.2.0] — Q4 2026
- [ ] Dashboard en tiempo real con WebSockets
- [ ] Notificaciones push al proveedor
- [ ] Exportación de reportes en PDF/Excel
- [ ] Integración con sistema contable externo
- [ ] Machine Learning para predicción de fraude

### [3.0.0] — 2027
- [ ] Microservicios con Kubernetes
- [ ] Base de datos PostgreSQL
- [ ] Autenticación OAuth2/OIDC
- [ ] Arquitectura multi-tenant

---

## Créditos

| Rol | Descripción |
|-----|-------------|
| **Desarrollo** | Equipo InvoiceFlow |
| **Institución** | Universidad de Palermo |
| **Materia** | Sistemas Multiagentes |
| **Año** | 2025-2026 |

### Tecnologías Principales

- Google ADK — Framework de agentes
- FastAPI — Backend API
- ChromaDB — Vector store (RAG)
- SQLite — Base de datos
- Google Gemini — Modelo de lenguaje
- scikit-learn — Machine learning
- **httpx** — Cliente HTTP async para acciones del chat IA

---

## Licencia

Este proyecto es **académico** y fue desarrollado con fines educativos.

---

*Última actualización: 2026-07-15*
