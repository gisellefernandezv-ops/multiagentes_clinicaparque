"""Tool para invocar al External Auditor vía A2A.

Cuando una factura se escala (> $500.000), el orquestador
llama a este tool para obtener el dictamen del auditor externo.
"""

import httpx
from typing import Optional, Dict, Any

EXTERNAL_AUDITOR_URL = "http://127.0.0.1:8003"


def call_external_auditor_tool(
    invoice_id: str,
    supplier_id: str,
    amount: float,
    invoice_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Invoca al External Auditor para auditar una factura escalada.

    Args:
        invoice_id: ID de la factura escalada.
        supplier_id: ID del proveedor.
        amount: Monto de la factura.
        invoice_data: Datos adicionales de la factura (opcional).

    Returns:
        Dict con el resultado de la auditoría:
        {
            "audit_id": "AUD-XXXXXXXX",
            "invoice_id": "<id>",
            "supplier_id": "<id>",
            "amount": <float>,
            "audit_result": "APPROVE" | "REJECT",
            "confidence": 0.0-1.0,
            "findings": [...],
            "summary": "...",
            "audited_at": "<timestamp>"
        }
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{EXTERNAL_AUDITOR_URL}/audit",
                json={
                    "invoice_id": invoice_id,
                    "supplier_id": supplier_id,
                    "amount": amount,
                    "invoice_data": invoice_data or {},
                },
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "audit_id": result.get("audit_id"),
                    "invoice_id": result.get("invoice_id"),
                    "supplier_id": result.get("supplier_id"),
                    "amount": result.get("amount"),
                    "audit_result": result.get("audit_result"),
                    "confidence": result.get("confidence"),
                    "findings": result.get("findings", []),
                    "summary": result.get("summary"),
                    "audited_at": result.get("audited_at"),
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "audit_result": "ERROR",
                }
                
    except httpx.ConnectError:
        return {
            "success": False,
            "error": "No se pudo conectar al External Auditor (puerto 8003)",
            "audit_result": "ERROR",
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Timeout esperando respuesta del External Auditor",
            "audit_result": "ERROR",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "audit_result": "ERROR",
        }


def request_audit_info_tool(
    invoice_id: str,
    info_needed: list[str],
) -> Dict[str, Any]:
    """Solicita información adicional para completar la auditoría.

    Args:
        invoice_id: ID de la factura.
        info_needed: Lista de información requerida.

    Returns:
        Dict con la solicitud de información.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{EXTERNAL_AUDITOR_URL}/audit/request-info",
                json={
                    "invoice_id": invoice_id,
                    "info_needed": info_needed,
                },
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "status": "INFO_REQUESTED",
                    "info_needed": info_needed,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("A2A TOOL TEST: Invocando External Auditor")
    print("=" * 60)
    
    result = call_external_auditor_tool(
        invoice_id="FC-2026-TEST-A2A",
        supplier_id="SUP001",
        amount=750000.0,
        invoice_data={
            "invoice_date": "2026-07-13",
            "currency": "ARS"
        }
    )
    
    print(f"\nSuccess: {result.get('success')}")
    if result.get('success'):
        print(f"Audit ID: {result.get('audit_id')}")
        print(f"Result: {result.get('audit_result')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"Summary: {result.get('summary')}")
        print(f"Findings: {len(result.get('findings', []))}")
    else:
        print(f"Error: {result.get('error')}")
    
    print("\n[Test completado]")
