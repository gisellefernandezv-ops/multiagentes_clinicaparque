"""Clientes HTTP para los microservicios."""
from __future__ import annotations

from typing import Optional

import httpx

from settings import settings


class SupplierClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.supplier_service_url

    def get_supplier(self, supplier_id: str) -> dict:
        try:
            r = httpx.get(
                f"{self.base_url}/suppliers/{supplier_id}",
                timeout=5.0,
            )
            if r.status_code == 200:
                return {"found": True, **r.json()}
            if r.status_code == 404:
                return {"found": False, "supplier_id": supplier_id,
                        "error": f"Proveedor {supplier_id} no encontrado"}
            return {"found": False, "supplier_id": supplier_id,
                    "error": f"supplier-service {r.status_code}: {r.text[:200]}"}
        except httpx.RequestError as e:
            return {"found": False, "supplier_id": supplier_id,
                    "error": f"supplier-service no responde: {e}"}

    def list_suppliers(self, status: Optional[str] = None) -> list:
        try:
            params = {"status": status} if status else None
            r = httpx.get(
                f"{self.base_url}/suppliers",
                params=params,
                timeout=5.0,
            )
            r.raise_for_status()
            return r.json()
        except httpx.RequestError:
            return []


class ContractClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.contract_service_url

    def check_contract(self, supplier_id: str, amount: float) -> dict:
        try:
            r = httpx.get(
                f"{self.base_url}/contracts/{supplier_id}/check",
                params={"amount": amount},
                timeout=10.0,
            )
            r.raise_for_status()
            return r.json()
        except httpx.RequestError as e:
            return {"found": False, "contract_limit": 0.0,
                    "within_limit": False, "contract_fragment": "",
                    "error": f"contract-service no responde: {e}"}

    def list_contracts(self) -> list:
        try:
            r = httpx.get(
                f"{self.base_url}/contracts",
                timeout=5.0,
            )
            r.raise_for_status()
            return r.json()
        except httpx.RequestError:
            return []


supplier_client = SupplierClient()
contract_client = ContractClient()