"""Ingesta de contratos a ChromaDB con embeddings de Google Generative AI.

Uso:
    python rag/ingest.py

Chunking por caracteres (500 chars, 50 de overlap). La colección `contracts`
queda persistida en `./data/chroma_db/`.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List

import chromadb
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Asegurar que el directorio raíz esté en sys.path para los imports `rag.*`
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.embedding_function import GoogleGenAiEmbeddingFunction  # noqa: E402

# Rutas
CONTRACTS_DIR = PROJECT_ROOT / "data" / "contracts"
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_db"
COLLECTION_NAME = "contracts"

# Chunking
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def _get_google_embedding_function():
    """Devuelve un embedding function de Google GenAI para ChromaDB.

    Usa el SDK nuevo (`google.genai`) vía `GoogleGenAiEmbeddingFunction`
    para evitar la incompatibilidad con el paquete deprecado
    `google.generativeai` que rompía `chromadb` 1.5.x.
    """
    return GoogleGenAiEmbeddingFunction(
        model_name="models/gemini-embedding-001",
        task_type="RETRIEVAL_DOCUMENT",
    )


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Divide el texto en chunks por caracteres con overlap.

    Estrategia simple: ventanas deslizantes que respetan saltos de párrafo
    cuando es posible (mejor calidad semántica que cortar a la fuerza).
    """
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)

        # Si no estamos al final, intentamos cortar en un salto de línea o espacio
        if end < n:
            # Buscar el último salto de párrafo en el rango
            cut = text.rfind("\n\n", start + chunk_size // 2, end)
            if cut == -1:
                cut = text.rfind(". ", start + chunk_size // 2, end)
            if cut == -1:
                cut = text.rfind(" ", start + chunk_size // 2, end)
            if cut > start:
                end = cut + 1  # incluir el delimitador

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= n:
            break

        # Avanzar, restando el overlap
        start = max(end - overlap, start + 1)

    return chunks


def _extract_supplier_id_from_filename(filename: str) -> str:
    """Extrae el supplier_id del nombre de archivo. Ej: 'contrato_proveedor_001.txt' → 'SUP001'."""
    m = re.search(r"proveedor[_\-]?(\d+)", filename, re.IGNORECASE)
    if not m:
        return "UNKNOWN"
    return f"SUP{m.group(1).zfill(3)}"


def ingest_all_contracts() -> dict:
    """Lee todos los .txt de data/contracts/ y los indexa en ChromaDB.

    Returns:
        dict con estadísticas: {"files": int, "chunks": int, "collection": str}
    """
    if not CONTRACTS_DIR.exists():
        raise FileNotFoundError(f"No existe el directorio: {CONTRACTS_DIR}")

    txt_files = sorted(CONTRACTS_DIR.glob("*.txt"))
    if not txt_files:
        raise RuntimeError(
            f"No hay archivos .txt en {CONTRACTS_DIR}. "
            "Agregá al menos uno antes de ingestar."
        )

    print(f"[ingest] Encontrados {len(txt_files)} contratos en {CONTRACTS_DIR}")

    # Inicializar cliente ChromaDB persistente
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Resetear colección si existe (idempotente para re-ingestas)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"[ingest] Colección '{COLLECTION_NAME}' existente eliminada.")
    except Exception:
        pass

    ef = _get_google_embedding_function()
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"description": "Contratos de proveedores indexados por chunks"},
    )

    total_chunks = 0

    for txt_file in txt_files:
        supplier_id = _extract_supplier_id_from_filename(txt_file.name)
        text = txt_file.read_text(encoding="utf-8")
        chunks = _chunk_text(text)

        print(f"[ingest] {txt_file.name} → supplier={supplier_id}, {len(chunks)} chunks")

        ids = [f"{supplier_id}_chunk_{i:03d}" for i in range(len(chunks))]
        metadatas = [
            {
                "supplier_id": supplier_id,
                "source_file": txt_file.name,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        total_chunks += len(chunks)

    stats = {
        "files": len(txt_files),
        "chunks": total_chunks,
        "collection": COLLECTION_NAME,
        "chroma_path": str(CHROMA_DIR),
    }

    print(f"[ingest] ✓ Ingesta completa: {stats['files']} archivos, {stats['chunks']} chunks")
    print(f"[ingest] ✓ Colección '{COLLECTION_NAME}' persistida en {CHROMA_DIR}")
    return stats


def main():
    """Entry point CLI."""
    try:
        ingest_all_contracts()
    except Exception as e:
        print(f"[ingest] ✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()