# SPECS 002 — Arquitectura de Agentes ADK

> **Proyecto**: InvoiceFlow  
> **Tipo**: Especificación Técnica  
> **Estado**: ✅ Implementado

---

## 1. Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INVOICE ORCHESTRATOR (Root Agent)                        │
│                         Modelo: gemini-2.5-flash                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │   Router    │  │  Validator  │  │  Contract   │  │     Payment     │    │
│  │   Agent     │  │   Agent    │  │   Agent     │  │     Agent       │    │
│  │  (Sub-Agent)│  │ (Sub-Agent)│  │ (Sub-Agent)│  │   (Sub-Agent)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              INVOICE MANAGER AGENT (Sub-Agent)                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    TOOLS PROPIAS DEL ORQUESTADOR                     │   │
│  │  • run_invoice_guardrail_tool  • extract_invoice_from_pdf            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ A2A (Agent-to-Agent)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL AUDITOR AGENT (A2A)                             │
│                         Puerto: 8003                                        │
│                    Modelo: gemini-2.5-flash                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  • perform_audit_tool     • request_additional_info_tool                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agente Orquestador

### 2.1 Información General

| Campo | Valor |
|-------|-------|
| **Nombre** | `invoice_orchestrator` |
| **Tipo** | LlmAgent (root) |
| **Modelo** | gemini-2.5-flash |
| **Output Key** | `final_decision` |

### 2.2 Sub-Agentes

| Agente | Output Key | Herramienta Principal |
|--------|-----------|---------------------|
| `validator_agent` | `validator_result` | `supplier_lookup_tool` |
| `contract_agent` | `contract_result` | `search_contract_tool` |
| `payment_agent` | `payment_result` | `register_payment_tool` |
| `invoice_manager_agent` | `invoice_manager_result` | `folder_manager_tool` |
| `router_agent` | `router_result` | `classify_intention_tool` |

### 2.3 Tools Propias

```python
tools = [
    FunctionTool(func=run_invoice_guardrail_tool),
    FunctionTool(func=extract_invoice_from_pdf),
]
```

### 2.4 Flujo del Orquestador

```
PASO 0: Identificar proveedor (validator_agent)
    ↓
PASO 1: Recibir PDF de factura
    ↓
PASO 2: Extraer datos (extract_invoice_from_pdf)
    ↓
PASO 3: Aplicar guardrail (run_invoice_guardrail_tool)
    ↓
PASO 4: Validar contrato (contract_agent)
    ↓
PASO 5: Registrar pago (payment_agent)
    ↓
PASO 6: Decisión final
```

---

## 3. Agente Validador

### 3.1 Información General

| Campo | Valor |
|-------|-------|
| **Nombre** | `validator_agent` |
| **Tipo** | LlmAgent (sub) |
| **Modelo** | gemini-2.5-flash |
| **Output Key** | `validator_result` |

### 3.2 Herramienta

```python
tools = [FunctionTool(func=supplier_lookup_tool)]
```

### 3.3 Parámetros de Entrada

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `supplier_id` | str | ID del proveedor (ej. "SUP001") |
| `name` | str | Nombre o parte del nombre |
| `cuit` | str | Número de CUIT |

### 3.4 Respuesta

```python
{
    "found": bool,
    "supplier_id": str,
    "name": str,
    "status": "ACTIVE" | "INACTIVE" | "SUSPENDED",
    "cuit": str,
    # ... otros campos
}
```

---

## 4. Agente de Contrato

### 4.1 Información General

| Campo | Valor |
|-------|-------|
| **Nombre** | `contract_agent` |
| **Tipo** | LlmAgent (sub) |
| **Modelo** | gemini-2.5-flash |
| **Output Key** | `contract_result` |

### 4.2 Herramienta

```python
tools = [FunctionTool(func=search_contract_tool)]
```

### 4.3 Parámetros de Entrada

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `supplier_id` | str | ID del proveedor |
| `amount` | float | Monto de la factura |

