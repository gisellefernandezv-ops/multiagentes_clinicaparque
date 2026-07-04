"""Supplier Service — microservicio de gestión de proveedores.

Puerto: 8001
DB: SQLite en data/suppliers.db

Endpoints:
- GET  /health
- GET  /suppliers
- GET  /suppliers/{supplier_id}
- POST /suppliers             (registrar nuevo)
- PUT  /suppliers/{id}/status (activar/desactivar)
- POST /suppliers/seed        (cargar datos demo)
"""
from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ----------------------------------------------------------------------
# Paths y DB
# ----------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "platform" / "data"
DB_PATH = DATA_DIR / "suppliers.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id   TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    cuit          TEXT NOT NULL,
    status        TEXT NOT NULL CHECK(status IN ('ACTIVE','INACTIVE','SUSPENDED')),
    category      TEXT,
    email         TEXT,
    phone         TEXT,
    registered_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_suppliers_status ON suppliers(status);
"""

SEED = [
    ("SUP001", "TechCorp SA",            "30-71234567-0", "ACTIVE",   "Servicios IT",                        "billing@techcorp.com.ar",  "+54-11-4000-0001", "2023-05-10"),
    ("SUP002", "Papelería Norte SRL",    "30-69874523-1", "ACTIVE",   "Insumos de oficina",                  "ventas@papelnorte.com.ar", "+54-11-4000-0002", "2022-11-22"),
    ("SUP003", "Servicios Rápidos SA",   "30-70111222-3", "INACTIVE", "Logística y mensajería",               "contacto@servrapidos.com", "+54-11-4000-0003", "2021-08-15"),
    ("SUP004", "Limpieza Total SRL",     "30-70555666-7", "ACTIVE",   "Servicios de limpieza",                "ops@limpiezatotal.com.ar", "+54-11-4000-0004", "2024-02-01"),
    ("SUP005", "Consultoría Digital SA", "30-71234999-2", "ACTIVE",   "Consultoría y transformación digital", "hello@condigital.com.ar",  "+54-11-4000-0005", "2024-06-30"),
]


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Idempotente: insertar solo si no existen
        for row in SEED:
            conn.execute(
                "INSERT OR IGNORE INTO suppliers VALUES (?,?,?,?,?,?,?,?)", row
            )
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"[supplier-service] DB inicializada en {DB_PATH}")
    yield


# ----------------------------------------------------------------------
# Modelos
# ----------------------------------------------------------------------

class Supplier(BaseModel):
    supplier_id: str
    name: str
    cuit: str
    status: str
    category: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    registered_at: str


class SupplierCreate(BaseModel):
    supplier_id: str = Field(..., pattern=r"^SUP\d{3,}$")
    name: str
    cuit: str
    status: str = "ACTIVE"
    category: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str  # ACTIVE | INACTIVE | SUSPENDED


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------

app = FastAPI(
    title="Supplier Service",
    description="Microservicio de gestión de proveedores",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"service": "supplier-service", "status": "ok", "db": str(DB_PATH)}


@app.get("/suppliers", response_model=List[Supplier])
def list_suppliers(status: Optional[str] = None):
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM suppliers WHERE status = ? ORDER BY supplier_id",
                (status.upper(),),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM suppliers ORDER BY supplier_id").fetchall()
    return [dict(r) for r in rows]


@app.get("/suppliers/{supplier_id}", response_model=Supplier)
def get_supplier(supplier_id: str):
    sid = supplier_id.strip().upper()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM suppliers WHERE supplier_id = ?", (sid,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, f"Proveedor {sid} no encontrado")
    return dict(row)


@app.post("/suppliers", response_model=Supplier, status_code=201)
def create_supplier(payload: SupplierCreate):
    sid = payload.supplier_id.strip().upper()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM suppliers WHERE supplier_id = ?", (sid,)
        ).fetchone()
        if existing:
            raise HTTPException(409, f"Proveedor {sid} ya existe")
        conn.execute(
            "INSERT INTO suppliers VALUES (?,?,?,?,?,?,?,?)",
            (
                sid,
                payload.name,
                payload.cuit,
                payload.status.upper(),
                payload.category,
                payload.email,
                payload.phone,
                datetime.utcnow().isoformat(timespec="seconds") + "Z",
            ),
        )
        conn.commit()
    return get_supplier(sid)


@app.put("/suppliers/{supplier_id}/status", response_model=Supplier)
def update_status(supplier_id: str, payload: StatusUpdate):
    sid = supplier_id.strip().upper()
    new_status = payload.status.upper()
    if new_status not in {"ACTIVE", "INACTIVE", "SUSPENDED"}:
        raise HTTPException(400, f"status inválido: {new_status}")
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE suppliers SET status = ? WHERE supplier_id = ?",
            (new_status, sid),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, f"Proveedor {sid} no encontrado")
    return get_supplier(sid)


@app.post("/suppliers/seed")
def seed():
    """Re-carga los datos demo (útil para reset)."""
    with get_conn() as conn:
        for row in SEED:
            conn.execute(
                "INSERT OR REPLACE INTO suppliers VALUES (?,?,?,?,?,?,?,?)", row
            )
        conn.commit()
    return {"seeded": len(SEED)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")