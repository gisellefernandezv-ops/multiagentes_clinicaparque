# InvoiceFlow — Índice de Especificaciones

> Documento maestro que organiza y referencia todas las especificaciones técnicas del proyecto.

---

## 📋 Tabla de Contenidos

| # | Spec | Descripción | Estado |
|---|------|-------------|--------|
| 000 | INDICE | Este documento — índice y navegación | ✅ |
| 001 | VISION | Visión general, objetivos, stack | ✅ |
| 002 | AGENTES | Arquitectura de agentes ADK | ✅ |
| 003 | HERRAMIENTAS | Tools y funciones del sistema | ✅ |
| 004 | FLUJOS | Flujo A (alta) y Flujo B (estado) | ✅ |
| 005 | GUARDRAILS | Sistema de validación (26 reglas) | ✅ |
| 006 | BACKEND | API REST y routers | ✅ |
| 007 | FRONTEND | Supplier Portal y Back Office | ✅ |
| 008 | RAG | ChromaDB y retrieval | ✅ |
| 009 | A2A | Protocolo Agent-to-Agent | ✅ |
| 010 | EVALUACION | Testing, golden cases, métricas | ✅ |
| 011 | ESTADO | Análisis E2E, bugs, roadmap | ✅ |
| **012** | **PROVEEDORES** | **ABM de proveedores + contratos con modo** | ✅ |
| **013** | **CHAT IA** | **Asistente IA con memoria y acciones** | ✅ |

---

## 📁 Archivos Creados

```
docs/
├── SPECS_000_INDICE.md          ← Este archivo (actualizado)
├── SPECS_001_VISION.md          ← Visión general ✅ NUEVO
├── SPECS_002_AGENTES.md          ← Arquitectura de agentes ✅ NUEVO
├── SPECS_003_HERRAMIENTAS.md     ← Tools del sistema ✅ NUEVO
├── SPECS_004_FLUJOS.md          ← Flujos de negocio ✅ NUEVO
├── SPECS_005_GUARDRAILS.md       ← Sistema de guardrails ✅ NUEVO
├── SPECS_006_BACKEND.md          ← API REST ✅ NUEVO
├── SPECS_007_FRONTEND.md         ← Interfaces ✅ NUEVO
├── SPECS_008_RAG.md              ← ChromaDB ✅ NUEVO
├── SPECS_009_A2A.md              ← External Auditor ✅ NUEVO
├── SPECS_010_EVALUACION.md       ← Testing ✅ NUEVO
├── SPECS_011_ESTADO.md           ← Análisis E2E ✅ NUEVO
├── SYSTEM_PROMPT.md              ← Prompt del sistema ✅ NUEVO
├── SPECS_012_PROVEEDORES.md       ← ABM proveedores + contratos ✅ NUEVO (2026-07-09)
├── SPECS_013_CHAT_IA.md            ← Asistente IA con memoria y acciones ✅ NUEVO (2026-07-09)
├── documento_guardrails_invoiceflow.md (existente)
├── especificacion_sistema_invoiceflow.md (existente)
├── GUIA_RAPIDA.md (actualizado)
├── INSTALACION_WINDOWS.md (actualizado)
├── INSTALACION_LINUX.md (actualizado)
└── INSTALACION_MACOS.md (actualizado)
```

---

## 🔗 Referencias Cruzadas

### Spec 001 → Visión
- Define los objetivos del sistema
- Identifica los stakeholders

### Spec 002 → Agentes
- Implementa los agentes definidos en visión
- Conecta con Spec 003 (tools)

### Spec 003 → Herramientas
- Provee las tools que los agentes usan
- Conecta con Spec 008 (RAG)

### Spec 004 → Flujos
- Implementa Flujo A y B
- Usa agents (Spec 002) y tools (Spec 003)

### Spec 005 → Guardrails
- Sistema de validación
- Aplica a todos los flujos

### Spec 006 → Backend
- API REST que expone funcionalidades
- Integra todos los componentes

### Spec 007 → Frontend
- Supplier Portal (proveedores)
- Back Office (administración)

### Spec 008 → RAG
- ChromaDB para búsqueda semántica
- Usa contracts como fuente de conocimiento

### Spec 009 → A2A
- External Auditor Agent
- Comunicación entre agentes

### Spec 010 → Evaluación
- Golden cases
- Métricas de calidad

### Spec 011 → Estado
- **DOCUMENTO MÁS IMPORTANTE** — Análisis E2E
- Identifica qué está funcionando ✅
- Identifica qué falta ⚠️
- Identifica bugs ❌

### SYSTEM_PROMPT
- Prompt del sistema para agentes
- Incluye identidad, reglas, datos de prueba

---

## 🚀 Uso Rápido

1. **Nuevo en el proyecto**: Empezar por `SPECS_001_VISION.md`
2. **Entender los flujos**: Leer `SPECS_004_FLUJOS.md`
3. **Desarrollar features**: Consultar specs relevantes
4. **Debugging**: Revisar `SPECS_011_ESTADO.md`
5. **Prompt de agentes**: Ver `SYSTEM_PROMPT.md`

---

## 📊 Resumen de Documentación

| Categoría | Archivos |
|-----------|----------|
| Especificaciones | 12 archivos (SPECS_000 - SPECS_011) |
| Instalación | 4 archivos (Windows, Linux, macOS, Guía rápida) |
| Técnicos | 2 archivos (Guardrails, Especificación sistema) |
| Prompts | 1 archivo (SYSTEM_PROMPT.md) |
| **Total** | **19 archivos de documentación** |

---

**Versión**: 2.2.0  
**Última actualización**: 2026-07-15
