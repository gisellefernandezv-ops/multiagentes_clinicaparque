# MCP Toolbox for Databases - InvoiceFlow

## Concepto

**MCP Toolbox** es un patrón de integración que usa el servidor MCP de Google (`toolbox_adk`) para exponer herramientas de base de datos configuradas via archivo YAML, sin hardcodear SQL en el código del agente.

## Arquitectura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Validator     │────▶│  ToolboxToolset │────▶│  toolbox_server │
│   Agent (ADK)   │     │   (Google ADK)  │     │  (lee tools.yaml)│
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │  suppliers.db   │
                                                │  (SQLite)       │
                                                └─────────────────┘
```

## Archivos de Configuración

### 1. `mcp_config/tools.yaml`
Define las consultas SQL permitidas (SOLO LECTURA):

```yaml
database:
  path: "app/data/suppliers.db"
  type: "sqlite"

tools:
  - name: "get_supplier_status"
    description: "Obtiene estado de proveedor"
    query: "SELECT ... WHERE supplier_id = :supplier_id"
    parameters:
      - name: "supplier_id"
        type: "string"
        required: true

security:
  readonly: true
```

### 2. `mcp_config/mcp_servers.json`
Configura el servidor MCP para ADK:

```json
{
  "mcpServers": {
    "invoiceflow-toolbox": {
      "command": "python",
      "args": ["-m", "app.services.toolbox_server.main"],
      "cwd": "invoice_approval_system"
    }
  }
}
```

## Ventajas de Seguridad

| Aspecto | Con SQL arbitrario | Con Toolbox YAML |
|---------|-------------------|------------------|
| Consultas permitidas | CUALQUIERA | Solo las definidas |
| Riesgo de injection | ALTO | NULO |
| Auditoria | Dificil | Facil (YAML) |
| Modificacion DB | Posible | BLOQUEADA |

## Uso en el Agente

```python
from google.adk.tools.toolbox_toolset import ToolboxToolset

# NO hardcode - todo viene del YAML
toolbox = ToolboxToolset(
    server_url="http://127.0.0.1:5000",
    tool_names=["get_supplier_status", "check_supplier_active"]
)

agent = LlmAgent(
    model="gemini-2.5-flash",
    name="validator_agent",
    tools=[toolbox]
)
```

## Inicio del Servidor MCP

```bash
# Opcion 1: Directo
python -m app.services.toolbox_server.main

# Opcion 2: Con MCP CLI
mcp run app/services/toolbox_server/main.py
```

## Agregar Nueva Consulta

1. Editar `mcp_config/tools.yaml`
2. Agregar entrada en `tools:`
3. Reiniciar el servidor MCP
4. Agregar `tool_name` a ToolboxToolset en el agente

**NO requiere cambiar código Python.**
