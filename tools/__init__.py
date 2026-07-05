"""Paquete `tools` — FunctionTool consumidas por los agentes de InvoiceFlow.

Tools disponibles:
- supplier_mcp_tool: Lookup de proveedores
- payment_db_tool: Escritura en SQLite de pagos
- rag_tool: Búsqueda de contratos en ChromaDB
- folder_manager_tool: Gestión de carpetas de facturas
- pdf_extractor_tool: Extracción de datos de PDF
- invoice_status_tool: Consulta de estado (Flujo B)
- ml_risk_tool: Evaluación de riesgo con ML

Uso:
    from tools.payment_db_tool import register_payment_tool
    from tools.invoice_status_tool import check_invoice_status_tool
    from tools.ml_risk_tool import evaluate_risk_tool
"""

from tools.supplier_mcp_tool import supplier_lookup_tool
from tools.payment_db_tool import register_payment_tool, list_payments
from tools.rag_tool import search_contract_tool
from tools.pdf_extractor_tool import extract_invoice_from_pdf
from tools.invoice_status_tool import (
    check_invoice_status_tool,
    list_supplier_invoices_tool,
    get_supplier_status_summary_tool,
)
from tools.ml_risk_tool import evaluate_risk_tool, train_risk_model_from_data

__all__ = [
    # Supplier
    "supplier_lookup_tool",
    # Payment
    "register_payment_tool",
    "list_payments",
    # RAG
    "search_contract_tool",
    # PDF
    "extract_invoice_from_pdf",
    # Status (Flujo B)
    "check_invoice_status_tool",
    "list_supplier_invoices_tool",
    "get_supplier_status_summary_tool",
    # ML Risk
    "evaluate_risk_tool",
    "train_risk_model_from_data",
]
