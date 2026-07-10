"""Tool RAG - busqueda de contratos en ChromaDB o Mock.

Wrapper sobre `rag.retriever` para ser usado como
`FunctionTool` por el agente de contrato de ADK.

Si la variable MOCK_RAG=true (default), usa el retriever mock.
Si MOCK_RAG=false, usa ChromaDB real (requiere GOOGLE_API_KEY).
"""

from __future__ import annotations

import os
from typing import Dict

# Importar segun configuracion
if os.getenv("MOCK_RAG", "true").lower() == "true":
    from rag.retriever_backup import retrieve_contract_info
else:
    from rag.retriever import retrieve_contract_info


def search_contract_tool(supplier_id: str, amount: float) -> dict:
    """Busca el contrato vigente del proveedor y verifica el monto autorizado.

    Args:
        supplier_id: ID del proveedor (ej. "SUP001").
        amount: Monto de la factura a verificar.

    Returns:
        dict con:
            - found (bool): si se encontro el contrato.
            - supplier_id (str).
            - contract_fragment (str): fragmento del contrato mas relevante.
            - contract_limit (float): monto maximo autorizado extraido.
            - within_limit (bool): si amount <= contract_limit.
            - amount_checked (float): eco del monto recibido.
            - error (str): mensaje de error si lo hubo.
    """
    if not supplier_id:
        return {
            "found": False,
            "supplier_id": "",
            "contract_fragment": "",
            "contract_limit": 0.0,
            "within_limit": False,
            "amount_checked": amount,
            "error": "supplier_id vacio",
        }

    if amount is None or amount < 0:
        return {
            "found": False,
            "supplier_id": supplier_id,
            "contract_fragment": "",
            "contract_limit": 0.0,
            "within_limit": False,
            "amount_checked": amount or 0.0,
            "error": "monto invalido",
        }

    result = retrieve_contract_info(supplier_id.upper(), float(amount))

    # Si la busqueda no encontro un fragmento del supplier correcto,
    # devolvemos un resultado explicito "no encontrado" para que el agente
    # pueda rechazar de forma trazable.
    if result.get("found") and result.get("contract_limit", 0.0) <= 0:
        result["found"] = False
        result["error"] = (
            "No se pudo extraer el monto maximo del contrato encontrado. "
            "Posible inconsistencia en el documento."
        )

    return result


if __name__ == "__main__":
    # Test rapido
    print("=" * 60)
    print("  RAG TOOL TEST (Mock Mode)")
    print("=" * 60)
    
    r = search_contract_tool("SUP001", 50000.0)
    print("\nSUP001 / $50.000:")
    print(f"  found={r['found']}  limit=${r['contract_limit']:,.0f}  within={r['within_limit']}")
    print(f"  fragmento: {r['contract_fragment'][:100]}...")
    print(f"  mock: {r.get('mock', False)}")
    
    r2 = search_contract_tool("SUP001", 200000.0)
    print(f"\nSUP001 / $200.000:")
    print(f"  found={r2['found']}  limit=${r2['contract_limit']:,.0f}  within={r2['within_limit']}")
    
    r3 = search_contract_tool("SUP999", 50000.0)
    print(f"\nSUP999 (inexistente) / $50.000:")
    print(f"  found={r3['found']}")
    print(f"  error: {r3['error']}")
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETADO")
    print("=" * 60)
