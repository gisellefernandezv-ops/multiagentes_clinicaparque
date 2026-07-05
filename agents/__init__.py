"""Paquete `agents` — definición de los agentes del sistema InvoiceFlow.

Agentes disponibles:
- orchestrator: Coordina todo el flujo
- router_agent: Clasifica intención en canal chat
- validator_agent: Valida proveedor
- contract_agent: Verifica contrato (RAG)
- payment_agent: Registra pagos
- invoice_manager_agent: Gestiona facturas

Uso:
    from agents import create_orchestrator, create_router_agent
    
    orchestrator = create_orchestrator()
    router = create_router_agent()
"""

from agents.validator_agent import create_validator_agent
from agents.contract_agent import create_contract_agent
from agents.payment_agent import create_payment_agent
from agents.orchestrator import create_orchestrator
from agents.invoice_manager_agent import create_invoice_manager_agent
from agents.router_agent import create_router_agent

__all__ = [
    "create_validator_agent",
    "create_contract_agent",
    "create_payment_agent",
    "create_orchestrator",
    "create_invoice_manager_agent",
    "create_router_agent",
]
