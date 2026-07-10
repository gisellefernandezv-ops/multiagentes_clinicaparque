"""Supplier Service — microservicio de gestion de proveedores + contratos.

Puerto: 8001
DB: SQLite en app/data/suppliers.db

Endpoints:
- GET    /health
- GET    /suppliers
- GET    /suppliers/{supplier_id}
- POST   /suppliers             (alta con contrato opcional)
- PUT    /suppliers/{id}        (modificar)
- DELETE /suppliers/{id}        (baja logica)
- PUT    /suppliers/{id}/status
- GET    /suppliers/{id}/contract
- POST   /suppliers/{id}/contract (asignar/reemplazar contrato)
- GET    /contracts             (listar todos los contratos)
- POST   /suppliers/seed        (datos demo)
"""
from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "app" / "data"
DB_PATH = DATA_DIR / "suppliers.db"
CONTRACTS_DIR = DATA_DIR / "contracts"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)


# FIX BUG-016: agregar tabla contracts
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
CREATE INDEX IF NOT EXISTS idx_suppliers_cuit ON suppliers(cuit);

CREATE TABLE IF NOT EXISTS contracts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id     TEXT NOT NULL,
    contract_limit  REAL NOT NULL,
    mode            TEXT NOT NULL CHECK(mode IN ('EXACTO','NO_SUPERAR')),
    start_date      TEXT,
    end_date        TEXT,
    file_path       TEXT,
    uploaded_at     TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_contracts_supplier ON contracts(supplier_id);
