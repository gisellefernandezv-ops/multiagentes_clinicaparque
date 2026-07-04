"""Endpoints REST para gestión del inbox y facturas."""
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from settings import settings
from orchestrator import process_invoice
from watcher import parse_invoice_file, move_file


router = APIRouter(tags=["inbox"])


# ----------------------------------------------------------------------
# Modelos
# ----------------------------------------------------------------------

class InvoiceIn(BaseModel):
    invoice_id: str
    supplier_id: str
    supplier_name: Optional[str] = None
    amount: float
    currency: str = "ARS"
    invoice_date: str  # YYYY-MM-DD


class InvoiceResult(BaseModel):
    decision: str
    invoice_id: str
    supplier_id: str
    amount: float
    rejection_reason: str
    confirmation_id: str
    payment_status: str
    guardrail_action: str
    guardrail_reason: str
    validation: dict = {}
    contract: dict = {}


class InboxItem(BaseModel):
    filename: str
    size: int
    invoice_id: Optional[str] = None
    supplier_id: Optional[str] = None
    amount: Optional[str] = None


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------

@router.get("/inbox", response_model=List[InboxItem])
def list_inbox():
    """Lista las facturas en el inbox (aún no procesadas)."""
    items = []
    for f in sorted(settings.inbox_dir.glob("*")):
        if not f.is_file() or f.suffix.lower() not in {".json", ".txt"}:
            continue
        try:
            invoice = parse_invoice_file(f)
            items.append(InboxItem(
                filename=f.name,
                size=f.stat().st_size,
                invoice_id=(invoice or {}).get("invoice_id"),
                supplier_id=(invoice or {}).get("supplier_id"),
                amount=str((invoice or {}).get("amount", "")),
            ))
        except Exception:
            items.append(InboxItem(filename=f.name, size=f.stat().st_size))
    return items


@router.post("/inbox/upload")
async def upload_invoice(file: UploadFile = File(...)):
    """Sube una factura al inbox (multipart)."""
    if not file.filename:
        raise HTTPException(400, "filename vacío")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".json", ".txt"}:
        raise HTTPException(400, f"Solo se aceptan .json o .txt (recibido: {suffix})")
    dst = settings.inbox_dir / file.filename
    content = await file.read()
    dst.write_bytes(content)
    return {
        "filename": file.filename,
        "size": len(content),
        "inbox_path": str(dst),
        "message": "Factura subida al inbox. Procesala con /inbox/process/<filename> o vía chat.",
    }


@router.post("/inbox/process/{filename}", response_model=InvoiceResult)
def process_inbox_file(filename: str):
    """Procesa una factura específica del inbox."""
    path = settings.inbox_dir / filename
    if not path.exists():
        raise HTTPException(404, f"Archivo no encontrado: {filename}")
    invoice = parse_invoice_file(path)
    if not invoice:
        new_path = move_file(path, settings.rejected_dir)
        raise HTTPException(400, f"No se pudo parsear {filename}. Movido a {new_path}")

    result = process_invoice(invoice, source_file=str(path))
    if result.get("decision") in {"APPROVED", "REJECTED", "ESCALATED"}:
        new_path = move_file(path, settings.processed_dir)
        result["moved_to"] = str(new_path)
    return result


@router.post("/inbox/process-all")
def process_all_inbox():
    """Procesa todas las facturas del inbox."""
    files = [
        f for f in sorted(settings.inbox_dir.glob("*"))
        if f.is_file() and f.suffix.lower() in {".json", ".txt"}
    ]
    if not files:
        return {"processed": 0, "results": [], "message": "Inbox vacío"}

    results = []
    for f in files:
        invoice = parse_invoice_file(f)
        if not invoice:
            new_path = move_file(f, settings.rejected_dir)
            results.append({"filename": f.name, "error": "parse failed",
                            "moved_to": str(new_path)})
            continue
        try:
            r = process_invoice(invoice, source_file=str(f))
            r["filename"] = f.name
            new_path = move_file(f, settings.processed_dir)
            r["moved_to"] = str(new_path)
            results.append(r)
        except Exception as e:
            new_path = move_file(f, settings.rejected_dir)
            results.append({"filename": f.name, "error": str(e),
                            "moved_to": str(new_path)})

    return {"processed": len(results), "results": results}


@router.post("/invoices", response_model=InvoiceResult)
def submit_invoice(invoice: InvoiceIn):
    """Procesa una factura directamente (sin pasar por el inbox)."""
    invoice_dict = invoice.model_dump()
    result = process_invoice(invoice_dict, source_file=None)
    return result


@router.get("/invoices")
def list_processed_invoices(limit: int = 50, decision: Optional[str] = None):
    """Lista facturas procesadas (de la DB de pagos)."""
    if not settings.payments_db.exists():
        return []
    with sqlite3.connect(str(settings.payments_db)) as conn:
        conn.row_factory = sqlite3.Row
        if decision:
            rows = conn.execute(
                "SELECT * FROM payments WHERE decision = ? "
                "ORDER BY id DESC LIMIT ?",
                (decision.upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM payments ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


@router.get("/dashboard")
def dashboard_stats():
    """Estadísticas para el dashboard."""
    stats = {
        "inbox_count": 0,
        "processed_count": 0,
        "rejected_files": 0,
        "decisions": {"APPROVED": 0, "REJECTED": 0, "ESCALATED": 0},
        "total_amount_approved": 0.0,
        "recent": [],
    }
    # Inbox
    stats["inbox_count"] = sum(
        1 for f in settings.inbox_dir.glob("*")
        if f.is_file() and f.suffix.lower() in {".json", ".txt"}
    )
    # Processed/Rejected
    stats["processed_count"] = sum(
        1 for f in settings.processed_dir.glob("*") if f.is_file()
    )
    stats["rejected_files"] = sum(
        1 for f in settings.rejected_dir.glob("*") if f.is_file()
    )

    # Pagos DB
    if settings.payments_db.exists():
        with sqlite3.connect(str(settings.payments_db)) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(
                "SELECT decision, COUNT(*) as n, SUM(amount) as total "
                "FROM payments GROUP BY decision"
            ).fetchall():
                d = row["decision"]
                if d in stats["decisions"]:
                    stats["decisions"][d] = row["n"]
                if d == "APPROVED":
                    stats["total_amount_approved"] = row["total"] or 0
            stats["recent"] = [
                dict(r) for r in conn.execute(
                    "SELECT invoice_id, supplier_id, amount, decision, "
                    "payment_status, registered_at FROM payments "
                    "ORDER BY id DESC LIMIT 10"
                ).fetchall()
            ]
    return stats