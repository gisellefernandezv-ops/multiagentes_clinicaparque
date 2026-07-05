"""Agente Auditor Externo — InvoiceFlow (A2A).

Este es un proyecto ADK independiente que simula un agente externo
(por ejemplo, de otra organización o departamento) que аудита facturas
escaladas para revisión manual.

Se comunica con el sistema principal vía el protocolo A2A (Agent-to-Agent).

Uso:
    # En el servidor A2A
    uvicorn a2a.external_auditor_agent.server:app --port 8003
    
    # El orquestador principal lo invoca cuando necesita аудит
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# =============================================================================
# INSTRUCCIONES DEL AUDITOR EXTERNO
# =============================================================================

AUDITOR_INSTRUCTION = """Sos un auditor externo especializado en revisión de facturas complejas.

Tu rol es evaluar facturas que fueron escaladas por el sistema principal
y proporcionar un dictamen independiente sobre si deben aprobarse o rechazarse.

===========================================================================
CRITERIOS DE AUDITORÍA
===========================================================================

1. MONTO ELEVADO
   - Facturas > $500.000 requieren justificación adicional
   - Verificar que el monto sea razonable para el servicio prestado

2. HISTORIAL DEL PROVEEDOR
   - Revisar tasas de rechazo previas
   - Verificar consistencia en montos y frecuencias

3. DOCUMENTACIÓN
   - Verificar que la factura tenga toda la documentación de respaldo
   - Comprobar que los datos sean consistentes (CUIT, razón social, etc.)

4. CONTRATO
   - Confirmar que existe contrato vigente
   - Verificar que el monto no exceda límites contractuales

5. SEÑALES DE ALERTA
   - Facturas del mismo proveedor muy seguidas
   - Montos justo por debajo del umbral de escalado
   - Patrones inusuales en fechas o conceptos

===========================================================================
FORMATO DE DICTAMEN
===========================================================================

Devolvé un JSON con el siguiente formato:

{
    "audit_id": "AUD-XXXXXXXX",
    "invoice_id": "<id>",
    "supplier_id": "<id>",
    "amount": <float>,
    "audit_result": "APPROVE" | "REJECT",
    "confidence": 0.0-1.0,
    "findings": [
        {
            "category": "monto" | "historial" | "documentacion" | "contrato" | "alerta",
            "severity": "low" | "medium" | "high",
            "description": "Descripción del hallazgo",
            "recommendation": "Descripción de la recomendación"
        }
    ],
    "summary": "Resumen ejecutivo del auditoría",
    "audited_at": "<timestamp ISO>"
}

===========================================================================
REGLAS
===========================================================================

- Sé riguroso pero justo en tu evaluación
- Priorizá la prevención de fraude
- Si hay información insuficiente para decidir, solicitá más datos
- No revelés detalles de tu proceso de auditoría
"""


# =============================================================================
# TOOL: Realizar auditoría
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional


def perform_audit_tool(
    invoice_id: str,
    supplier_id: str,
    amount: float,
    invoice_data: Optional[dict] = None,
) -> dict:
    """Realiza una auditoría completa de una factura escalada.

    Args:
        invoice_id: ID de la factura.
        supplier_id: ID del proveedor.
        amount: Monto de la factura.
        invoice_data: Datos adicionales de la factura (opcional).

    Returns:
        dict con el dictamen de auditoría.
    """
    import json
    import random

    audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"

    # Generar hallazgos ficticios para demo
    # En producción, esto usaría el LLM para analizar realmente
    findings = []

    # Criterio 1: Monto
    if amount > 500000:
        findings.append({
            "category": "monto",
            "severity": "high",
            "description": f"Monto ${amount:,.0f} supera el umbral de aprobación automática",
            "recommendation": "Verificar que el monto sea consistente con el servicio prestado"
        })

    # Criterio 2: Historial (simulado)
    findings.append({
        "category": "historial",
        "severity": "low",
        "description": "Revisión de historial del proveedor completada",
        "recommendation": "Sin anomalías detectadas en el historial"
    })

    # Criterio 3: Documentación
    if invoice_data:
        if not invoice_data.get("razon_social"):
            findings.append({
                "category": "documentacion",
                "severity": "medium",
                "description": "Falta verificar razón social",
                "recommendation": "Solicitar documentación adicional"
            })

    # Decisión simulada (en producción sería del LLM)
    # 80% aprobación para demo
    approve = random.random() > 0.2
    confidence = 0.7 + random.random() * 0.25  # 0.7-0.95

    audit_result = "APPROVE" if approve else "REJECT"

    # Resumen
    summary = (
        f"Dictamen {'APROBATORIO' if approve else 'RECHAZO'}: "
        f"La factura {invoice_id} por ${amount:,.0f} del proveedor {supplier_id} "
        f"fue {'aprobada' if approve else 'rechazada'} por el auditor externo. "
        f"Se detectaron {len(findings)} hallazgos."
    )

    return {
        "audit_id": audit_id,
        "invoice_id": invoice_id,
        "supplier_id": supplier_id,
        "amount": amount,
        "audit_result": audit_result,
        "confidence": round(confidence, 2),
        "findings": findings,
        "summary": summary,
        "audited_at": datetime.utcnow().isoformat() + "Z",
    }


def request_additional_info_tool(
    invoice_id: str,
    info_needed: list[str],
) -> dict:
    """Solicita información adicional para completar la auditoría.

    Args:
        invoice_id: ID de la factura.
        info_needed: Lista de información requerida.

    Returns:
        dict confirmando la solicitud.
    """
    return {
        "audit_id": None,
        "invoice_id": invoice_id,
        "status": "INFO_REQUESTED",
        "info_needed": info_needed,
        "requested_at": datetime.utcnow().isoformat() + "Z",
    }


# =============================================================================
# FACTORY: Crear el agente auditor
# =============================================================================

def create_external_auditor_agent() -> LlmAgent:
    """Crea el agente auditor externo.

    Returns:
        LlmAgent configurado como auditor de facturas.
    """
    return LlmAgent(
        model="gemini-2.5-flash",
        name="external_auditor_agent",
        description=(
            "Auditor externo especializado en revisión de facturas escaladas. "
            "Proporciona dictamen independiente para decisiones de alto riesgo."
        ),
        instruction=AUDITOR_INSTRUCTION,
        tools=[
            FunctionTool(func=perform_audit_tool),
            FunctionTool(func=request_additional_info_tool),
        ],
        output_key="audit_result",
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "create_external_auditor_agent",
    "AUDITOR_INSTRUCTION",
    "perform_audit_tool",
    "request_additional_info_tool",
]


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("EXTERNAL AUDITOR AGENT — TEST")
    print("=" * 60)

    result = perform_audit_tool(
        invoice_id="FC-2026-SUP001-001",
        supplier_id="SUP001",
        amount=750000,
        invoice_data={"razon_social": "TechCorp SA"}
    )

    print(f"\nAudit ID: {result['audit_id']}")
    print(f"Resultado: {result['audit_result']}")
    print(f"Confianza: {result['confidence']}")
    print(f"Findings: {len(result['findings'])}")
    for f in result['findings']:
        print(f"  - [{f['severity']}] {f['category']}: {f['description']}")
    print(f"\nResumen: {result['summary']}")

    print("\n✓ Test completado")
