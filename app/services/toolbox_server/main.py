"""
MCP Toolbox Server - InvoiceFlow
Servidor HTTP que expone herramientas definidas en tools.yaml
Compatible con ToolboxToolset de Google ADK (server_url)
"""
import sqlite3
import yaml
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Cargar configuración desde YAML (mcp_config está en la raíz del proyecto)
CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "mcp_config" / "tools.yaml"

def load_config() -> Dict[str, Any]:
    """Carga la configuración desde tools.yaml"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()
DB_PATH = Path(__file__).parent.parent.parent.parent / config["database"]["path"]

# Crear app FastAPI
app = FastAPI(title="InvoiceFlow Toolbox", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Modelos Pydantic
# =============================================================================

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}

class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: List[Dict[str, Any]]

# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health")
def health():
    """Health check"""
    return {
        "status": "ok",
        "service": "invoiceflow-toolbox",
        "version": "1.0.0",
        "tools_count": len(config["tools"]),
        "tools": [t["name"] for t in config["tools"]]
    }

@app.get("/tools")
def list_tools() -> List[ToolInfo]:
    """Lista todas las herramientas disponibles"""
    tools = []
    for tool_def in config["tools"]:
        tools.append(ToolInfo(
            name=tool_def["name"],
            description=tool_def["description"],
            parameters=tool_def.get("parameters", [])
        ))
    return tools

@app.post("/call")
def call_tool(request: ToolCallRequest) -> Dict[str, Any]:
    """Ejecuta una herramienta específica"""
    tool_name = request.tool_name
    arguments = request.arguments
    
    # Buscar la herramienta en la configuración
    tool_def = None
    for t in config["tools"]:
        if t["name"] == tool_name:
            tool_def = t
            break
    
    if not tool_def:
        raise HTTPException(status_code=404, detail=f"Herramienta '{tool_name}' no encontrada")
    
    # Ejecutar la consulta con parámetros
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Filtrar argumentos que coinciden con los parámetros de la query
        query_params = {}
        for p in tool_def.get("parameters", []):
            if p["name"] in arguments:
                query_params[p["name"]] = arguments[p["name"]]
        
        cursor.execute(tool_def["query"], query_params)
        rows = cursor.fetchall()
        
        # Convertir resultados
        results = [dict(row) for row in rows]
        
        return {
            "success": True,
            "tool_name": tool_name,
            "results_count": len(results),
            "results": results
        }
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    finally:
        conn.close()

@app.get("/")
def root():
    """Endpoint raíz con información del servidor"""
    return {
        "service": "InvoiceFlow MCP Toolbox",
        "version": "1.0.0",
        "description": "API de herramientas para validación de proveedores",
        "endpoints": {
            "health": "/health",
            "tools": "/tools",
            "call": "/call"
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("InvoiceFlow MCP Toolbox Server")
    print("=" * 50)
    print(f"DB: {DB_PATH}")
    print(f"Herramientas: {[t['name'] for t in config['tools']]}")
    print("Puerto: 5000")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
