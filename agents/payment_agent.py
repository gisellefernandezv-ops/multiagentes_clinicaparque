"""Agente de registro de pagos.

Persiste el resultado de la aprobación (o rechazo/escalación) en SQLite.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from tools.payment_db_tool import register_payment_tool

PAYMENT_AGENT_INSTRUCTION = """Sos el agente de registro de pagos del sistema de aprobación de facturas.

Tu responsabilidad es dejar constancia permanente del resultado de cada
factura en la base de datos SQLite. Registrás TANTO las aprobadas como las
rechazadas y las escaladas. NUNCA omitás el registro, incluso si hubo error
en los pasos anteriores.

DATOS DISPONIBLES EN EL STATE DE LA SESIÓN:
- invoice_id: ID de la factura
- supplier_id: ID del proveedor
- amount: monto de la factura
- decision: APPROVED | REJECTED | ESCALATED
- rejection_reason: motivo (puede estar vacío si APPROVED)

PASO A PASO:
1. Leé del state: invoice_id, supplier_id, amount, decision, rejection_reason.
2. Llamá a la tool `register_payment_tool` con esos parámetros exactos.
   El nombre de cada parámetro debe coincidir: invoice_id, supplier_id,
   amount, decision, rejection_reason.
3. Devolvé un dict con el resultado:
       {"status": "REGISTERED",
        "confirmation_id": <id devuelto por la tool>,
        "payment_status": <payment_status devuelto>,
        "registered_at": <registered_at devuelto>}
   Si la tool devolvió `success=False`, devolvé:
       {"status": "ERROR",
        "error": <mensaje de error>,
        "confirmation_id": "",
        "payment_status": "",
        "registered_at": ""}

IMPORTANTE:
- Generá siempre un `confirmation_id` único (lo hace la tool automáticamente).
- Aunque `decision` sea REJECTED o ESCALATED, registr igual.
- No tomes decisiones sobre la aprobación (eso es responsabilidad del orquestador).
"""


def create_payment_agent() -> LlmAgent:
    """Crea el sub-agente de registro de pagos."""
    return LlmAgent(
        model="gemini-2.5-flash",
        name="payment_agent",
        description="Registra el resultado de la factura en SQLite.",
        instruction=PAYMENT_AGENT_INSTRUCTION,
        tools=[FunctionTool(func=register_payment_tool)],
        output_key="payment_result",
    )


__all__ = ["create_payment_agent", "PAYMENT_AGENT_INSTRUCTION"]


if __name__ == "__main__":
    agent = create_payment_agent()
    print(f"✓ {agent.name} creado con {len(agent.tools)} tool(s)")