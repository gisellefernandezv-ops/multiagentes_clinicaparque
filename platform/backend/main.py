"""InvoiceFlow Backend — API principal.

Puertos:
  8000 — Backend (este) + UI estática
  8001 — Supplier service (microservicio)
  8002 — Contract service (microservicio)

Levanta:
  - API REST
  - File watcher del inbox (si enable_watcher=True)
  - Sirve el frontend estático
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Bootstrap: agregar raíz del proyecto para imports legacy (guardrails, etc.)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from .settings import settings
from .watcher import InboxWatcher
from .inbox_router import router as inbox_router
from .chat_router import router as chat_router
from .new_invoices_router import router as new_invoices_router
from .supplier_portal_router import router as supplier_portal_router


# Watcher global (lo iniciamos en lifespan)
watcher: InboxWatcher | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global watcher
    print(f"[backend] Iniciando InvoiceFlow backend en puerto {settings.port}")
    print(f"[backend] Frontend: {settings.frontend_dir}")
    print(f"[backend] Inbox:    {settings.inbox_dir}")
    print(f"[backend] Processed:{settings.processed_dir}")
    print(f"[backend] Supplier service URL: {settings.supplier_service_url}")
    print(f"[backend] Contract service URL: {settings.contract_service_url}")

    if settings.enable_watcher:
        watcher = InboxWatcher()
        watcher.start()
    yield

    if watcher:
        watcher.stop()


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


@app.get("/health")
def health():
    """Health check agregado."""
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


# Routers
app.include_router(inbox_router)
app.include_router(chat_router)
app.include_router(new_invoices_router)
app.include_router(supplier_portal_router)


# Frontend estático
if settings.frontend_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(settings.frontend_dir)),
        name="static",
    )

    @app.get("/")
    def root():
        return FileResponse(str(settings.frontend_dir / "index.html"))

# Supplier Portal estático
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
        "platform.backend.main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
        reload=False,
    )
