"""Agente validador de proveedores.

Usa MCP Toolbox (configurado en mcp_config/tools.yaml) para verificar que 
el proveedor exista y esté ACTIVE. NO hardcode - toda la config viene del YAML.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools.toolbox_toolset import ToolboxToolset

VALIDATOR_INSTRUCTION = """Sos el agente validador de proveedores del sistema de aprobación de facturas.

Tu responsabilidad es verificar que el proveedor exista en el sistema y esté activo,
y dar la bienvenida al usuario con un mensaje amigable.

PARAMETROS QUE PUEDES RECIBIR:
- supplier_id: ID del proveedor (ej. "SUP001")
- name: nombre o parte del nombre de la empresa
- cuit: número de CUIT/RUC (ej. "30-71234567-0")

HERRAMIENTAS MCP DISPONIBLES (configuradas en tools.yaml):
- get_supplier_status: Obtiene estado y detalles por ID
- check_supplier_active: Verifica si está activo
- get_supplier_by_cuit: Busca por CUIT
- list_active_suppliers: Lista proveedores activos

PASO A PASO:
1. Recibí el valor de búsqueda del orquestador.
2. Usá la herramienta MCP apropiada para verificar el proveedor.
3. Evaluá el resultado:
   
   SI proveedor encontrado y ACTIVE:
     -> Devolvé ÚNICAMENTE este texto (nada más):
       "Hola [name], este es el portal para la gestión de facturación. ¿Querés adjuntar una factura? o ¿Querés consultar el estado de una factura ya enviada?"
     -> El resultado técnico se guarda automáticamente.
   
   SI proveedor encontrado pero INACTIVE:
     -> "Lo sentimos, tu cuenta está actualmente inactiva. Por favor, contactá a soporte para más información."
   
   SI no encontrado:
     -> "No encontramos ningún proveedor registrado con esos datos. Verificá el CUIT o nombre e intentá nuevamente."

REGLAS CRÍTICAS:
- Solo devolvé TEXTO, nunca JSON ni datos técnicos en tu respuesta.
- No incluyas llaves, corchetes ni formato de diccionario en tu respuesta.
- Usá el nombre de la empresa para personalizar el saludo.
- NO menciones estados, categorías, CUIT, email ni teléfonos en el mensaje al usuario.
"""


def create_validator_agent() -> LlmAgent:
    """Crea el sub-agente validador de proveedores.
    
    Usa ToolboxToolset de Google ADK para conectar al servidor MCP
    que lee consultas de mcp_config/tools.yaml (sin hardcode).
    """
    # ToolboxToolset se conecta al servidor MCP que expone las herramientas
    # definidas en tools.yaml. El servidor se especifica en mcp_servers.json
    toolbox_toolset = ToolboxToolset(
        server_url="http://127.0.0.1:5000",
        tool_names=["get_supplier_status", "check_supplier_active", 
                   "get_supplier_by_cuit", "list_active_suppliers"]
    )
    
    return LlmAgent(
        model="gemini-2.5-flash",
        name="validator_agent",
        description="Valida que el proveedor exista y esté activo en el registro.",
        instruction=VALIDATOR_INSTRUCTION,
        tools=[toolbox_toolset],
        output_key="validator_result",
    )


__all__ = ["create_validator_agent", "VALIDATOR_INSTRUCTION"]


if __name__ == "__main__":
    agent = create_validator_agent()
    print(f"OK: {agent.name} creado con ToolboxToolset (config YAML)")
