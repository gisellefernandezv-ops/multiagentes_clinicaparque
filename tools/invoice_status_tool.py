"""Tool de Consulta de Estado de Facturas — InvoiceFlow (Flujo B).

Permite a los proveedores consultar el estado de sus facturas ya enviadas.
Este es el Flujo B del sistema (consulta de estado), diferenciado del
Flujo A (alta de factura nueva).

Uso:
    from tools.invoice_status_tool import check_invoice_status_tool
    
    resultado = check_invoice_status_tool(
        invoice_id="FC-2026-SUP001-001",
        supplier_id="SUP001"
    )
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

# =============================================================================
# RUTAS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAYMENTS_DB = PROJECT_ROOT / "data" / "payments.db"

# =============================================================================
# MAPA DE ESTADOS
# =============================================================================

# Estados posibles en la base de datos
ESTADO_DISPLAY = {
    "PENDING": {
        "label": "Pendiente",
        "icon": "⏳",
        "descripcion": "La factura está siendo procesada por el sistema.",
        "color": "warning",
        "mostrar_cbu": False,
        "mostrar_fecha_pago": False,
        "mostrar_rechazo": False,
    },
    "PENDING_PAYMENT": {
        "label": "Aprobada - En espera de pago",
        "icon": "✅",
        "descripcion": "La factura fue aprobada y está en cola para pago.",
        "color": "success",
        "mostrar_cbu": False,
        "mostrar_fecha_pago": False,
        "mostrar_rechazo": False,
    },
    "PENDING_HUMAN_REVIEW": {
        "label": "En revisión manual",
        "icon": "⚠️",
        "descripcion": "La factura requiere revisión por parte del equipo de aprobación.",
        "color": "warning",
        "mostrar_cbu": False,
        "mostrar_fecha_pago": False,
        "mostrar_rechazo": False,
    },
    "PENDIENTE_TECNICO": {
        "label": "Procesando",
        "icon": "🔧",
        "descripcion": "Estamos procesando tu factura, te confirmaremos en breve.",
        "color": "info",
        "mostrar_cbu": False,
        "mostrar_fecha_pago": False,
        "mostrar_rechazo": False,
    },
    "APPROVED": {
        "label": "Aprobada",
        "icon": "✅",
        "descripcion": "La factura fue aprobada exitosamente.",
        "color": "success",
        "mostrar_cbu": False,
        "mostrar_fecha_pago": False,
        "mostrar_rechazo": False,
    },
    "REJECTED": {
        "label": "Rechazada",
        "icon": "❌",
        "descripcion": "La factura fue rechazada.",
        "color": "danger",
        "mostrar_cbu": False,
        "mostrar_fecha_pago": False,
        "mostrar_rechazo": True,
    },
    "ESCALATED": {
        "label": "Escalada a revisión",
        "icon": "⏫",
        "descripcion": "La factura fue escalada para revisión manual.",
        "color": "warning",
        "mostrar_cbu": False,
        "mostrar_fecha_pago": False,
        "mostrar_rechazo": False,
    },
    "PAID": {
        "label": "Pagada",
        "icon": "💰",
        "descripcion": "El pago fue realizado.",
        "color": "success",
        "mostrar_cbu": True,
        "mostrar_fecha_pago": True,
        "mostrar_rechazo": False,
    },
}

CBU_DEFAULT = "0170298440000001234567"  # CBU placeholder (en producción vendría de contrato)


def _ensure_db():
    """Asegura que la DB exista."""
    if not PAYMENTS_DB.exists():
        return False
    return True


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convierte una Row de SQLite a dict."""
    return dict(row)


# =============================================================================
# FUNCIÓN PRINCIPAL: Consultar estado de UNA factura
# =============================================================================


