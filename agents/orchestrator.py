"""Agente orquestador (root agent).

Coordina los agentes especializados en orden estricto:
    1. PDF Extractor     -> extrae datos del PDF de factura
    2. validator_agent   -> valida proveedor
    3. contract_agent    -> verifica contrato (RAG)
    4. Si monto > $500.000 -> call_external_auditor_tool (A2A)
    5. payment_agent     -> registra en SQLite

Aplica guardrail antes de aprobar. Toma decision final:
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
from tools.a2a_audit_tool import call_external_auditor_tool


# ----------------------------------------------------------------------
# Tool local del orquestador: aplica el guardrail estructural
# ----------------------------------------------------------------------


def run_invoice_guardrail_tool(invoice_json: str, tool_context: Optional[ToolContext] = None) -> dict:
    """Aplica el guardrail estructural a la factura.

    El orquestador llama a esta tool antes de tomar la decision final.
    Devuelve un dict con `passed`, `action` y `reason`.
    """
    try:
        invoice_data = json.loads(invoice_json) if isinstance(invoice_json, str) else invoice_json
    except (json.JSONDecodeError, TypeError) as e:
        return {"passed": False, "action": "REJECT", "reason": f"JSON invalido: {e}"}

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

ORCHESTRATOR_INSTRUCTION = """Sos el orquestador del sistema de aprobacion de facturas de proveedores.

Tu rol es coordinar los agentes especializados en orden estricto. NUNCA
apruebes una factura sin completar todos los pasos. Si algun agente reporta
error o rechazo, detenes el flujo y registras el motivo.

===========================================================================
FLUJO OBLIGATORIO (en este orden estricto)
===========================================================================

PASO 0 - IDENTIFICACION DEL PROVEEDOR (OBLIGATORIO)
=====================================================
Este es el PRIMER paso. No continues hasta identificar al proveedor.

ACCIONES:
1. Mostrar el mensaje inicial:
   "Bienvenido al portal de proveedores. Por favor, identificate con tu CUIT, nombre o numero de proveedor."
   
2. Cuando el usuario proporcione sus datos (CUIT, nombre o ID):
   - NO intentes leer del state, el valor acaba de llegar
   - Transferir al sub-agente `validator_agent` pasándole directamente el valor
     que el usuario ingreso
   - El agente hara la busqueda en la base de datos y mostrara los datos del proveedor
   
3. Si el proveedor es encontrado y esta ACTIVE:
   - Mostrar la informacion y preguntar:
     "Queres adjuntar una factura? o Queres consultar el estado de una factura ya enviada?"
   - Guardar en state: supplier_id, supplier_name, supplier_status, supplier_email
   
4. Si el usuario eligio "consultar factura ya enviada":
   - Transferir al sub-agente `invoice_manager_agent` para buscar facturas del proveedor
   
5. Si el usuario eligio "adjuntar factura":
   - Continuar con el PASO 1 (recepc ion de PDF)
   
IMPORTANTE: El valor que el usuario ingresa va en el parametro de la llamada
   al validator_agent. NO lo busques en el state porque aun no existe.

PASO 1 - RECEPCION DEL PDF (solo si proveedor validado)
========================================================
Una vez confirmado por el usuario, pedir el PDF de la factura.

ACCIONES:
1. Usar la tool `extract_invoice_from_pdf` con el contenido del PDF
2. Extraer: invoice_id, amount, currency, invoice_date
3. VERIFICAR que el CUIT/proveedor del PDF coincida con el identificado
   en el PASO 0. Si no coincide -> RECHAZAR y explicar por que.

4. MOSTRAR un resumen de la factura:
   "Factura: [invoice_id]"
   "Importe: [currency] [amount]"
   "Fecha: [invoice_date]"
   "Confirma el envio para aprobacion?"

PASO 2 - GUARDRAIL ESTRUCTURAL
===============================
Una vez confirmado, llamar a `run_invoice_guardrail_tool` con los datos.
Registrar en state: guardrail_action, guardrail_reason

PASO 3 - CONTROL CONTRACTUAL (RAG)
===================================
Transferir al sub-agente `contract_agent` con supplier_id y amount.
Verificar que existe contrato vigente y el monto esta dentro del limite.

PASO 4 - DECISION DE ESCALADO (A2A)
====================================
Si el monto supera $500.000:
   -> Llamar a `call_external_auditor_tool` con:
      - invoice_id
      - supplier_id
      - amount
      - invoice_data (datos de la factura)
   -> El External Auditor devuelve un dictamen:
      - audit_result: "APPROVE" o "REJECT"
      - summary: resumen de la auditoria
      - findings: lista de hallazgos
   -> Usar el resultado del auditor para la decision final

PASO 5 - REGISTRO DE PAGO
==========================
Transferir al sub-agente `payment_agent` con todos los datos.

PASO 6 - DECISION FINAL
========================
{
    "decision": "APPROVED" | "REJECTED" | "ESCALATED",
    "invoice_id": "<id>",
    "supplier_id": "<id>",
    "supplier_name": "<nombre>",
    "amount": <float>,
    "currency": "<moneda>",
    "rejection_reason": "<motivo o vacio>",
    "confirmation_id": "<id>",
    "payment_status": "<estado>",
    "guardrail_action": "<APPROVE|REJECT|ESCALATE>",
    "guardrail_reason": "<motivo>",
    "audit_result": "<si fue auditado externamente>",
    "audit_summary": "<resumen del auditor externo>"
}

===========================================================================
REGLAS CRITICAS
===========================================================================
- El proveedor DEBE estar identificado y validado ANTES de pedir el PDF.
- El CUIT del PDF debe coincidir con el proveedor identificado.
- Si el monto supera $500.000, llamar SIEMPRE al External Auditor via A2A.
- Mostrar el progreso del flujo en cada paso.
- El resultado del auditor externo es OBLIGATORIO para facturas > $500.000.
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
            "Orquestador del sistema de aprobacion de facturas. "
            "Recibe un PDF de factura, extrae los datos, identifica al proveedor, "
            "y coordina validator_agent -> contract_agent -> payment_agent. "
            "Para montos > $500.000 invoca al External Auditor via A2A."
        ),
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=[
            FunctionTool(func=run_invoice_guardrail_tool),
            FunctionTool(func=extract_invoice_from_pdf),
            FunctionTool(func=call_external_auditor_tool),
        ],
        sub_agents=[validator, contract, payment, invoice_manager],
        output_key="final_decision",
    )


# Alias para que `agent.py` lo importe directamente
root_agent = None  # se setea en agent.py para evitar import circular


__all__ = ["create_orchestrator", "root_agent", "ORCHESTRATOR_INSTRUCTION", "run_invoice_guardrail_tool"]


if __name__ == "__main__":
    orch = create_orchestrator()
    print(f"Orchestrator creado: {orch.name}")
    print(f"  Sub-agentes: {[a.name for a in orch.sub_agents]}")
    print(f"  Tools propios: {len(orch.tools)}")
