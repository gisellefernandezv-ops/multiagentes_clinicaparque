"""Paquete `guardrails` — reglas de seguridad y validación de InvoiceFlow.

Módulos:
- invoice_guardrail: Funciones legacy de validación
- guardrail_engine: Motor YAML que procesa rules.yaml
- rules.yaml: Archivo de configuración de todas las reglas

Uso:
    from guardrails.guardrail_engine import GuardrailEngine, evaluate_guardrails
    
    engine = GuardrailEngine()
    result = engine.evaluate(invoice_data)
"""

from guardrails.invoice_guardrail import apply_invoice_guardrail
from guardrails.guardrail_engine import (
    GuardrailEngine,
    evaluate_guardrails,
    get_engine,
)

__all__ = [
    "apply_invoice_guardrail",
    "GuardrailEngine",
    "evaluate_guardrails",
    "get_engine",
]
