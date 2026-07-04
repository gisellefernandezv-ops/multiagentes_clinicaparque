"""Agente validador de proveedores.

Usa la tool `supplier_lookup_tool` para verificar que el proveedor exista
y esté ACTIVE. Devuelve un dict con el resultado para que el orquestador
lo escriba en el state.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from tools.supplier_mcp_tool import supplier_lookup_tool

VALIDATOR_INSTRUCTION = """Sos el agente validador de proveedores del sistema de aprobación de facturas.

Tu responsabilidad es verificar que el proveedor exista en el sistema y esté activo,
y dar la bienvenida al usuario con un mensaje amigable.

PARAMETROS QUE PUEDES RECIBIR:
- supplier_id: ID del proveedor (ej. "SUP001")
- name: nombre o parte del nombre de la empresa
- cuit: número de CUIT/RUC (ej. "30-71234567-0")

PASO A PASO:
1. Recibí el valor de búsqueda del orquestador.
2. Llamá a la tool `supplier_lookup_tool` con el parámetro apropiado.
3. Evaluá el resultado:
   
   SI `found == True` y `status == "ACTIVE"`:
     → Devolvé ÚNICAMENTE este texto (nada más):
       "Hola [name], este es el portal para la gestión de facturación. ¿Querés adjuntar una factura? o ¿Querés consultar el estado de una factura ya enviada?"
     → El resultado técnico (status, supplier_data) se guarda automáticamente.
   
   SI `found == True` pero `status != "ACTIVE"`:
     → "Lo sentimos, tu cuenta está actualmente inactiva. Por favor, contactá a soporte para más información."
   
   SI `found == False`:
     → "No encontramos ningún proveedor registrado con esos datos. Verificá el CUIT o nombre e intentá nuevamente."

REGLAS CRÍTICAS:
- Solo devolvé TEXTO, nunca JSON ni datos técnicos en tu respuesta.
- No incluyas llaves, corchetes ni formato de diccionario en tu respuesta.
- Usá el nombre de la empresa para personalizar el saludo.
- NO menciones estados, categorías, CUIT, email ni teléfonos en el mensaje al usuario.
"""


def create_validator_agent() -> LlmAgent:
    """Crea el sub-agente validador de proveedores."""
    return LlmAgent(
        model="gemini-2.5-flash",
        name="validator_agent",
        description="Valida que el proveedor exista y esté activo en el registro.",
        instruction=VALIDATOR_INSTRUCTION,
        tools=[FunctionTool(func=supplier_lookup_tool)],
        output_key="validator_result",
    )


__all__ = ["create_validator_agent", "VALIDATOR_INSTRUCTION"]


if __name__ == "__main__":
    agent = create_validator_agent()
    print(f"✓ {agent.name} creado con {len(agent.tools)} tool(s)")