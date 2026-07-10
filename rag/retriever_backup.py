"""Retriever semantico MOCK para pruebas sin ChromaDB.

Este modulo proporciona la misma interfaz que retriever.py pero sin usar ChromaDB.
Usa los archivos de contrato directamente y extrae el monto maximo por regex.

Para activar este modo, configura MOCK_RAG=true en .env
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Si MOCK_RAG esta enabled, usar este modulo
USE_MOCK = os.getenv("MOCK_RAG", "true").lower() == "true"

# Limites contractuales por proveedor (extraidos de los contratos)
CONTRACT_LIMITS = {
    "SUP001": 150000.0,  # contrato_proveedor_001.txt
    "SUP002": 30000.0,   # contrato_proveedor_002.txt
    "SUP004": 80000.0,   # contrato_proveedor_004.txt
    "SUP005": 200000.0,  # contrato_proveedor_005.txt
}

# Fragmentos de contratos para mostrar en el resultado
CONTRACT_FRAGMENTS = {
    "SUP001": "CONTRATO DE SERVICIOS PROFESIONALES... El monto maximo autorizado por factura es de $150,000 (ciento cincuenta mil pesos)...",  # noqa
    "SUP002": "CONTRATO DE SUMINISTROS... El limite maximo por operacion es de $30,000 (treinta mil pesos)...",  # noqa
    "SUP004": "CONTRATO DE SERVICIOS... El monto maximo autorizado por factura es de $80,000 (ochenta mil pesos)...",  # noqa
    "SUP005": "CONTRATO DE CONSULTORIA... El limite maximo de facturacion mensual es de $200,000 (doscientos mil pesos)...",  # noqa
}


def _parse_amount(text: str) -> Optional[float]:
    """Extrae un monto numerico de un string con formato '$150.000' o '$150,000.00'."""
    if not text:
        return None
    
    text_clean = text.replace("\xa0", " ")
    
    # Patrones de monto
    priority_pattern = re.compile(
        r"(?:monto\s+maximo|monto\s+autorizado|limite\s+maximo|maximo\s+autorizado)"
        r"[^\d\$]{0,40}"
        r"\$\s*([\d\.,]+)",
        re.IGNORECASE,
    )
    m = priority_pattern.search(text_clean)
    candidates = []
    if m:
        candidates.append(m.group(1))
    
    # Cualquier "$ numero" como fallback
    generic_pattern = re.compile(r"\$\s*([\d\.,]+)")
    for gm in generic_pattern.finditer(text_clean):
        candidates.append(gm.group(1))
    
    for raw in candidates:
        try:
            value = _normalize_number(raw)
            if value and value > 0:
                return value
        except (ValueError, TypeError):
            continue
    
    return None


def _normalize_number(raw: str) -> float:
    """Normaliza '150.000' / '150,000' / '150,000.50' a float."""
    s = raw.strip()
    
    has_dot = "." in s
    has_comma = "," in s
    
    if has_dot and has_comma:
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    elif has_comma:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    elif has_dot:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(".", "")
    
    return float(s)


def _get_contract_text(supplier_id: str) -> Optional[str]:
    """Lee el archivo de contrato para un proveedor."""
    contracts_dir = PROJECT_ROOT / "data" / "contracts"
    
    # Mapear supplier_id a archivo
    mapping = {
        "SUP001": "contrato_proveedor_001.txt",
        "SUP002": "contrato_proveedor_002.txt",
        "SUP004": "contrato_proveedor_004.txt",
        "SUP005": "contrato_proveedor_005.txt",
    }
    
    filename = mapping.get(supplier_id.upper())
    if not filename:
        return None
    
    filepath = contracts_dir / filename
    if not filepath.exists():
        return None
    
    try:
        return filepath.read_text(encoding="utf-8")
    except Exception:
        return None


def retrieve_contract_info(supplier_id: str, amount: float, n_results: int = 2) -> Dict:
    """Busca el contrato del proveedor y extrae el monto maximo.
    
    Si USE_MOCK=True (default), usa los datos locales directamente.
    Si USE_MOCK=False, usa ChromaDB (requiere GOOGLE_API_KEY).
    """
    supplier_id = supplier_id.upper().strip()
    
    # Intentar con modo mock primero si esta habilitado
    if USE_MOCK:
        return _retrieve_mock(supplier_id, amount)
    
    # Si no, intentar con ChromaDB real
    try:
        from rag.retriever_real import retrieve_contract_info as real_retriever
        return real_retriever(supplier_id, amount, n_results)
    except ImportError:
        # Si no existe retriever_real, caer a mock
        return _retrieve_mock(supplier_id, amount)


def _retrieve_mock(supplier_id: str, amount: float) -> Dict:
    """Implementacion mock: usa archivos locales y limites predefinidos."""
    
    # Verificar si tenemos limite predefinido
    contract_limit = CONTRACT_LIMITS.get(supplier_id, 0.0)
    fragment = CONTRACT_FRAGMENTS.get(supplier_id, "")
    
    # Si no tenemos predefinido, intentar leer del archivo
    if contract_limit == 0.0:
        contract_text = _get_contract_text(supplier_id)
        if contract_text:
            contract_limit = _parse_amount(contract_text) or 0.0
            # Tomar los primeros 500 chars como fragmento
            fragment = contract_text[:500] + "..."
    
    # Si aun no tenemos limite, devolver no encontrado
    if contract_limit == 0.0:
        return {
            "found": False,
            "supplier_id": supplier_id,
            "contract_fragment": "",
            "all_chunks": [],
            "contract_limit": 0.0,
            "within_limit": False,
            "amount_checked": amount,
            "raw_extraction": "",
            "error": "Proveedor no tiene contrato registrado" if not fragment else "",
            "mock": True,
        }
    
    within_limit = amount <= contract_limit
    
    return {
        "found": True,
        "supplier_id": supplier_id,
        "contract_fragment": fragment,
        "all_chunks": [fragment] if fragment else [],
        "contract_limit": contract_limit,
        "within_limit": within_limit,
        "amount_checked": amount,
        "raw_extraction": f"${contract_limit:,.0f}",
        "error": "",
        "mock": True,
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        sid = sys.argv[1]
    else:
        sid = "SUP001"
    
    if len(sys.argv) > 2:
        amt = float(sys.argv[2])
    else:
        amt = 50000.0
    
    print(f"\n=== MOCK RETRIEVER: {sid} / ${amt} ===")
    result = retrieve_contract_info(sid, amt)
    print(f"Found: {result['found']}")
    print(f"Contract limit: ${result['contract_limit']:,.0f}")
    print(f"Within limit: {result['within_limit']}")
    print(f"Mock: {result.get('mock', False)}")
    if result['contract_fragment']:
        print(f"Fragment: {result['contract_fragment'][:200]}...")
