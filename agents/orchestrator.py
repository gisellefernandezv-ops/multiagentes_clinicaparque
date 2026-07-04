"""Agente orquestador (root agent).

Coordina los 3 sub-agentes en orden estricto:
    1. PDF Extractor     → extrae datos del PDF de factura
    2. validator_agent   → valida proveedor
    3. contract_agent    → verifica contrato (RAG)
    4. payment_agent     → registra en SQLite

Aplica guardrail antes de aprobar. Toma decisión final:
APPROVED | REJECTED | ESCALATED.
"""

from __future__ import annotations

import json
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, ToolContext

from guardrails.invoice_guardrail import apply_invoice_guardrail
from agents.validator_agent import create_validator_agent
from agents.contract_agent import create_contract_agent
from agents.payment_agent import create_payment_agent
from agents.invoice_manager_agent import create_invoice_manager_agent
from tools.pdf_extractor_tool import extract_invoice_from_pdf

# ----------------------------------------------------------------------
# Tool local del orquestador: aplica el guardrail estructural
# ----------------------------------------------------------------------


def run_invoice_guardrail_tool(invoice_json: str, tool_context: Optional[ToolContext] = None) -> dict:
    """Aplica el guardrail estructural a la factura.

    El orquestador llama a esta tool antes de tomar la decisión final.
    Devuelve un dict con `passed`, `action` y `reason`.
    """
    try:
        invoice_data = json.loads(invoice_json) if isinstance(invoice_json, str) else invoice_json
    except (json.JSONDecodeError, TypeError) as e:
        return {"passed": False, "action": "REJECT", "reason": f"JSON inválido: {e}"}

    result = apply_invoice_guardrail(invoice_data)

    if tool_context is not None:
        try:
            tool_context.state.update(
                {
                    "guardrail_action": result["action"],
                    "guardrail_reason": result["reason"],
                }
            )
        except Exception:
            pass

    return result


# ----------------------------------------------------------------------
# Instruction del orquestador
# ----------------------------------------------------------------------

ORCHESTRATOR_INSTRUCTION = """Sos el orquestador del sistema de aprobación de facturas de proveedores.

Tu rol es coordinar los agentes especializados en orden estricto. NUNCA
apruebes una factura sin completar todos los pasos. Si algún agente reporta
error o rechazo, detenés el flujo y registrás el motivo.

===========================================================================
FLUJO OBLIGATORIO (en este orden estricto)
===========================================================================

PASO 0 — IDENTIFICACIÓN DEL PROVEEDOR (OBLIGATORIO)
══════════════════════════════════════════════════
Este es el PRIMER paso. No continués hasta identificar al proveedor.

ACCIONES:
1. Mostrá el mensaje inicial:
   "🏢 Bienvenido al portal de proveedores. Por favor, identificate con tu CUIT, nombre o número de proveedor."
   
2. Cuando el usuario proporcione sus datos (CUIT, nombre o ID):
   - NO intentes leer del state, el valor acaba de llegar
   - Transferí al sub-agente `validator_agent` pasándole directamente el valor
     que el usuario ingresó
   - El agente hará la búsqueda en la base de datos y mostrará los datos del proveedor
   
3. Si el proveedor es encontrado y está ACTIVE:
   - Mostrá la información y preguntá:
     "¿Querés adjuntar una factura? o ¿Querés consultar el estado de una factura ya enviada?"
   - Guardá en state: supplier_id, supplier_name, supplier_status, supplier_email
   
4. Si el usuario eligió "consultar factura ya enviada":
   - Transferí al sub-agente `invoice_manager_agent` para buscar facturas del proveedor
   
5. Si el usuario eligió "adjuntar factura":
   - Continuar con el PASO 1 (recepción de PDF)
   
⚠️ IMPORTANTE: El valor que el usuario ingresa va en el parámetro de la llamada
   al validator_agent. NO lo busques en el state porque aún no existe.

PASO 1 — RECEPCIÓN DEL PDF (solo si proveedor validado)
═════════════════════════════════════════════════════════
Una vez confirmado por el usuario, pedí el PDF de la factura.

ACCIONES:
1. Usá la tool `extract_invoice_from_pdf` con el contenido del PDF
2. Extraé: invoice_id, amount, currency, invoice_date
3. VERIFICÁ que el CUIT/proveedor del PDF coincida con el identificado
   en el PASO 0. Si no coincide → RECHAZAR y explicar por qué.

4. MOSTRÁ un resumen de la factura:
   "📄 Factura: [invoice_id]"
   "💰 Importe: [currency] [amount]"
   "📅 Fecha: [invoice_date]"
   "¿Confirma el envío para aprobación?"

PASO 2 — GUARDRAIL ESTRUCTURAL
══════════════════════════════════
Una vez confirmado, llamá a `run_invoice_guardrail_tool` con los datos.
Registrá en state: guardrail_action, guardrail_reason

PASO 3 — CONTROL CONTRACTUAL (RAG)
═══════════════════════════════════
Transferí al sub-agente `contract_agent` con supplier_id y amount.
Verificá que existe contrato vigente y el monto está dentro del límite.

PASO 4 — REGISTRO DE PAGO
═════════════════════════════
Transferí al sub-agente `payment_agent` con todos los datos.

PASO 5 — DECISIÓN FINAL
══════════════════════════
{
    "decision": "APPROVED" | "REJECTED" | "ESCALATED",
    "invoice_id": "<id>",
    "supplier_id": "<id>",
    "supplier_name": "<nombre>",
    "amount": <float>,
    "currency": "<moneda>",
    "rejection_reason": "<motivo o vacío>",
    "confirmation_id": "<id>",
    "payment_status": "<estado>",
    "guardrail_action": "<APPROVE|REJECT|ESCALATE>",
    "guardrail_reason": "<motivo>"
}

===========================================================================
REGLAS CRÍTICAS
===========================================================================
- El proveedor DEBE estar identificado y validado ANTES de pedir el PDF.
- El CUIT del PDF debe coincidir con el proveedor identificado.
- Si el monto supera $500.000, escalás SIEMPRE a revisión humana.
- Mostrá el progreso del flujo en cada paso.
"""


def create_orchestrator() -> LlmAgent:
    """Crea el agente orquestador (root agent) con sus sub-agentes."""
    validator = create_validator_agent()
    contract = create_contract_agent()
    payment = create_payment_agent()
    invoice_manager = create_invoice_manager_agent()

    return LlmAgent(
        model="gemini-2.5-flash",
        name="invoice_orchestrator",
        description=(
            "Orquestador del sistema de aprobación de facturas. "
            "Recibe un PDF de factura, extrae los datos, identifica al proveedor, "
            "y coordina validator_agent → contract_agent → payment_agent. "
            "Tambien gestiona facturas con invoice_manager_agent."
        ),
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=[
            FunctionTool(func=run_invoice_guardrail_tool),
            FunctionTool(func=extract_invoice_from_pdf),
        ],
        sub_agents=[validator, contract, payment, invoice_manager],
        output_key="final_decision",
    )


# Alias para que `agent.py` lo importe directamente
root_agent = None  # se setea en agent.py para evitar import circular


__all__ = ["create_orchestrator", "root_agent", "ORCHESTRATOR_INSTRUCTION", "run_invoice_guardrail_tool"]


if __name__ == "__main__":
    orch = create_orchestrator()
    print(f"✓ {orch.name} creado")
    print(f"  Sub-agentes: {[a.name for a in orch.sub_agents]}")
    print(f"  Tools propios: {len(orch.tools)}")