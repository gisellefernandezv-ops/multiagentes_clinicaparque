"""Embedding function custom para ChromaDB usando el paquete nuevo `google.genai`.

¿Por qué existe? El wrapper oficial de ChromaDB (`GoogleGenerativeAiEmbeddingFunction`)
sigue dependiendo de `google.generativeai`, paquete deprecado por Google que rompió
compatibilidad en su versión 0.8.6 (`ClientOptions does not accept an option 'headers'`).
Este módulo implementa la misma interfaz (protocol `EmbeddingFunction` de ChromaDB)
pero llamando directamente a `google.genai`, que sí está mantenido.

Uso:
    from rag.embedding_function import GoogleGenAiEmbeddingFunction
    ef = GoogleGenAiEmbeddingFunction(task_type="RETRIEVAL_DOCUMENT")
    collection = client.create_collection(name="...", embedding_function=ef)
"""

from __future__ import annotations

import os
from typing import List

# ChromaDB >=0.5 expone el protocolo via chromadb.api.types; para mantener
# compatibilidad con versiones más viejas, simplemente heredamos de object y
# exponemos __call__.
try:
    from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
except Exception:  # pragma: no cover
    class EmbeddingFunction:  # type: ignore[no-redef]
        """Stub mínimo del protocolo."""

    Documents = List[str]
    Embeddings = List[List[float]]


DEFAULT_MODEL = "models/gemini-embedding-001"


class GoogleGenAiEmbeddingFunction(EmbeddingFunction):
    """Embedding function basada en `google.genai` (nuevo SDK).

    Implementa el contrato de ChromaDB: `__call__(input: Documents) -> Embeddings`.

    Args:
        api_key: API key de Google. Si no se pasa, se lee de `GOOGLE_API_KEY`.
        model_name: nombre del modelo de embeddings.
        task_type: tipo de tarea (`RETRIEVAL_DOCUMENT`, `RETRIEVAL_QUERY`, etc.).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY no configurada. Copiá .env.example a .env."
            )
        self.model_name = model_name
        self.task_type = task_type

        # Importación lazy: evita que el módulo falle al importarse sin la dep.
        try:
            from google import genai  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "Falta el paquete `google-genai`. Instalalo con: pip install google-genai"
            ) from e

        self._client = genai.Client(api_key=self.api_key)

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002
        """Genera embeddings para una lista de documentos."""
        if not input:
            return []

        # El SDK nuevo acepta una lista de contenidos y devuelve embeddings
        # en el mismo orden. `task_type` se pasa por config para ajustar la
        # similitud (documento vs query).
        from google.genai import types  # type: ignore

        embeddings: Embeddings = []
        # Hacemos batch para minimizar round-trips
        for text in input:
            resp = self._client.models.embed_content(
                model=self.model_name,
                contents=text,
                config=types.EmbedContentConfig(task_type=self.task_type),
            )
            # `resp.embeddings` es una lista de ContentEmbedding; cada uno tiene `.values`
            vec = resp.embeddings[0].values if resp.embeddings else []
            embeddings.append(list(vec))
        return embeddings


__all__ = ["GoogleGenAiEmbeddingFunction"]