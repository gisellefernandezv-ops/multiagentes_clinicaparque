"""Paquete `agents` — definición de los 5 agentes del sistema."""

from agents.validator_agent import create_validator_agent
from agents.contract_agent import create_contract_agent
from agents.payment_agent import create_payment_agent
from agents.orchestrator import create_orchestrator
from agents.invoice_manager_agent import create_invoice_manager_agent

__all__ = [
    "create_validator_agent",
    "create_contract_agent",
    "create_payment_agent",
    "create_orchestrator",
    "create_invoice_manager_agent",
]