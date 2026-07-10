# SPECS 003 — Herramientas del Sistema

> **Proyecto**: InvoiceFlow  
> **Tipo**: Especificación Técnica  
> **Estado**: ✅ Implementado

---

## 1. Índice de Herramientas

| # | Herramienta | Archivo | Agente |
|---|-------------|---------|--------|
| 1 | `supplier_lookup_tool` | `tools/supplier_mcp_tool.py` | validator_agent |
| 2 | `search_contract_tool` | `tools/rag_tool.py` | contract_agent |
| 3 | `register_payment_tool` | `tools/payment_db_tool.py` | payment_agent |
| 4 | `check_invoice_status_tool` | `tools/invoice_status_tool.py` | router_agent |
| 5 | `list_supplier_invoices_tool` | `tools/invoice_status_tool.py` | router_agent |
| 6 | `get_supplier_status_summary_tool` | `tools/invoice_status_tool.py` | router_agent |
| 7 | `list_pending_invoices` | `tools/folder_manager_tool.py` | invoice_manager_agent |
| 8 | `create_supplier_folder` | `tools/folder_manager_tool.py` | invoice_manager_agent |
| 9 | `move_invoice_to_folder` | `tools/folder_manager_tool.py` | invoice_manager_agent |
| 10 | `group_invoices_by_supplier` | `tools/folder_manager_tool.py` | invoice_manager_agent |
| 11 | `list_supplier_folders` | `tools/folder_manager_tool.py` | invoice_manager_agent |
| 12 | `extract_invoice_from_pdf` | `tools/pdf_extractor_tool.py` | orchestrator |
| 13 | `run_invoice_guardrail_tool` | `agents/orchestrator.py` | orchestrator |
| 14 | `perform_audit_tool` | `a2a/external_auditor_agent/agent.py` | external_auditor |
| 15 | `request_additional_info_tool` | `a2a/external_auditor_agent/agent.py` | external_auditor |

---

## 2. Herramientas de Validación

### 2.1 supplier_lookup_tool

**Propósito**: Consultar datos de un proveedor por ID, CUIT o nombre.

**Ubicación**: `tools/supplier_mcp_tool.py`

**Parámetros**:
```python
supplier_id: str = None   # ej. "SUP001"
name: str = None           # ej. "TechCorp"
cuit: str = None           # ej. "30-71234567-0"
```

**Retorno**:
```python
{
    "found": bool,
    "supplier_id": str,
    "name": str,
    "cuit": str,
    "status": "ACTIVE" | "INACTIVE" | "SUSPENDED",
    "category": str,
    "email": str,
    "phone": str,
    "lookup_by": str  # "supplier_id" | "cuit" | "name"
}
```

**Base de datos**: `app/data/suppliers.db`

---

## 3. Herramientas de Contrato (RAG)

### 3.1 search_contract_tool

**Propósito**: Buscar contrato vigente y verificar monto autorizado.

**Ubicación**: `tools/rag_tool.py`

**Parámetros**:
```python
supplier_id: str   # ej. "SUP001"
amount: float       # ej. 50000.0
```

**Retorno**:
```python
{
    "found": bool,
    "supplier_id": str,
    "contract_limit": float,
    "within_limit": bool,
    "contract_fragment": str,  # Texto del contrato
    "amount_checked": float,
    "error": str
}
```

**Dependencias**: ChromaDB + Gemini Embeddings

---

## 4. Herramientas de Pago

### 4.1 register_payment_tool

**Propósito**: Registrar el resultado de una factura en SQLite.

**Ubicación**: `tools/payment_db_tool.py`

**Parámetros**:
```python
invoice_id: str
supplier_id: str
amount: float
decision: str        # "APPROVED" | "REJECTED" | "ESCALATED"
rejection_reason: str = ""
```

**Retorno**:
```python
{
    "success": bool,
    "confirmation_id": str,     # "PAY-XXXXXXXX"
    "payment_status": str,       # "PENDING_PAYMENT" | "REJECTED" | "PENDING_HUMAN_REVIEW"
    "registered_at": str,         # ISO timestamp
    "error": str
}
```

**Base de datos**: `data/payments.db`

**Mapeo de decisiones**:
| Decision | Payment Status |
|----------|----------------|
| APPROVED | PENDING_PAYMENT |
| REJECTED | REJECTED |
| ESCALATED | PENDING_HUMAN_REVIEW |

---

## 5. Herramientas de Estado

### 5.1 check_invoice_status_tool

**Propósito**: Consultar estado de una factura específica.

**Ubicación**: `tools/invoice_status_tool.py`

