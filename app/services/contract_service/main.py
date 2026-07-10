"""Contract Service — microservicio de contratos + RAG.

Puerto: 8002

Endpoints:
- GET  /health
- POST /contracts/upload         (sube un TXT de contrato)
- GET  /contracts                (lista contratos registrados)
- POST /contracts/{id}/ingest    (re-indexa en ChromaDB)
- POST /contracts/seed           (carga contratos demo)
- GET  /contracts/{supplier_id}/check?amount=N  (verifica límite vía RAG)
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# --- Bootstrap: agregar raíz del proyecto a sys.path ---
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from rag.embedding_function import GoogleGenAiEmbeddingFunction  # noqa: E402

# ----------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------

DATA_DIR = PROJECT_ROOT / "app" / "data"
CONTRACTS_DIR = DATA_DIR / "contracts"
CHROMA_DIR = DATA_DIR / "chroma_db"
CONTRACTS_META = DATA_DIR / "contracts_meta.json"
COLLECTION_NAME = "contracts"

DATA_DIR.mkdir(parents=True, exist_ok=True)
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------
# Storage de metadata (qué contratos hay + supplier_id)
# ----------------------------------------------------------------------

def load_meta() -> dict:
    if CONTRACTS_META.exists():
        return json.loads(CONTRACTS_META.read_text(encoding="utf-8"))
    return {"contracts": {}}  # supplier_id -> {filename, uploaded_at}


def save_meta(meta: dict):
    CONTRACTS_META.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ----------------------------------------------------------------------
# RAG helpers
# ----------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            cut = text.rfind("\n\n", start + chunk_size // 2, end)
            if cut == -1:
                cut = text.rfind(". ", start + chunk_size // 2, end)
            if cut == -1:
                cut = text.rfind(" ", start + chunk_size // 2, end)
            if cut > start:
                end = cut + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _extract_supplier_id(filename: str) -> str:
    import re
    m = re.search(r"proveedor[_\-]?(\d+)", filename, re.IGNORECASE)
    if not m:
        return "UNKNOWN"
    return f"SUP{m.group(1).zfill(3)}"


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = GoogleGenAiEmbeddingFunction(
        model_name="models/gemini-embedding-001",
        task_type="RETRIEVAL_DOCUMENT",
    )
    return client, ef


def ingest_contract(filename: str, text: str) -> dict:
    """Indexa un contrato en ChromaDB. Idempotente (elimina previos del supplier)."""
    supplier_id = _extract_supplier_id(filename)
    client, ef = get_collection()

    # Obtener o crear coleccion (NO eliminar toda la coleccion)
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME, embedding_function=ef
        )
        existing = collection.get(where={"supplier_id": supplier_id})
        if existing and existing.get("ids"):
            collection.delete(ids=existing["ids"])
    except Exception:
        collection = client.create_collection(
            name=COLLECTION_NAME, embedding_function=ef
        )

    chunks = _chunk_text(text)
    ids = [f"{supplier_id}_chunk_{i:03d}" for i in range(len(chunks))]
    metadatas = [
        {
            "supplier_id": supplier_id,
            "source_file": filename,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        for i in range(len(chunks))
    ]
    collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    return {"supplier_id": supplier_id, "filename": filename, "chunks": len(chunks)}


# Seed de demo: copia contratos del repo base
SEED_CONTRACTS = [
    ("contrato_proveedor_001.txt", "TechCorp SA",            "SUP001", 150000),
    ("contrato_proveedor_002.txt", "Papelería Norte SRL",    "SUP002", 30000),
    ("contrato_proveedor_004.txt", "Limpieza Total SRL",     "SUP004", 80000),
    ("contrato_proveedor_005.txt", "Consultoría Digital SA", "SUP005", 200000),
]


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def init_db():
    """Inicializa: si no hay nada, siembra contratos demo."""
    meta = load_meta()
    if meta["contracts"]:
        print(f"[contract-service] {len(meta['contracts'])} contratos ya cargados")
        return
    print("[contract-service] Sembrando contratos demo...")
    for fname, _name, sid, _limit in SEED_CONTRACTS:
        src = PROJECT_ROOT / "data" / "contracts" / fname
        dst = CONTRACTS_DIR / fname
        if src.exists():
            text = src.read_text(encoding="utf-8")
            dst.write_text(text, encoding="utf-8")
            try:
                ingest_contract(fname, text)
                meta["contracts"][sid] = {
                    "filename": fname,
                    "uploaded_at": "2026-06-28T00:00:00Z",
                }
            except Exception as e:
                print(f"[contract-service] WARN: no se pudo ingestar {fname}: {e}")
    save_meta(meta)


app = FastAPI(
    title="Contract Service",
    description="Microservicio de contratos + RAG",
    version="1.0.0",
    lifespan=lifespan,
)


# ----------------------------------------------------------------------
# Modelos
# ----------------------------------------------------------------------

class UploadResponse(BaseModel):
    supplier_id: str
    filename: str
    chunks: int
    message: str


class ContractInfo(BaseModel):
    supplier_id: str
    filename: str
    uploaded_at: str


class CheckResponse(BaseModel):
    supplier_id: str
    found: bool
    contract_limit: float
    within_limit: bool
    contract_fragment: str
    error: Optional[str] = None


# ----------------------------------------------------------------------
# RAG query
# ----------------------------------------------------------------------

def _parse_amount(text: str) -> Optional[float]:
    import re
    if not text:
        return None
    text = text.replace("\xa0", " ")
    prio = re.compile(
        r"(?:monto\s+m[áa]ximo|monto\s+autorizado|l[íi]mite\s+m[áa]ximo)"
        r"[^\d\$]{0,40}\$\s*([\d\.,]+)",
        re.IGNORECASE,
    )
    generic = re.compile(r"\$\s*([\d\.,]+)")

    candidates = []
    m = prio.search(text)
    if m:
        candidates.append(m.group(1))
    for gm in generic.finditer(text):
        candidates.append(gm.group(1))

    for raw in candidates:
        try:
            s = raw.strip()
            has_dot = "." in s
            has_comma = "," in s
            if has_dot and has_comma:
                if s.rfind(".") > s.rfind(","):
                    s = s.replace(",", "")
                else:
                    s = s.replace(".", "").replace(",", ".")
            elif has_comma:
                parts = s.split(",")
                if len(parts) == 2 and len(parts[1]) == 3:
                    s = s.replace(",", "")
                else:
                    s = s.replace(",", ".")
            elif has_dot:
                parts = s.split(".")
                if len(parts) == 2 and len(parts[1]) == 3:
                    s = s.replace(".", "")
            v = float(s)
            if v > 0:
                return v
        except (ValueError, TypeError):
            continue
    return None


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------

@app.get("/health")
def health():
    meta = load_meta()
    return {
        "service": "contract-service",
        "status": "ok",
        "contracts_loaded": len(meta["contracts"]),
        "chroma_path": str(CHROMA_DIR),
    }


@app.post("/contracts/upload", response_model=UploadResponse)
async def upload_contract(filename: str, content: str):
    """Sube un contrato (texto plano) y lo indexa en ChromaDB.

    Query params:
      - filename: nombre del archivo (ej: contrato_proveedor_006.txt)
      - content: cuerpo del contrato (en producción vendría como multipart)
    """
    if not filename.endswith(".txt"):
        raise HTTPException(400, "Solo se aceptan archivos .txt")
    if len(content) < 100:
        raise HTTPException(400, "Contrato demasiado corto (<100 chars)")

    # Guardar archivo
    dst = CONTRACTS_DIR / filename
    dst.write_text(content, encoding="utf-8")

    # Indexar
    result = ingest_contract(filename, content)

    # Actualizar metadata
    from datetime import datetime
    meta = load_meta()
    meta["contracts"][result["supplier_id"]] = {
        "filename": filename,
        "uploaded_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    save_meta(meta)

    return UploadResponse(
        supplier_id=result["supplier_id"],
        filename=result["filename"],
        chunks=result["chunks"],
        message=f"Contrato indexado correctamente",
    )


@app.get("/contracts", response_model=List[ContractInfo])
def list_contracts():
    meta = load_meta()
    return [
        ContractInfo(supplier_id=sid, **info)
        for sid, info in sorted(meta["contracts"].items())
    ]


@app.get("/contracts/{supplier_id}/check", response_model=CheckResponse)
def check_contract(supplier_id: str, amount: float = Query(...)):
    """Verifica si `amount` está dentro del límite contractual del proveedor."""
    sid = supplier_id.strip().upper()
    meta = load_meta()
    if sid not in meta["contracts"]:
        return CheckResponse(
            supplier_id=sid,
            found=False,
            contract_limit=0.0,
            within_limit=False,
            contract_fragment="",
            error="Proveedor no tiene contrato registrado",
        )

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        ef = GoogleGenAiEmbeddingFunction(
            model_name="models/gemini-embedding-001",
            task_type="RETRIEVAL_QUERY",
        )
        collection = client.get_collection(
            name=COLLECTION_NAME, embedding_function=ef
        )
        query = "monto maximo autorizado por factura limite economico condiciones"
        # Filtrar por supplier_id a nivel de ChromaDB (where clause)
        try:
            results = collection.query(
                query_texts=[query],
                n_results=3,
                where={"supplier_id": sid},
            )
        except Exception:
            results = collection.query(query_texts=[query], n_results=3)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        # Priorizar chunks del supplier correcto
        chosen_idx = next(
            (i for i, m in enumerate(metadatas) if m.get("supplier_id", "").upper() == sid),
            None,
        )
        if chosen_idx is None and documents:
            chosen_idx = 0
        if chosen_idx is None:
            return CheckResponse(
                supplier_id=sid, found=False, contract_limit=0.0,
                within_limit=False, contract_fragment="",
                error="No se encontraron chunks relevantes",
            )

        fragment = documents[chosen_idx]
        limit = _parse_amount(fragment) or 0.0
        return CheckResponse(
            supplier_id=sid,
            found=True,
            contract_limit=limit,
            within_limit=(limit > 0 and amount <= limit),
            contract_fragment=fragment[:500],
        )
    except Exception as e:
        return CheckResponse(
            supplier_id=sid, found=False, contract_limit=0.0,
            within_limit=False, contract_fragment="",
            error=f"Error en RAG: {e}",
        )


@app.post("/contracts/seed")
def seed():
    """Reset: borra y vuelve a sembrar contratos demo."""
    init_db()
    return {"seeded": len(SEED_CONTRACTS)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="info")