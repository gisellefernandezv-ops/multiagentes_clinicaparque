"""InvoiceFlow Backend - API principal.

Puertos:
  8000 - Backend (este) + UI estatica
  8001 - Supplier service (microservicio)
  8002 - Contract service (microservicio)

Levanta:
  - API REST
  - File watcher del inbox (si enable_watcher=True)
  - Sirve el frontend estatico
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Bootstrap: agregar raz del proyecto para imports legacy (guardrails, etc.)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from .settings import settings
from .watcher import InboxWatcher, parse_invoice_file, move_file
from .orchestrator import process_invoice
from .inbox_router import router as inbox_router
from .chat_router import router as chat_router
from .new_invoices_router import router as new_invoices_router
from .supplier_portal_router import router as supplier_portal_router
from .health_extended import get_full_observability
from .logger import setup_logging, get_logger

# Configurar logging centralizado
logger = setup_logging(PROJECT_ROOT)


# Watcher global (lo iniciamos en lifespan)
watcher: InboxWatcher | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global watcher
    logger.info(f"Iniciando InvoiceFlow backend en puerto {settings.port}")
    logger.info(f"Frontend: {settings.frontend_dir}")
    logger.info(f"Inbox: {settings.inbox_dir}")
    logger.info(f"Processed: {settings.processed_dir}")
    logger.info(f"Supplier service URL: {settings.supplier_service_url}")
    logger.info(f"Contract service URL: {settings.contract_service_url}")
    logger.info("Watcher habilitado" if settings.enable_watcher else "Watcher deshabilitado")

    if settings.enable_watcher:
        def auto_process_invoice(path: Path):
            """Procesa automaticamente una factura nueva en el inbox."""
            logger.info(f"[watcher] Procesando archivo: {path.name}")
            try:
                invoice = parse_invoice_file(path)
                if not invoice:
                    logger.warning(f"[watcher] No se pudo parsear {path.name}, moviendo a rejected/")
                    move_file(path, settings.rejected_dir)
                    return
                
                result = process_invoice(invoice, source_file=str(path))
                decision = result.get("decision", "UNKNOWN")
                
                if decision in {"APPROVED", "REJECTED", "ESCALATED"}:
                    move_file(path, settings.processed_dir)
                    logger.info(f"[watcher] Procesada: {path.name} -> {decision}")
                else:
                    logger.warning(f"[watcher] Decision desconocida: {decision} para {path.name}")
                    
            except Exception as e:
                logger.error(f"[watcher] Error procesando {path.name}: {e}")
                move_file(path, settings.rejected_dir)
        
        watcher = InboxWatcher(on_new_file=auto_process_invoice)
        watcher.start()
        logger.info("[watcher] File watcher iniciado")
    yield

    if watcher:
        watcher.stop()
        logger.info("[watcher] File watcher detenido")


app = FastAPI(
    title="InvoiceFlow API",
    description="Backend principal del producto InvoiceFlow",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# FIX BUG-008: middleware para evitar cache del browser en assets estaticos
class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    """Fuerza no-cache en /static/, /supplier/, /tests/ y en rutas de HTML.

    Tambien aplica no-cache a:
    - `/` (index.html del BackOffice)
    - `/supplier` (root del Supplier Portal)
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        # Assets estaticos siempre re-descargar
        if path.startswith(("/static/", "/supplier/", "/tests/")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        # HTML root siempre re-descargar (para que cargue nuevo script tag)
        elif path in ("/", "/supplier", "/supplier/", "/index.html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheStaticMiddleware)


# FIX BUG-011: endpoint proxy para que el browser NO haga fetch cross-origin
# a 8001/8002/8003 (que no tienen CORS). El backend agrega todo.
@app.get("/agents/health")
async def agents_health():
    """Health check agregado de TODOS los servicios (proxy same-origin).

    El browser hace fetch a este endpoint (mismo origen: :8000) y el backend
    consulta los microservicios internamente. Evita problemas de CORS.

    Divide los servicios en:
    - SERVICIOS CRITICOS: InvoiceFlow Backend, Supplier Service (validacion de proveedores), Contract Service (RAG)
    - SERVICIOS SECUNDARIOS: External Auditor (auditoria A2A)
    """
    import httpx

    # Servicios criticos - son necesarios para el funcionamiento del sistema
    critical_services = [
        ("invoiceflow-backend", f"http://127.0.0.1:{settings.port}/health"),
        ("supplier-service",   f"{settings.supplier_service_url}/health"),
        ("contract-service",    f"{settings.contract_service_url}/health"),
    ]

    # Servicios secundarios - opcionales para auditoria extendida
    secondary_services = [
        ("external-auditor",   "http://127.0.0.1:8003/health"),
    ]

    async def check_service(name: str, url: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "ok": True,
                        "status": data.get("status", "unknown"),
                        "url": url,
                        "details": {k: v for k, v in data.items() if k not in ("status", "service")},
                    }
                else:
                    return {"ok": False, "status": "down", "url": url, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"ok": False, "status": "down", "url": url, "error": str(e)}

    results = {}
    for name, url in critical_services:
        results[name] = await check_service(name, url)
    for name, url in secondary_services:
        results[name] = await check_service(name, url)

    # Verificar estado general
    critical_ok = all(results[name]["ok"] for name, _ in critical_services)
    all_ok = all(results[name]["ok"] for name, _ in critical_services + secondary_services)

    return {
        "status": "ok" if critical_ok else "degraded",
        "all_services_ok": all_ok,
        "critical_services": {name: results[name] for name, _ in critical_services},
        "secondary_services": {name: results[name] for name, _ in secondary_services},
    }


# FIX BUG-016: proxy endpoints para ABM de proveedores
# El browser NO debe hacer fetch cross-origin a 8001 (sin CORS).
# El backend hace de proxy same-origin.
import httpx

@app.get("/suppliers/proxy-list")
async def suppliers_proxy_list(status: str = None, q: str = None):
    """FIX BUG-016: lista de proveedores (proxy a supplier-service:8001)."""
    params = {}
    if status: params["status"] = status
    if q: params["q"] = q
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{settings.supplier_service_url}/suppliers", params=params)
    return r.json()


@app.get("/suppliers/proxy-contracts")
async def suppliers_proxy_contracts():
    """FIX BUG-016: lista de contratos (proxy a supplier-service:8001)."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{settings.supplier_service_url}/contracts")
    return r.json()


@app.post("/suppliers/proxy-create")
async def suppliers_proxy_create(payload: dict):
    """FIX BUG-016: crear proveedor con contrato (proxy)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            f"{settings.supplier_service_url}/suppliers",
            json=payload,
        )
        if r.status_code >= 400:
            from fastapi import HTTPException
            raise HTTPException(r.status_code, r.text)
        return r.json()


@app.put("/suppliers/proxy-update/{supplier_id}")
async def suppliers_proxy_update(supplier_id: str, payload: dict):
    """FIX BUG-016: modificar proveedor + contrato (proxy)."""
    # FIX BUG-018: ambos calls deben estar dentro del mismo async with
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Actualizar datos del proveedor (sin el campo contract, sin supplier_id)
        supplier_data = {k: v for k, v in payload.items() if k not in ("contract", "supplier_id")}
        r = await client.put(
            f"{settings.supplier_service_url}/suppliers/{supplier_id}",
            json=supplier_data,
        )
        if r.status_code >= 400:
            from fastapi import HTTPException
            raise HTTPException(r.status_code, r.text)
        # 2. Si se envio contrato, actualizarlo
        if "contract" in payload and payload["contract"]:
            rc = await client.post(
                f"{settings.supplier_service_url}/suppliers/{supplier_id}/contract",
                json=payload["contract"],
            )
            if rc.status_code >= 400:
                from fastapi import HTTPException
                raise HTTPException(rc.status_code, rc.text)
    return {"ok": True}


@app.delete("/suppliers/proxy-delete/{supplier_id}")
async def suppliers_proxy_delete(supplier_id: str):
    """FIX BUG-016: baja logica de proveedor (proxy)."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.delete(f"{settings.supplier_service_url}/suppliers/{supplier_id}")
    return r.json()


@app.get("/health")
def health():
    """Health check basico."""
    import httpx
    services = {}
    for name, url in [
        ("supplier-service", settings.supplier_service_url),
        ("contract-service", settings.contract_service_url),
    ]:
        try:
            r = httpx.get(f"{url}/health", timeout=2.0)
            services[name] = r.json() if r.status_code == 200 else {"status": "down"}
        except Exception as e:
            services[name] = {"status": "down", "error": str(e)}

    return {
        "service": "invoiceflow-backend",
        "status": "ok",
        "version": "1.0.0",
        "watcher_enabled": settings.enable_watcher,
        "microservices": services,
        "paths": {
            "inbox": str(settings.inbox_dir),
            "processed": str(settings.processed_dir),
            "rejected": str(settings.rejected_dir),
        },
    }


@app.get("/health/observability")
async def health_observability():
    """Health check completo con observabilidad del sistema.
    
    Incluye:
    - Estado de todos los servicios (backend, supplier, contract, MCP Toolbox)
    - Estado de bases de datos (SQLite: suppliers, payments, chat_sessions)
    - Estado de integraciones (RAG/ChromaDB, File Watcher)
    - Tracking de logs recientes
    - Metricas de archivos (inbox, processed, rejected)
    """
    try:
        return await get_full_observability(settings, PROJECT_ROOT)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/logs/recent")
async def logs_recent(lines: int = 100):
    """Endpoint para obtener logs recientes del sistema."""
    from .health_extended import get_recent_logs
    return get_recent_logs(PROJECT_ROOT, lines)


# Routers
app.include_router(inbox_router)
app.include_router(chat_router)
app.include_router(new_invoices_router)
app.include_router(supplier_portal_router)


# Frontend estatico
if settings.frontend_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(settings.frontend_dir)),
        name="static",
    )

    @app.get("/")
    def root():
        return FileResponse(str(settings.frontend_dir / "index.html"))

# FIX BUG-006: montar tests/eval/datasets para que el frontend pueda cargar el dataset
EVAL_DATASETS_DIR = PROJECT_ROOT / "tests" / "eval" / "datasets"
if EVAL_DATASETS_DIR.exists():
    app.mount(
        "/tests/eval/datasets",
        StaticFiles(directory=str(EVAL_DATASETS_DIR)),
        name="eval_datasets",
    )

# Supplier Portal estatico
SUPPLIER_PORTAL_DIR = PROJECT_ROOT / "supplier_portal"
if SUPPLIER_PORTAL_DIR.exists():
    app.mount(
        "/supplier",
        StaticFiles(directory=str(SUPPLIER_PORTAL_DIR), html=True),
        name="supplier_static",
    )

    @app.get("/supplier")
    @app.get("/supplier/")
    def supplier_portal_root():
        return FileResponse(str(SUPPLIER_PORTAL_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.backend.main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
        reload=False,
    )
