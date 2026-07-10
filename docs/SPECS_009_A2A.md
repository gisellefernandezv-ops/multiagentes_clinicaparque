# SPECS 009 — Protocolo A2A y External Auditor

> **Proyecto**: InvoiceFlow  
> **Tipo**: Especificación de Comunicación  
> **Estado**: ✅ Implementado (Demo)

---

## 1. Resumen del Protocolo A2A

**Agent-to-Agent (A2A)** permite la comunicación entre agentes de diferentes sistemas o proyectos ADK independientes.

### 1.1 Caso de Uso

Cuando una factura es escalada (`ESCALATED`) por superar el umbral de $500,000, el orquestador consulta a un auditor externo para obtener un dictamen.

### 1.2 Arquitectura

```
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│    SISTEMA PRINCIPAL            │   A2A   │    EXTERNAL AUDITOR            │
│                                 │  HTTP   │                                 │
│  ┌─────────────────────────┐   │         │  ┌─────────────────────────┐   │
│  │ Invoice Orchestrator    │───────────────>│ External Auditor Agent   │   │
│  └─────────────────────────┘   │         │  └─────────────────────────┘   │
│          │                     │         │          │                  │
│          │ (ESCALATE)           │         │          │ Dictamen          │
│          ▼                     │         │          ▼                  │
│  ┌─────────────────────────┐   │         │  ┌─────────────────────────┐   │
│  │ External Auditor Tool   │<───────────────│ perform_audit_tool     │   │
│  └─────────────────────────┘   │         │  └─────────────────────────┘   │
└─────────────────────────────────┘         └─────────────────────────────────┘
        Puerto 8000                                  Puerto 8003
```

---

## 2. External Auditor Agent

### 2.1 Información General

| Campo | Valor |
|-------|-------|
| **Nombre** | `external_auditor_agent` |
| **Puerto** | 8003 |
| **Modelo** | gemini-2.5-flash |
| **Ubicación** | `a2a/external_auditor_agent/` |

### 2.2 Archivos

```
a2a/external_auditor_agent/
├── agent.py       # Definición del agente
├── server.py      # Servidor FastAPI
└── __init__.py
```

---

## 3. Herramientas del Auditor

### 3.1 perform_audit_tool

**Propósito**: Realizar auditoría completa de una factura escalada.

**Parámetros**:
```python
invoice_id: str           # ID de la factura
supplier_id: str          # ID del proveedor
amount: float             # Monto de la factura
invoice_data: dict = None # Datos adicionales
```

**Retorno**:
```python
{
    "audit_id": str,           # "AUD-XXXXXXXX"
    "invoice_id": str,
    "supplier_id": str,
    "amount": float,
    "audit_result": "APPROVE" | "REJECT",
    "confidence": float,       # 0.0 - 1.0
    "findings": [
        {
            "category": str,   # monto | historial | documentacion | contrato | alerta
            "severity": str,   # low | medium | high
            "description": str,
            "recommendation": str
        }
    ],
    "summary": str,
    "audited_at": str          # ISO timestamp
}
```

### 3.2 request_additional_info_tool

**Propósito**: Solicitar información adicional para completar la auditoría.

**Parámetros**:
```python
invoice_id: str
info_needed: list[str]
```

---

## 4. Criterios de Auditoría

### 4.1 Categorías de Hallazgos

| Categoría | Descripción |
|-----------|-------------|
| `monto` | Verificación de monto elevado |
| `historial` | Revisión de historial del proveedor |
| `documentacion` | Completitud de documentación |
| `contrato` | Verificación contractual |
| `alerta` | Señales de alerta |

### 4.2 Severidades

| Severidad | Significado |
|-----------|-------------|
| `low` | Sin anomalías |
| `medium` | Requiere revisión |
| `high` | Requiere acción inmediata |

---

## 5. Integración con Orquestador

### 5.1 Flujo de Escalado

```
1. Guardrail detecta monto > $500,000
2. Orquestador detecta action = ESCALATE
3. Orquestador invoca External Auditor (A2A)
4. Auditor realiza auditoría
5. Auditor devuelve dictamen
6. Orquestador registra decisión final
```

### 5.2 Implementación (Conceptual)

```python
# En orchestrator.py
if guardrail_result["action"] == "ESCALATE":
    # Invocar A2A External Auditor
    audit_result = external_auditor.perform_audit(
        invoice_id=invoice["invoice_id"],
        supplier_id=invoice["supplier_id"],
        amount=invoice["amount"]
    )
    
    if audit_result["audit_result"] == "APPROVE":
        final_decision = "APPROVED"
    else:
        final_decision = "REJECTED"
```

---

## 6. Servidor A2A

### 6.1 Punto de Entrada

```bash
uvicorn a2a.external_auditor_agent.server:app --port 8003
```

### 6.2 Endpoints

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/health` | Health check |
| POST | `/audit` | Realizar auditoría |

---

## 7. Limitaciones de la Demo

⚠️ **Nota**: La implementación actual es una demo. En producción:

1. El External Auditor debería ser un **servicio independiente real**
2. La comunicación A2A debería usar el **protocolo estándar de A2A**
3. El dictamen debería ser **vinculante** (automático o con intervención humana)

---

## 8. Referencias

| Documento | Descripción |
|-----------|-------------|
| `a2a/external_auditor_agent/agent.py` | Definición del agente |
| `a2a/external_auditor_agent/server.py` | Servidor |
| `SPECS_002_AGENTES.md` | Integración con orquestador |

---

**Versión**: 2.0.0  
**Última actualización**: 2026-07-15