"""

SEED = [
    ("SUP001", "TechCorp SA",            "30-71234567-0", "ACTIVE",   "Servicios IT",                        "billing@techcorp.com.ar",  "+54-11-4000-0001", "2023-05-10"),
    ("SUP002", "Papeleria Norte SRL",    "30-69874523-1", "ACTIVE",   "Insumos de oficina",                  "ventas@papelnorte.com.ar", "+54-11-4000-0002", "2022-11-22"),
    ("SUP003", "Servicios Rapidos SA",   "30-70111222-3", "INACTIVE", "Logistica y mensajeria",               "contacto@servrapidos.com", "+54-11-4000-0003", "2021-08-15"),
    ("SUP004", "Limpieza Total SRL",     "30-70555666-7", "ACTIVE",   "Servicios de limpieza",                "ops@limpiezatotal.com.ar", "+54-11-4000-0004", "2024-02-01"),
    ("SUP005", "Consultoria Digital SA", "30-71234999-2", "ACTIVE",   "Consultoria y transformacion digital", "hello@condigital.com.ar",  "+54-11-4000-0005", "2024-06-30"),
]

# Contratos seed (mode NO_SUPERAR por default)
SEED_CONTRACTS = [
    # (supplier_id, limit, mode, start, end)
    ("SUP001", 150000, "NO_SUPERAR", "2025-01-15", "2026-01-14"),
    ("SUP002", 30000,  "NO_SUPERAR", "2024-01-01", "2025-12-31"),
    ("SUP004", 80000,  "NO_SUPERAR", "2024-02-01", "2026-12-31"),
    ("SUP005", 200000, "NO_SUPERAR", "2024-07-01", "2026-06-30"),
]


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        for row in SEED:
            conn.execute(
                "INSERT OR IGNORE INTO suppliers VALUES (?,?,?,?,?,?,?,?)", row
            )
        for sid, limit, mode, start, end in SEED_CONTRACTS:
            # Solo insertar si no existe contrato para ese supplier
            existing = conn.execute(
                "SELECT 1 FROM contracts WHERE supplier_id = ?", (sid,)
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO contracts (supplier_id, contract_limit, mode, start_date, end_date, uploaded_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (sid, limit, mode, start, end, datetime.utcnow().isoformat(timespec="seconds") + "Z"),
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
    """FIX BUG-016: schema de alta con contrato opcional."""
    supplier_id: Optional[str] = None  # Si None, se auto-genera
    name: str
    cuit: str = Field(..., description="CUIT formato XX-XXXXXXXX-X")
    status: str = "ACTIVE"
    category: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    # Contrato opcional en el alta
    contract: Optional["ContractCreate"] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    cuit: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str  # ACTIVE | INACTIVE | SUSPENDED


class Contract(BaseModel):
    id: int
    supplier_id: str
    contract_limit: float
    mode: str  # EXACTO | NO_SUPERAR
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    file_path: Optional[str] = None
    uploaded_at: str


class ContractCreate(BaseModel):
    """FIX BUG-016: contrato de proveedor con modo de validación."""
    contract_limit: float = Field(..., gt=0)
    mode: str = Field("NO_SUPERAR", pattern=r"^(EXACTO|NO_SUPERAR)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    file_name: Optional[str] = None  # nombre del archivo subido (opcional)


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------

app = FastAPI(
    title="Supplier Service",
    description="Microservicio de gestion de proveedores y contratos",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "service": "supplier-service",
        "status": "ok",
        "version": "2.0.0",
        "db": str(DB_PATH),
    }


# ----------------------------------------------------------------------
# SUPPLIERS - CRUD
# ----------------------------------------------------------------------

@app.get("/suppliers", response_model=List[Supplier])
def list_suppliers(
    status: Optional[str] = None,
    q: Optional[str] = None,  # busqueda por nombre o CUIT
):
    sql = "SELECT * FROM suppliers WHERE 1=1"
    params = []
    if status:
        sql += " AND status = ?"
        params.append(status.upper())
    if q:
        sql += " AND (name LIKE ? OR cuit LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    sql += " ORDER BY supplier_id"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
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
    """FIX BUG-016: Alta de proveedor con contrato opcional."""
    # Auto-generar ID si no se provee
    sid = (payload.supplier_id or "").strip().upper()
    if not sid:
        # Buscar siguiente ID disponible
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT supplier_id FROM suppliers ORDER BY supplier_id DESC LIMIT 1"
            ).fetchall()
            if rows:
                last = rows[0]["supplier_id"]
                # Extraer numero
                num = int(last.replace("SUP", "")) + 1
            else:
                num = 1
            sid = f"SUP{num:03d}"

    if not sid.startswith("SUP"):
        raise HTTPException(400, f"supplier_id debe empezar con SUP: {sid}")

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM suppliers WHERE supplier_id = ? OR cuit = ?", (sid, payload.cuit)
        ).fetchone()
        if existing:
            raise HTTPException(409, f"Proveedor {sid} o CUIT {payload.cuit} ya existe")

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

        # Si se envio contrato, crearlo
        if payload.contract:
            conn.execute(
                "INSERT INTO contracts (supplier_id, contract_limit, mode, start_date, end_date, file_path, uploaded_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    sid,
                    payload.contract.contract_limit,
                    payload.contract.mode,
                    payload.contract.start_date,
                    payload.contract.end_date,
                    payload.contract.file_name,
                    datetime.utcnow().isoformat(timespec="seconds") + "Z",
                ),
            )

        conn.commit()
    return get_supplier(sid)


@app.put("/suppliers/{supplier_id}", response_model=Supplier)
def update_supplier(supplier_id: str, payload: SupplierUpdate):
    sid = supplier_id.strip().upper()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT * FROM suppliers WHERE supplier_id = ?", (sid,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, f"Proveedor {sid} no encontrado")

        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            return dict(existing)
        if "status" in updates:
            updates["status"] = updates["status"].upper()
            if updates["status"] not in {"ACTIVE", "INACTIVE", "SUSPENDED"}:
                raise HTTPException(400, f"status invalido: {updates['status']}")

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        conn.execute(
            f"UPDATE suppliers SET {set_clause} WHERE supplier_id = ?",
            (*updates.values(), sid),
        )
        conn.commit()
    return get_supplier(sid)


@app.delete("/suppliers/{supplier_id}", response_model=Supplier)
def delete_supplier(supplier_id: str):
    """FIX BUG-016: Baja logica (status = INACTIVE)."""
    sid = supplier_id.strip().upper()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE suppliers SET status = 'INACTIVE' WHERE supplier_id = ?", (sid,)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, f"Proveedor {sid} no encontrado")
    return get_supplier(sid)


@app.put("/suppliers/{supplier_id}/status", response_model=Supplier)
def update_status(supplier_id: str, payload: StatusUpdate):
    """FIX BUG-016: Cambio rapido de estado (legacy)."""
    return update_supplier(supplier_id, SupplierUpdate(status=payload.status))


# ----------------------------------------------------------------------
# CONTRACTS
# ----------------------------------------------------------------------

@app.get("/suppliers/{supplier_id}/contract")
def get_contract(supplier_id: str):
    """FIX BUG-016: obtener el contrato activo de un proveedor."""
    sid = supplier_id.strip().upper()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM contracts WHERE supplier_id = ? ORDER BY id DESC LIMIT 1",
            (sid,),
        ).fetchone()
    if row is None:
        return {"supplier_id": sid, "found": False, "contract": None}
    return {
        "supplier_id": sid,
        "found": True,
        "contract": dict(row),
    }


@app.post("/suppliers/{supplier_id}/contract", response_model=Contract)
def upsert_contract(supplier_id: str, payload: ContractCreate):
    """FIX BUG-016: Asignar o reemplazar contrato de un proveedor."""
    sid = supplier_id.strip().upper()
    with get_conn() as conn:
        # Verificar que el proveedor existe
        sup = conn.execute("SELECT 1 FROM suppliers WHERE supplier_id = ?", (sid,)).fetchone()
        if not sup:
            raise HTTPException(404, f"Proveedor {sid} no encontrado")

        # Eliminar contratos previos (reemplazar)
        conn.execute("DELETE FROM contracts WHERE supplier_id = ?", (sid,))

        cur = conn.execute(
            "INSERT INTO contracts (supplier_id, contract_limit, mode, start_date, end_date, file_path, uploaded_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                sid,
                payload.contract_limit,
                payload.mode,
                payload.start_date,
                payload.end_date,
                payload.file_name,
                datetime.utcnow().isoformat(timespec="seconds") + "Z",
            ),
        )
        conn.commit()
        contract_id = cur.lastrowid

        row = conn.execute(
            "SELECT * FROM contracts WHERE id = ?", (contract_id,)
        ).fetchone()
    return dict(row)


@app.get("/contracts", response_model=List[Contract])
def list_contracts():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM contracts ORDER BY supplier_id").fetchall()
    return [dict(r) for r in rows]


# FIX BUG-016: endpoint de validacion de contrato contra factura
@app.get("/suppliers/{supplier_id}/check")
def check_contract_for_invoice(supplier_id: str, amount: float):
    """Valida un monto contra el contrato del proveedor.
    Devuelve contract_limit, mode, within_limit, found."""
    sid = supplier_id.strip().upper()
    with get_conn() as conn:
        sup = conn.execute("SELECT 1 FROM suppliers WHERE supplier_id = ?", (sid,)).fetchone()
        if not sup:
            return {"supplier_id": sid, "found": False, "error": f"Proveedor {sid} no existe"}
        contract = conn.execute(
            "SELECT * FROM contracts WHERE supplier_id = ? ORDER BY id DESC LIMIT 1",
            (sid,),
        ).fetchone()
    if not contract:
        return {
            "supplier_id": sid,
            "found": False,
            "error": f"Proveedor {sid} no tiene contrato registrado",
        }
    limit = float(contract["contract_limit"])
    mode = contract["mode"]
    # FIX BUG-016: validacion segun modo
    if mode == "EXACTO":
        within = abs(amount - limit) < 0.01
    else:  # NO_SUPERAR
        within = amount <= limit
    return {
        "supplier_id": sid,
        "found": True,
        "contract_limit": limit,
        "mode": mode,
        "within_limit": within,
        "contract_fragment": f"Contrato {mode}: límite ${limit:,.0f}",
    }


@app.post("/suppliers/seed")
def seed():
    with get_conn() as conn:
        for row in SEED:
            conn.execute(
                "INSERT OR REPLACE INTO suppliers VALUES (?,?,?,?,?,?,?,?)", row
            )
        conn.commit()
    return {"seeded": len(SEED)}


SupplierCreate.model_rebuild()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
