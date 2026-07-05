"""Servidor A2A — External Auditor Agent.

Este servidor expone el agente auditor externo para comunicación
con el sistema principal vía protocolo A2A.

Puerto: 8003

Endpoints:
- POST /audit — Realizar auditoría de factura
- GET /health — Health check
- GET / — Info del agente
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from agent import perform_audit_tool, request_additional_info_tool

# =============================================================================
# APP
# =============================================================================

app = FastAPI(
    title="InvoiceFlow External Auditor",
    description="Agente auditor externo para revisión de facturas escaladas",
    version="1.0.0",
)

# =============================================================================
# SCHEMAS
# =============================================================================


class AuditRequest(BaseModel):
    """Request para iniciar una auditoría."""
    invoice_id: str
    supplier_id: str
    amount: float
    invoice_data: Optional[dict] = None


class AdditionalInfoRequest(BaseModel):
    """Request para solicitar información adicional."""
    invoice_id: str
    info_needed: list[str]


# =============================================================================
# ENDPOINTS
# =============================================================================


@app.get("/")
def root():
    """Info del agente."""
    return {
        "agent": "external_auditor_agent",
        "description": "Auditor externo especializado en facturas escaladas",
        "version": "1.0.0",
        "endpoints": {
            "POST /audit": "Realizar auditoría de factura",
            "POST /audit/request-info": "Solicitar información adicional",
            "GET /health": "Health check",
        },
    }


@app.get("/health")
def health():
    """Health check."""
    return {
        "service": "external-auditor",
        "status": "ok",
        "version": "1.0.0",
    }


@app.post("/audit")
def audit(request: AuditRequest):
    """Realiza una auditoría de factura escalada.

    El sistema principal llama a este endpoint cuando una factura
    requiere revisión por parte del auditor externo.
    """
    try:
        result = perform_audit_tool(
            invoice_id=request.invoice_id,
            supplier_id=request.supplier_id,
            amount=request.amount,
            invoice_data=request.invoice_data,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/request-info")
def request_info(request: AdditionalInfoRequest):
    """Solicita información adicional para la auditoría."""
    try:
        result = request_additional_info_tool(
            invoice_id=request.invoice_id,
            info_needed=request.info_needed,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8003,
        log_level="info",
        reload=False,
    )
