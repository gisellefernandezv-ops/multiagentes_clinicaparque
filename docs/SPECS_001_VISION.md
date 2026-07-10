# SPECS 001 — Visión General del Sistema

> **Proyecto**: InvoiceFlow — Sistema Multiagente de Aprobación de Facturas  
> **Tipo**: Documento de Visión y Objetivos  
> **Estado**: ✅ Estable

---

## 1. Resumen Ejecutivo

**InvoiceFlow** es un sistema multiagente desarrollado con **Google ADK** que automatiza el proceso de aprobación de facturas de proveedores. El sistema recibe facturas en formato JSON, valida proveedores, verifica límites contractuales mediante RAG, y registra todas las decisiones para auditoría.

### Objetivos Principales

1. ✅ **Automatizar** la validación de facturas de proveedores
2. ✅ **Verificar** que los proveedores estén activos
3. ✅ **Controlar** que los montos no excedan límites contractuales
4. ✅ **Auditar** todas las decisiones (aprobadas, rechazadas, escaladas)
5. ✅ **Proporcionar** interfaces para proveedores y administradores

---

## 2. Stakeholders

| Rol | Interés | Responsabilidad |
|-----|---------|----------------|
| **Proveedores** | Subir facturas, consultar estado | Usar Supplier Portal |
| **Administración** | Aprobar/rechazar/escalar | Usar Back Office |
| **Auditor Externo** | Revisar facturas complejas | Sistema A2A |
| **DevOps** | Mantener sistema | Despliegue y monitoreo |

---

## 3. Stack Tecnológico

| Componente | Tecnología | Versión | Justificación |
|-----------|------------|---------|--------------|
| **Framework de Agentes** | Google ADK | 2.3.0 | Requerido por la consigna |
| **Modelo LLM** | Gemini 2.0 Flash | latest | Balance latencia/costo |
| **Embeddings** | Gemini Embedding | 001 | Compatible con ChromaDB |
| **Vector Store** | ChromaDB | 1.5.9 | Persistencia local sin servidor |
| **Base de Datos** | SQLite | 3.x | Cero configuración |
| **Backend API** | FastAPI | 0.100+ | Alto rendimiento |
| **Lenguaje** | Python | 3.12 | Requerido por consigna |
| **Métricas NLP** | BertScore + XLM-RoBERTa | latest | Evaluación multilingüe |
| **ML** | scikit-learn | latest | Modelo de riesgo |
| **UI** | HTML/CSS/JS | — | Frontend ligero |

---

## 4. Funcionalidades Principales

### 4.1 Flujo A — Alta de Factura

```
Proveedor sube factura → Validación → Control Contractual → Decisión
```

**Pasos**:
1. Proveedor se identifica (CUIT, nombre o ID)
2. Valida proveedor existe y está ACTIVE
3. Extrae datos de factura (PDF o JSON)
4. Aplica guardrails (26 reglas)
5. Verifica contrato vigente (RAG)
6. Verifica monto dentro del límite
7. Registra decisión en SQLite
8. Notifica resultado

**Decisiones Posibles**:
- `APPROVED` → Factura aprobada
- `REJECTED` → Factura rechazada
- `ESCALATED` → Requiere revisión humana

### 4.2 Flujo B — Consulta de Estado

```
Proveedor consulta → Buscar factura → Mostrar estado
```

**Estados Posibles**:
- Pendiente
- Aprobada (esperando pago)
- Escalada (en revisión)
- Rechazada
- Pagada

### 4.3 Canal de Chat

```
Usuario escribe → RouterAgent → Derivar a flujo correspondiente
```

**Intenciones Soportadas**:
- `new_invoice` → Flujo A
- `check_status` → Flujo B
- `chitchat` → Respuesta amigable
- `technical_support` → Ayuda básica

---

## 5. Casos de Uso Principales

### UC-001: Subir Factura Nueva
- Proveedor se loguea
- Adjunta archivo de factura
- Sistema valida y procesa
- Proveedor recibe resultado

### UC-002: Consultar Estado
- Proveedor se loguea
- Solicita estado de factura
- Sistema muestra estado actual

### UC-003: Consultar Historial
- Proveedor ve todas sus facturas
- Filtra por año/mes/estado

### UC-004: Dashboard Back Office
- Admin ve estadísticas
- Gestiona inbox
- Consulta historial completo

---

## 6. Métricas de Éxito

| Métrica | Objetivo | Medición |
|---------|----------|----------|
| **Pass Rate** | > 95% | Golden cases |
| **BertScore F1** | > 0.85 | Justificaciones |
| **Tiempo de respuesta** | < 30s | End-to-end |
| **Uptime** | > 99% | Disponibilidad |

---

## 7. Limitaciones Conocidas

1. **Sin reintentos explícitos**: Si una tool falla, no hay retry automático
2. **Mock del supplier**: En producción debería ser REST API real
3. **Sin autenticación**: UI es local, no expuesta a internet
4. **Sesiones volátiles**: InMemorySessionService pierde al reiniciar

---

## 8. Referencias

| Documento | Descripción |
|-----------|-------------|
| `SPECS_004_FLUJOS.md` | Detalle de Flujo A y B |
| `SPECS_002_AGENTES.md` | Arquitectura de agentes |
| `SPECS_005_GUARDRAILS.md` | Sistema de validación |
| `README.md` | Documentación principal |

---

**Versión**: 2.0.0  
**Última actualización**: 2026-07-15