def check_invoice_status_tool(
    invoice_id: str,
    supplier_id: str | None = None,
) -> dict:
    """Consulta el estado de una factura específica.

    Args:
        invoice_id: ID de la factura a consultar.
        supplier_id: ID del proveedor (para seguridad, opcional pero recomendado).

    Returns:
        dict con:
            - found (bool): si se encontró la factura
            - invoice_id (str)
            - supplier_id (str)
            - amount (float)
            - decision (str)
            - payment_status (str)
            - rejection_reason (str | null)
            - registered_at (str)
            - confirmation_id (str)
            - display (dict): datos formateados para mostrar al usuario
            - error (str): mensaje de error si lo hubo
    """
    if not invoice_id:
        return {
            "found": False,
            "error": "invoice_id es obligatorio",
            "invoice_id": "",
            "supplier_id": "",
            "amount": 0.0,
            "decision": "",
            "payment_status": "",
            "rejection_reason": "",
            "registered_at": "",
            "confirmation_id": "",
            "display": {},
        }

    if not _ensure_db():
        return {
            "found": False,
            "error": "Base de datos no disponible",
            "invoice_id": invoice_id,
            "supplier_id": supplier_id or "",
            "amount": 0.0,
            "decision": "",
            "payment_status": "",
            "rejection_reason": "",
            "registered_at": "",
            "confirmation_id": "",
            "display": {},
        }

    try:
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM payments
                WHERE invoice_id = ?
                """,
                (invoice_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return {
                    "found": False,
                    "error": f"No se encontró la factura {invoice_id}",
                    "invoice_id": invoice_id,
                    "supplier_id": supplier_id or "",
                    "amount": 0.0,
                    "decision": "",
                    "payment_status": "",
                    "rejection_reason": "",
                    "registered_at": "",
                    "confirmation_id": "",
                    "display": {},
                }

            # Verificar que el supplier_id coincida (seguridad)
            if supplier_id and row["supplier_id"] != supplier_id:
                return {
                    "found": False,
                    "error": "No autorizado a consultar datos de otro proveedor",
                    "invoice_id": invoice_id,
                    "supplier_id": row["supplier_id"],
                    "amount": 0.0,
                    "decision": "",
                    "payment_status": "",
                    "rejection_reason": "",
                    "registered_at": "",
                    "confirmation_id": "",
                    "display": {},
                }

            data = _row_to_dict(row)
            payment_status = data.get("payment_status", "UNKNOWN")

            # Obtener info de display
            display_info = ESTADO_DISPLAY.get(
                payment_status,
                ESTADO_DISPLAY.get("PENDING", {
                    "label": payment_status,
                    "icon": "❓",
                    "descripcion": "Estado desconocido",
                    "color": "secondary",
                    "mostrar_cbu": False,
                    "mostrar_fecha_pago": False,
                    "mostrar_rechazo": False,
                })
            )

            return {
                "found": True,
                "error": "",
                "invoice_id": data["invoice_id"],
                "supplier_id": data["supplier_id"],
                "amount": float(data["amount"]),
                "decision": data.get("decision", ""),
                "payment_status": payment_status,
                "rejection_reason": data.get("rejection_reason") or None,
                "registered_at": data.get("registered_at", ""),
                "confirmation_id": data.get("confirmation_id", ""),
                "display": {
                    "label": display_info["label"],
                    "icon": display_info["icon"],
                    "descripcion": display_info["descripcion"],
                    "color": display_info["color"],
                    "mostrar_cbu": display_info["mostrar_cbu"],
                    "mostrar_fecha_pago": display_info["mostrar_fecha_pago"],
                    "mostrar_rechazo": display_info["mostrar_rechazo"],
                    # Agregar datos adicionales si corresponde
                    "cbu": CBU_DEFAULT if display_info["mostrar_cbu"] else None,
                    "rejection_reason": (
                        data.get("rejection_reason")
                        if display_info["mostrar_rechazo"]
                        else None
                    ),
                },
            }

    except Exception as e:
        return {
            "found": False,
            "error": f"Error consultando factura: {str(e)}",
            "invoice_id": invoice_id,
            "supplier_id": supplier_id or "",
            "amount": 0.0,
            "decision": "",
            "payment_status": "",
            "rejection_reason": "",
            "registered_at": "",
            "confirmation_id": "",
            "display": {},
        }


# =============================================================================
# FUNCIÓN: Listar facturas de un proveedor
# =============================================================================


def list_supplier_invoices_tool(
    supplier_id: str,
    limit: int = 50,
    status_filter: str | None = None,
) -> dict:
    """Lista todas las facturas de un proveedor.

    Args:
        supplier_id: ID del proveedor.
        limit: Cantidad máxima de resultados.
        status_filter: Filtrar por estado específico (opcional).

    Returns:
        dict con:
            - found (bool)
            - supplier_id (str)
            - invoices (list): lista de facturas
            - total (int): total de facturas
            - error (str)
    """
    if not supplier_id:
        return {
            "found": False,
            "error": "supplier_id es obligatorio",
            "supplier_id": "",
            "invoices": [],
            "total": 0,
        }

    if not _ensure_db():
        return {
            "found": False,
            "error": "Base de datos no disponible",
            "supplier_id": supplier_id,
            "invoices": [],
            "total": 0,
        }

    try:
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM payments WHERE supplier_id = ?"
            params: list = [supplier_id]

            if status_filter:
                query += " AND payment_status = ?"
                params.append(status_filter)

            query += " ORDER BY registered_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            invoices = []
            for row in rows:
                data = _row_to_dict(row)
                payment_status = data.get("payment_status", "UNKNOWN")
                display_info = ESTADO_DISPLAY.get(
                    payment_status,
                    {
                        "label": payment_status,
                        "icon": "❓",
                        "descripcion": "Estado desconocido",
                        "color": "secondary",
                    }
                )

                invoices.append({
                    "invoice_id": data["invoice_id"],
                    "amount": float(data["amount"]),
                    "decision": data.get("decision", ""),
                    "payment_status": payment_status,
                    "status_label": display_info["label"],
                    "status_icon": display_info["icon"],
                    "status_color": display_info["color"],
                    "rejection_reason": data.get("rejection_reason") or None,
                    "registered_at": data.get("registered_at", ""),
                    "confirmation_id": data.get("confirmation_id", ""),
                })

            return {
                "found": True,
                "error": "",
                "supplier_id": supplier_id,
                "invoices": invoices,
                "total": len(invoices),
            }

    except Exception as e:
        return {
            "found": False,
            "error": f"Error listando facturas: {str(e)}",
            "supplier_id": supplier_id,
            "invoices": [],
            "total": 0,
        }


# =============================================================================
# FUNCIÓN: Resumen de estados de un proveedor
# =============================================================================


def get_supplier_status_summary_tool(supplier_id: str) -> dict:
    """Obtiene el resumen de estados de facturas de un proveedor.

    Args:
        supplier_id: ID del proveedor.

    Returns:
        dict con conteos por estado:
            - supplier_id
            - total
            - pending
            - approved
            - rejected
            - escalated
            - paid
            - error
    """
    if not supplier_id:
        return {
            "error": "supplier_id es obligatorio",
            "supplier_id": "",
            "total": 0,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "escalated": 0,
            "paid": 0,
        }

    if not _ensure_db():
        return {
            "error": "Base de datos no disponible",
            "supplier_id": supplier_id,
            "total": 0,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "escalated": 0,
            "paid": 0,
        }

    try:
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN payment_status IN ('PENDING', 'PENDIENTE_TECNICO') THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN payment_status = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN payment_status = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN payment_status IN ('ESCALATED', 'PENDING_HUMAN_REVIEW') THEN 1 ELSE 0 END) as escalated,
                    SUM(CASE WHEN payment_status = 'PAID' THEN 1 ELSE 0 END) as paid
                FROM payments
                WHERE supplier_id = ?
                """,
                (supplier_id,),
            )
            row = cursor.fetchone()

            return {
                "error": "",
                "supplier_id": supplier_id,
                "total": row[0] or 0,
                "pending": row[1] or 0,
                "approved": row[2] or 0,
                "rejected": row[3] or 0,
                "escalated": row[4] or 0,
                "paid": row[5] or 0,
            }

    except Exception as e:
        return {
            "error": f"Error obteniendo resumen: {str(e)}",
            "supplier_id": supplier_id,
            "total": 0,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "escalated": 0,
            "paid": 0,
        }


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("INVOICE STATUS TOOL — TEST")
    print("=" * 60)

    # Test: Consulta de factura inexistente
    print("\n--- Test: Factura inexistente ---")
    result = check_invoice_status_tool("INV-NO-EXISTE", "SUP001")
    print(f"  Resultado: found={result['found']}, error={result['error']}")

    # Test: Resumen de proveedor
    print("\n--- Test: Resumen proveedor ---")
    result = get_supplier_status_summary_tool("SUP001")
    print(f"  Resultado: {result}")

    print("\n✓ Tests completados")
