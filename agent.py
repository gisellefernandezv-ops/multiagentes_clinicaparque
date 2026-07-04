"""Entry point de ADK — exporta `root_agent`.

Este archivo es el que Google ADK detecta al correr `adk web` desde el
directorio padre.

Uso:
    cd invoice_approval_system
    adk web .
    # o, desde el padre:
    adk web invoice_approval_system

La UI queda en http://localhost:8000.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Asegurar que el directorio raíz esté en sys.path (necesario para que
# `adk web` encuentre los imports relativos tipo `from agents...`)
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Cargar .env lo antes posible para que los tools que leen GOOGLE_API_KEY
# al import-time (ChromaDB embedding function) la encuentren.
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass

# Validación rápida: si no hay API key, fallar con mensaje claro
if not os.getenv("GOOGLE_API_KEY"):
    import warnings
    warnings.warn(
        "GOOGLE_API_KEY no está configurada. "
        "Copiá .env.example a .env y completá tu API key antes de usar el sistema.",
        stacklevel=1,
    )

from agents.orchestrator import create_orchestrator

# ADK busca esta variable a nivel módulo
root_agent = create_orchestrator()


__all__ = ["root_agent"]


if __name__ == "__main__":
    print(f"✓ root_agent: {root_agent.name}")
    print(f"  model: {root_agent.model}")
    print(f"  sub_agents: {[a.name for a in root_agent.sub_agents]}")
    print(f"  tools: {len(root_agent.tools)}")