### 4.4 Respuesta

```python
{
    "status": "WITHIN_LIMIT" | "EXCEEDS_LIMIT" | "NO_CONTRACT",
    "contract_limit": float,
    "contract_fragment": str,
    "within_limit": bool
}
```

---

## 5. Agente de Pago

### 5.1 Información General

| Campo | Valor |
|-------|-------|
| **Nombre** | `payment_agent` |
| **Tipo** | LlmAgent (sub) |
| **Modelo** | gemini-2.5-flash |
| **Output Key** | `payment_result` |

### 5.2 Herramienta

```python
tools = [FunctionTool(func=register_payment_tool)]
```

### 5.3 Parámetros de Entrada

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `invoice_id` | str | ID de la factura |
| `supplier_id` | str | ID del proveedor |
| `amount` | float | Monto de la factura |
| `decision` | str | APPROVED / REJECTED / ESCALATED |
| `rejection_reason` | str | Motivo del rechazo |

### 5.4 Respuesta

```python
{
    "success": bool,
    "confirmation_id": str,  # PAY-XXXXXXXX
    "payment_status": str,   # PENDING_PAYMENT / REJECTED / PENDING_HUMAN_REVIEW
    "registered_at": str    # ISO timestamp
}
```

---

## 6. Agente Gestor de Facturas

### 6.1 Información General

| Campo | Valor |
|-------|-------|
| **Nombre** | `invoice_manager_agent` |
| **Tipo** | LlmAgent (sub) |
| **Modelo** | gemini-2.5-flash |
| **Output Key** | `invoice_manager_result` |

### 6.2 Herramientas

```python
tools = [
    FunctionTool(func=list_pending_invoices),
    FunctionTool(func=create_supplier_folder),
    FunctionTool(func=move_invoice_to_folder),
    FunctionTool(func=group_invoices_by_supplier),
    FunctionTool(func=list_supplier_folders),
]
```

---

## 7. Agente Router

### 7.1 Información General

| Campo | Valor |
|-------|-------|
| **Nombre** | `router_agent` |
| **Tipo** | LlmAgent (sub) |
| **Modelo** | gemini-2.5-flash |
| **Output Key** | `router_result` |

### 7.2 Herramientas

```python
tools = [
    FunctionTool(func=classify_intention_tool),
    FunctionTool(func=derive_action_tool),
]
```

### 7.3 Intenciones Soportadas

| Intención | Descripción |
|-----------|-------------|
| `new_invoice` | Usuario quiere subir factura |
| `check_status` | Usuario quiere consultar estado |
| `chitchat` | Conversación general |
| `technical_support` | Soporte técnico |

---

## 8. State Compartido

Los agentes se comunican a través del `session.state` de ADK:

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
    "validator_result": dict,
    "contract_result": dict,
    "payment_result": dict,
    
    # Decisión final
    "final_decision": dict
}
```

---

## 9. External Auditor Agent (A2A)

### 9.1 Información General

| Campo | Valor |
|-------|-------|
| **Nombre** | `external_auditor_agent` |
| **Puerto** | 8003 |
| **Modelo** | gemini-2.5-flash |
| **Protocolo** | A2A |

### 9.2 Herramientas

```python
tools = [
    FunctionTool(func=perform_audit_tool),
    FunctionTool(func=request_additional_info_tool),
]
```

### 9.3 Uso

Se invoca cuando una factura es escalada (`ESCALATED`) para revisión manual.

---

## 10. Referencias

| Documento | Descripción |
|-----------|-------------|
| `SPECS_003_HERRAMIENTAS.md` | Detalle de todas las tools |
| `SPECS_004_FLUJOS.md` | Cómo los agentes interactúan |
| `SPECS_009_A2A.md` | Protocolo A2A |

---

**Versión**: 2.0.0  
**Última actualización**: 2026-07-15
