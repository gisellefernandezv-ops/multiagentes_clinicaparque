"""Tool RAG — búsqueda de contratos en ChromaDB.

Wrapper sobre `rag.retriever.retrieve_contract_info` para ser usado como
`FunctionTool` por el agente de contrato de ADK.
"""

from __future__ import annotations

from typing import Dict

from rag.retriever import retrieve_contract_info


def search_contract_tool(supplier_id: str, amount: float) -> dict:
    """Busca el contrato vigente del proveedor y verifica el monto autorizado.

    Args:
        supplier_id: ID del proveedor (ej. "SUP001").
        amount: Monto de la factura a verificar.

    Returns:
        dict con:
            - found (bool): si se encontró el contrato.
            - supplier_id (str).
            - contract_fragment (str): fragmento del contrato más relevante.
            - contract_limit (float): monto máximo autorizado extraído.
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
            "error": "supplier_id vacío",
        }

    if amount is None or amount < 0:
        return {
            "found": False,
            "supplier_id": supplier_id,
            "contract_fragment": "",
            "contract_limit": 0.0,
            "within_limit": False,
            "amount_checked": amount or 0.0,
            "error": "monto inválido",
        }

    result: Dict = retrieve_contract_info(supplier_id, float(amount))

    # Si la búsqueda semántica no encontró un fragmento del supplier correcto,
    # devolvemos un resultado explícito "no encontrado" para que el agente
    # pueda rechazar de forma trazable.
    if result.get("found") and result.get("contract_limit", 0.0) <= 0:
        result["found"] = False
        result["error"] = (
            "No se pudo extraer el monto máximo del contrato encontrado. "
            "Posible inconsistencia en el documento."
        )

    return result


if __name__ == "__main__":
    # Test rápido
    r = search_contract_tool("SUP001", 50000.0)
    print("SUP001 / $50.000:")
    print(f"  found={r['found']}  limit=${r['contract_limit']}  within={r['within_limit']}")
    print(f"  fragmento: {r['contract_fragment'][:200]}...")

    r2 = search_contract_tool("SUP001", 200000.0)
    print(f"\nSUP001 / $200.000:")
    print(f"  found={r2['found']}  limit=${r2['contract_limit']}  within={r2['within_limit']}")