**Parámetros**:
```python
invoice_id: str
supplier_id: str = None  # Opcional, para seguridad
```

**Retorno**:
```python
{
    "found": bool,
    "invoice_id": str,
    "supplier_id": str,
    "amount": float,
    "decision": str,
    "payment_status": str,
    "rejection_reason": str | null,
    "registered_at": str,
    "confirmation_id": str,
    "display": {
        "label": str,
        "icon": str,
        "descripcion": str,
        "color": str
    },
    "error": str
}
```

### 5.2 list_supplier_invoices_tool

**Propósito**: Listar todas las facturas de un proveedor.

**Parámetros**:
```python
supplier_id: str
limit: int = 50
status_filter: str = None
```

**Retorno**:
```python
{
    "found": bool,
    "supplier_id": str,
    "invoices": [...],
    "total": int,
    "error": str
}
```

### 5.3 get_supplier_status_summary_tool

**Propósito**: Obtener conteo de facturas por estado.

**Parámetros**:
```python
supplier_id: str
```

**Retorno**:
```python
{
    "supplier_id": str,
    "total": int,
    "pending": int,
    "approved": int,
    "rejected": int,
    "escalated": int,
    "paid": int,
    "error": str
}
```

---

## 6. Herramientas de Gestión de Archivos

### 6.1 list_pending_invoices

**Propósito**: Listar facturas pendientes en carpeta.

**Retorno**:
```python
{
    "success": bool,
    "invoices": [
        {
            "filename": str,
            "supplier_id": str | null,
            "path": str,
            "size_kb": float
        }
    ],
    "count": int,
    "folder": str
}
```

### 6.2 create_supplier_folder

**Propósito**: Crear carpeta por CUIT de proveedor.

**Parámetros**:
```python
cuit: str  # ej. "30-71234567-0"
```

### 6.3 move_invoice_to_folder

**Propósito**: Mover factura a carpeta del proveedor.

**Parámetros**:
```python
invoice_filename: str
cuit: str
```

### 6.4 group_invoices_by_supplier

**Propósito**: Agrupar facturas automáticamente por proveedor.

**Parámetros**:
```python
supplier_id: str = None  # Si es null, procesa todos
```

### 6.5 list_supplier_folders

**Propósito**: Listar carpetas de proveedores existentes.

---

## 7. Herramientas del Orquestador

### 7.1 run_invoice_guardrail_tool

**Propósito**: Aplicar guardrails estructurales a una factura.

**Ubicación**: `agents/orchestrator.py`

**Parámetros**:
```python
invoice_json: str  # JSON con datos de factura
```

**Retorno**:
```python
{
    "passed": bool,
    "action": "APPROVE" | "REJECT" | "ESCALATE",
    "reason": str
}
```

### 7.2 extract_invoice_from_pdf

**Propósito**: Extraer datos de factura desde PDF.

**Ubicación**: `tools/pdf_extractor_tool.py`

---

## 8. Herramientas del Auditor Externo

### 8.1 perform_audit_tool

**Propósito**: Realizar auditoría de factura escalada.

**Ubicación**: `a2a/external_auditor_agent/agent.py`

**Parámetros**:
```python
invoice_id: str
supplier_id: str
amount: float
invoice_data: dict = None
```

**Retorno**:
```python
{
    "audit_id": str,        # "AUD-XXXXXXXX"
    "invoice_id": str,
    "supplier_id": str,
    "amount": float,
    "audit_result": "APPROVE" | "REJECT",
    "confidence": float,
    "findings": [
        {
            "category": str,
            "severity": "low" | "medium" | "high",
            "description": str,
            "recommendation": str
        }
    ],
    "summary": str,
    "audited_at": str
}
```

### 8.2 request_additional_info_tool

**Propósito**: Solicitar información adicional para auditoría.

---

## 9. Rutas de Archivos

| Variable | Ruta |
|---------|------|
| `PROJECT_ROOT` | Raíz del proyecto |
| `DATA_DIR` | `app/data/` |
| `PAYMENTS_DB` | `data/payments.db` |
| `SUPPLIERS_DB` | `app/data/suppliers.db` |
| `INVOICES_DIR` | `data/new invoices/` |
| `INBOX_DIR` | `app/data/inbox/` |
| `CHROMA_DIR` | `app/data/chroma_db/` |

---

## 10. Referencias

| Documento | Descripción |
|-----------|-------------|
| `SPECS_002_AGENTES.md` | Cómo se usan las tools |
| `SPECS_005_GUARDRAILS.md` | Sistema de validación |
| `SPECS_008_RAG.md` | ChromaDB y embeddings |

---

**Versión**: 2.0.0  
**Última actualización**: 2026-07-15
