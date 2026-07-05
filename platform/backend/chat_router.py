"""Chat-driven: el usuario le indica al sistema qué factura procesar.

Patrones que entiende:
  - "procesá /inbox/INV-XXX.json"
  - "procesá la factura INV-XXX"
  - "procesá todo el inbox"
  - "procesá todas las facturas pendientes"
  - "lista las facturas del inbox"
  - "qué facturas hay pendientes?"
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .settings import settings
from .orchestrator import process_invoice
from .watcher import parse_invoice_file, move_file


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    intent: str
    message: str
    data: Optional[dict] = None


# ----------------------------------------------------------------------
# Parser de intents (rule-based; en prod usaría LLM)
# ----------------------------------------------------------------------

INTENT_RE = [
    (re.compile(r"(proces[áa]|aprueb[áa]|revis[áa]).*(todo|Todas|all|inbox)", re.I),
     "process_all"),
    (re.compile(r"(proces[áa]|aprueb[áa]).*(?:la\s+)?(?:factura\s+)?([A-Z]{2,}-?\d+)", re.I),
     "process_one"),
    (re.compile(r"([\/\\]inbox[\/\\][^\s]+\.(?:json|txt))", re.I),
     "process_path"),
    (re.compile(r"(list|qu[ée]\s+hay|pendientes|inbox)", re.I),
     "list_inbox"),
    (re.compile(r"(historial|pagos|procesad[ao]s)", re.I),
     "history"),
]


def parse_intent(message: str) -> tuple[str, Optional[str]]:
    """Devuelve (intent, param)."""
    for pat, intent in INTENT_RE:
        m = pat.search(message)
        if m:
            param = m.group(1) if m.groups() else None
            return intent, param
    return "unknown", None


# ----------------------------------------------------------------------
# Handlers por intent
# ----------------------------------------------------------------------

def handle_process_all() -> dict:
    files = sorted(settings.inbox_dir.glob("*"))
    files = [f for f in files if f.is_file() and f.suffix.lower() in {".json", ".txt"}]
    results = []
    for f in files:
        results.append(_process_single_file(f))
    return {
        "intent": "process_all",
        "message": f"Procesadas {len(results)} facturas del inbox.",
        "data": {"results": results},
    }


def handle_process_one(invoice_id: str) -> dict:
    # Buscar archivo por invoice_id en nombre
    candidates = list(settings.inbox_dir.glob(f"*{invoice_id}*"))
    if not candidates:
        return {
            "intent": "process_one",
            "message": f"No encontré ninguna factura con ID {invoice_id} en el inbox.",
            "data": {"found": False, "invoice_id": invoice_id},
        }
    results = [_process_single_file(f) for f in candidates]
    return {
        "intent": "process_one",
        "message": f"Procesada factura {invoice_id}",
        "data": {"results": results},
    }


def handle_process_path(path_str: str) -> dict:
    # Limpiar path (puede tener comillas o caracteres extra)
    path_str = path_str.strip().strip('"').strip("'")
    path = Path(path_str)
    if not path.exists():
        # Intentar relativo al inbox
        alt = settings.inbox_dir / path.name
        if alt.exists():
            path = alt
        else:
            return {
                "intent": "process_path",
                "message": f"No encontré el archivo: {path_str}",
                "data": {"found": False, "path": path_str},
            }
    result = _process_single_file(path)
    return {
        "intent": "process_path",
        "message": f"Procesado {path.name}",
        "data": {"results": [result]},
    }


def handle_list_inbox() -> dict:
    files = sorted(settings.inbox_dir.glob("*"))
    files = [f for f in files if f.is_file() and f.suffix.lower() in {".json", ".txt"}]
    items = []
    for f in files:
        try:
            invoice = parse_invoice_file(f)
            items.append({
                "filename": f.name,
                "size": f.stat().st_size,
                "invoice_id": (invoice or {}).get("invoice_id", "?"),
                "supplier_id": (invoice or {}).get("supplier_id", "?"),
                "amount": (invoice or {}).get("amount", "?"),
            })
        except Exception:
            items.append({"filename": f.name, "size": f.stat().st_size, "error": True})
    return {
        "intent": "list_inbox",
        "message": f"{len(items)} factura(s) en el inbox.",
        "data": {"items": items},
    }


def handle_history() -> dict:
    import sqlite3
    if not settings.payments_db.exists():
        return {"intent": "history", "message": "Sin historial aún.", "data": {"items": []}}
    with sqlite3.connect(str(settings.payments_db)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM payments ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return {
        "intent": "history",
        "message": f"{len(rows)} pago(s) registrado(s).",
        "data": {"items": [dict(r) for r in rows]},
    }


# ----------------------------------------------------------------------
# Procesamiento de archivo individual
# ----------------------------------------------------------------------

def _process_single_file(path: Path) -> dict:
    invoice = parse_invoice_file(path)
    if not invoice:
        # Mover a rejected
        new_path = move_file(path, settings.rejected_dir)
        return {
            "filename": path.name,
            "error": "No se pudo parsear el archivo",
            "moved_to": str(new_path),
        }
    try:
        result = process_invoice(invoice, source_file=str(path))
        result["filename"] = path.name
        # Mover a processed si fue decisión final correcta
        if result.get("decision") in {"APPROVED", "REJECTED", "ESCALATED"}:
            new_path = move_file(path, settings.processed_dir)
            result["moved_to"] = str(new_path)
        return result
    except Exception as e:
        new_path = move_file(path, settings.rejected_dir)
        return {
            "filename": path.name,
            "error": f"Error procesando: {e}",
            "moved_to": str(new_path),
        }


# ----------------------------------------------------------------------
# Endpoint
# ----------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
def chat(msg: ChatMessage):
    intent, param = parse_intent(msg.message)
    handlers = {
        "process_all": handle_process_all,
        "process_one": lambda: handle_process_one(param),
        "process_path": lambda: handle_process_path(param),
        "list_inbox": handle_list_inbox,
        "history": handle_history,
    }
    handler = handlers.get(intent)
    if handler is None:
        return ChatResponse(
            intent="unknown",
            message=(
                "No entendí la instrucción. Probá con:\n"
                "  • 'procesá todo el inbox'\n"
                "  • 'procesá la factura INV-001'\n"
                "  • 'procesá /inbox/INV-001.json'\n"
                "  • 'qué facturas hay en el inbox?'\n"
                "  • 'mostrame el historial de pagos'"
            ),
        )
    return ChatResponse(**handler())
