# Changelog — InvoiceFlow

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

## [1.0.0] — 2025-XX-XX

### Added

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
  - Detecta: new_invoice, check_status, chitchat, technical_support
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
- Dashboard con 5 badges de estado (Pendiente, Aprobada, Escalada, Rechazada, Pagada)
- Upload de PDF con drag & drop
- Historial filtrable por año, mes, estado
- Modal de detalle con información contextual según estado
- Chat flotante accesible desde cualquier página
- Footer con datos de contacto

**Back Office (Con Sidebar)**:
- Sidebar de navegación: Dashboard, Inbox, Historial, Chat interno, Estado de Agentes, Evaluación, Docs
- Dashboard con tarjetas de estados y filtro por año/mes
- Panel de Inbox con upload y procesamiento
- Chat interno diferenciado del chat de soporte
- Página de Observabilidad con métricas de agentes
- Página de Evaluación con resultados LLM-as-a-Judge
- Documentación técnica integrada

#### Evaluación y Testing
- **20 Golden Cases** en `invoiceflow-dataset.json`
- Configuración de evaluación `eval_config.yaml`
- Métricas: accuracy, precision, recall, latency, coverage

#### A2A External Auditor
- Servidor independiente en puerto 8003
- Agente auditor externo para revisión de facturas escaladas
- Dictámenes con hallazgos categorizados

### Changed

#### Backend — Imports Relativos
- Todos los imports internos del backend ahora usan imports relativos (`.`)
- Archivos `__init__.py` agregados en todos los paquetes
- Estructura de directorios como paquetes Python válidos

#### Orquestador HTTP
- `platform/backend/orchestrator.py` reescrito para usar imports relativos
- `service_clients.py` actualizado
- Routers (`inbox_router.py`, `chat_router.py`, `watcher.py`) con imports corregidos

#### Frontend
- Cambio de navegación por tabs a sidebar (especificación original)
- Actualización de CSS para diseño con sidebar
- Actualización de JavaScript para navegación entre páginas

### Fixed

#### Module Not Found Errors
- Problema de imports en `platform.backend.main`
- Conflictos con directorio `platform/` vs módulo `platform` de Python
- Imports absolutos cambiados a relativos

#### Path Issues en Windows
- Scripts `.bat` corregidos para ejecutar desde cualquier ubicación
- Manejo de rutas con espacios y caracteres especiales

---

## [0.9.0] — 2025-01-15

### Added

#### Sistema Multiagente ADK
- Implementación base del orquestador con Google ADK
- Agentes: validator_agent, contract_agent, payment_agent
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

## [0.8.0] — 2025-01-01

### Added

- Estructura base del proyecto
- Definición de agentes y herramientas
- Base de datos con proveedores y contratos de prueba
- API REST básica con FastAPI

---

## Notas de Versión

### Convenciones de Versión
- **MAJOR**: Cambios incompatibles en la API
- **MINOR**: Nuevas funcionalidades compatibles
- **PATCH**: Correcciones de bugs

### Estado de Releases
- 🟢 **Stable**: Funciona correctamente
- 🟡 **Beta**: Funcional pero con limitaciones conocidas
- 🔴 **Alpha**: En desarrollo activo

---

## Migración entre Versiones

### De 0.9.x a 1.0.0

1. **Actualizar dependencias:**
```bash
pip install -r requirements.txt
```

2. **Limpiar caché de Python:**
```bash
rmdir /s /q __pycache__
rmdir /s /q platform\__pycache__
rmdir /s /q agents\__pycache__
# etc.
```

3. **Re-iniciar servicios:**
```bash
python INICIAR.bat
```

### Configuración Requerida

El archivo `rules.yaml` es nuevo en 1.0.0. Asegúrate de que exista en:
```
guardrails/rules.yaml
```

---

## Próximas Versiones

### [1.1.0] — Planeado
- [ ] Integración completa con Google ADK Eval
- [ ] Dashboard en tiempo real con WebSockets
- [ ] Notificaciones push al proveedor
- [ ] Exportación de reportes en PDF/Excel

### [1.2.0] — Planeado
- [ ] Integración con sistema contable externo
- [ ] Módulo de reporting avanzado
- [ ] Machine Learning para predicción de fraude
- [ ] API GraphQL como alternativa a REST

### [2.0.0] — Roadmap
- [ ] Microservicios con Kubernetes
- [ ] Base de datos PostgreSQL
- [ ] Autenticación OAuth2/OIDC
- [ ] Multi-tenant architecture

---

## Créditos

Desarrollado para el Trabajo Práctico de Sistemas Multiagentes
Universidad Palermo — 2025

### Autores
- Equipo de desarrollo InvoiceFlow

### Tecnologías
- Google ADK
- FastAPI
- ChromaDB
- SQLite
- Google Gemini

---

## Licencia

Este proyecto es académico y fue desarrollado con fines educativos.
