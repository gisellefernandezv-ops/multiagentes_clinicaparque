"""Retriever semántico sobre ChromaDB para el agente de contrato.

Expone una función `retrieve_contract_info(supplier_id, amount)` que devuelve
el fragmento más relevante del contrato y el monto máximo extraído por regex.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Asegurar que el directorio raíz esté en sys.path
import sys as _sys
if str(PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(PROJECT_ROOT))

from rag.embedding_function import GoogleGenAiEmbeddingFunction

CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_db"
COLLECTION_NAME = "contracts"


def _get_embedding_function():
    """Embedding function para queries RAG.

    Usa `RETRIEVAL_QUERY` para optimizar la similitud cuando el texto
    embebido es una consulta (no un documento).
    """
    return GoogleGenAiEmbeddingFunction(
        model_name="models/gemini-embedding-001",
        task_type="RETRIEVAL_QUERY",
    )


def _parse_amount(text: str) -> Optional[float]:
    """Extrae un monto numérico de un string con formato '$150.000' o '$150,000.00'.

    Acepta separadores de miles con punto o coma. Si encuentra varios, devuelve
    el primero que parezca monto principal (heurística: el primero precedido
    por 'monto', 'máximo', 'autorizado', 'límite' o '$').
    """
    if not text:
        return None

    # Limpiar texto: quedarnos con los segmentos que contengan $
    # y posibles candidatos con palabras clave
    text_clean = text.replace("\xa0", " ")

    # Patrón 1: buscar "$ número" precedido por palabras clave (más confiable)
    priority_pattern = re.compile(
        r"(?:monto\s+m[áa]ximo|monto\s+autorizado|l[íi]mite\s+m[áa]ximo|m[áa]ximo\s+autorizado)"
        r"[^\d\$]{0,40}"
        r"\$\s*([\d\.,]+)",
        re.IGNORECASE,
    )
    m = priority_pattern.search(text_clean)
    candidates = []
    if m:
        candidates.append(m.group(1))

    # Patrón 2: cualquier "$ número" como fallback
    generic_pattern = re.compile(r"\$\s*([\d\.,]+)")
    for gm in generic_pattern.finditer(text_clean):
        candidates.append(gm.group(1))

    for raw in candidates:
        try:
            value = _normalize_number(raw)
            if value and value > 0:
                return value
        except (ValueError, TypeError):
            continue

    return None


def _normalize_number(raw: str) -> float:
    """Normaliza '150.000' / '150,000' / '150.000,50' / '150,000.50' a float.

    Heurística:
      - Si tiene tanto . como ,: el último separador es el decimal.
      - Si solo tiene uno de los dos:
          * Si tiene exactamente 3 dígitos después del separador, es miles.
          * Si tiene 1-2 dígitos después, es decimal.
    """
    s = raw.strip()

    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        # El último en aparecer es el decimal
        if s.rfind(".") > s.rfind(","):
            # formato US: 1,234.56
            s = s.replace(",", "")
        else:
            # formato EU: 1.234,56
            s = s.replace(".", "").replace(",", ".")
    elif has_comma:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 3:
            # separador de miles: 150,000
            s = s.replace(",", "")
        else:
            # decimal con coma: 150,50
            s = s.replace(",", ".")
    # else: solo punto. Si tiene 3 dígitos después, es miles; si no, decimal.
    elif has_dot:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(".", "")

    return float(s)


def _get_collection():
    """Carga la colección ChromaDB (lazy init)."""
    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            f"ChromaDB no inicializada en {CHROMA_DIR}. "
            "Corré primero: python rag/ingest.py"
        )
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=_get_embedding_function(),
    )


def retrieve_contract_info(supplier_id: str, amount: float, n_results: int = 2) -> Dict:
    """Busca el contrato del proveedor en ChromaDB y extrae el monto máximo.

    Args:
        supplier_id: ID del proveedor (ej. "SUP001").
        amount: Monto de la factura a contrastar (solo se usa para devolver
            `within_limit` en el resultado).
        n_results: cantidad de chunks a recuperar.

    Returns:
        dict con:
            - found: bool
            - supplier_id: str
            - contract_fragment: str (texto del chunk más relevante)
            - all_chunks: List[str] (todos los chunks recuperados)
            - contract_limit: float (0.0 si no se pudo extraer)
            - within_limit: bool
            - amount_checked: float
            - raw_extraction: str (el match regex antes de normalizar)
    """
    try:
        collection = _get_collection()
    except FileNotFoundError as e:
        return {
            "found": False,
            "supplier_id": supplier_id,
            "contract_fragment": "",
            "all_chunks": [],
            "contract_limit": 0.0,
            "within_limit": False,
            "amount_checked": amount,
            "raw_extraction": "",
            "error": str(e),
        }

    # Construir query rica: incluir el ID del proveedor para mejorar el match
    query_text = (
        f"contrato proveedor {supplier_id} "
        f"monto máximo autorizado por factura límite"
    )

    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )
    except Exception as e:
        return {
            "found": False,
            "supplier_id": supplier_id,
            "contract_fragment": "",
            "all_chunks": [],
            "contract_limit": 0.0,
            "within_limit": False,
            "amount_checked": amount,
            "raw_extraction": "",
            "error": f"ChromaDB query failed: {e}",
        }

    documents: List[str] = results.get("documents", [[]])[0] if results else []
    metadatas: List[dict] = results.get("metadatas", [[]])[0] if results else []

    # Filtrar: quedarnos solo con chunks del supplier_id correcto
    filtered_docs = []
    for doc, meta in zip(documents, metadatas):
        if meta.get("supplier_id", "").upper() == supplier_id.upper():
            filtered_docs.append(doc)

    # Si el filtrado dejó la lista vacía pero hay docs, los usamos todos
    # (puede pasar que el supplier_id del metadata no esté bien poblado en alguna versión)
    chosen_docs = filtered_docs if filtered_docs else documents

    if not chosen_docs:
        return {
            "found": False,
            "supplier_id": supplier_id,
            "contract_fragment": "",
            "all_chunks": [],
            "contract_limit": 0.0,
            "within_limit": False,
            "amount_checked": amount,
            "raw_extraction": "",
            "error": "No se encontraron chunks relevantes",
        }

    fragment = chosen_docs[0]

    # Extraer monto del fragmento principal; si falla, probar en todos los chunks
    raw_extraction = ""
    contract_limit = _parse_amount(fragment) or 0.0
    if contract_limit == 0.0:
        for d in chosen_docs:
            v = _parse_amount(d)
            if v and v > 0:
                contract_limit = v
                raw_extraction = d
                break

    # Capturar el match crudo para auditoría
    if contract_limit > 0:
        m = re.search(r"\$\s*([\d\.,]+)", fragment)
        if m:
            raw_extraction = m.group(1)

    return {
        "found": True,
        "supplier_id": supplier_id,
        "contract_fragment": fragment,
        "all_chunks": chosen_docs,
        "contract_limit": contract_limit,
        "within_limit": (contract_limit > 0 and amount <= contract_limit),
        "amount_checked": amount,
        "raw_extraction": raw_extraction,
        "error": "",
    }


if __name__ == "__main__":
    # Test rápido desde CLI
    import sys
    sid = sys.argv[1] if len(sys.argv) > 1 else "SUP001"
    amt = float(sys.argv[2]) if len(sys.argv) > 2 else 50000.0
    result = retrieve_contract_info(sid, amt)
    print(f"\n=== Resultado para {sid} / ${amt} ===")
    print(f"Found: {result['found']}")
    print(f"Contract limit: ${result['contract_limit']}")
    print(f"Within limit: {result['within_limit']}")
    print(f"\nFragmento:\n{result['contract_fragment'][:400]}...")