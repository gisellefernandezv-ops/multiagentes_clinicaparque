"""LLM as a Judge — evaluación semántica con Gemini.

Usa `gemini-2.0-flash-latest` como juez para comparar la respuesta real del
sistema contra el golden case.
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict

from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Import lazy para no romper si el paquete google.generativeai no está
# instalado (la evaluación BertScore sí lo necesita, pero el judge lo necesita
# aparte).
import google.generativeai as genai  # noqa: E402


JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemini-2.0-flash-latest")

LLM_JUDGE_PROMPT = """Sos un juez experto en sistemas de aprobación de facturas.

Tu tarea es evaluar si la respuesta de un sistema multiagente es CORRECTA para
un caso de prueba dado. Sé estricto pero justo.

CRITERIOS DE EVALUACIÓN (ponderados):
1. **Decisión final** (peso 60%): debe coincidir con la decisión esperada.
2. **Justificación** (peso 25%): debe ser coherente con los datos de la
   factura (montos, proveedores, IDs) y citar el motivo correctamente.
3. **Campos requeridos presentes** (peso 15%): los campos listados en
   `expected_fields` deben estar presentes y no vacíos.

CASO ESPERADO (golden):
{expected}

RESPUESTA REAL DEL SISTEMA:
{actual}

Responde EXCLUSIVAMENTE con un JSON válido (sin markdown, sin explicaciones
adicionales fuera del JSON) con esta forma:

{{
  "passed": <bool>,
  "score": <float entre 0 y 1>,
  "reasoning": "<explicación corta y concreta>"
}}
"""


def _parse_judge_response(raw: str) -> Dict:
    """Extrae el JSON de la respuesta del juez, tolerando markdown ```json ...```."""
    if not raw:
        return {"passed": False, "score": 0.0, "reasoning": "respuesta vacía del juez"}

    text = raw.strip()

    # Quitar fences de markdown
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    # Intentar parsear el primer bloque { ... }
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    return {
        "passed": False,
        "score": 0.0,
        "reasoning": f"no se pudo parsear JSON del juez. Raw: {raw[:200]}",
    }


def _build_expected_block(case: Dict) -> str:
    """Compone el bloque esperado del caso."""
    return json.dumps(
        {
            "case_id": case.get("case_id"),
            "description": case.get("description"),
            "expected_decision": case.get("expected_decision"),
            "expected_fields": case.get("expected_fields", []),
            "expected_contract_limit": case.get("expected_contract_limit"),
            "input": case.get("input"),
        },
        indent=2,
        ensure_ascii=False,
    )


def _build_actual_block(actual_response: Dict) -> str:
    """Compone el bloque de respuesta real del sistema."""
    if isinstance(actual_response, dict):
        return json.dumps(actual_response, indent=2, ensure_ascii=False, default=str)
    return str(actual_response)


def evaluate_with_llm_judge(case: Dict, actual_response: Dict) -> Dict:
    """Evalúa si la respuesta del sistema es correcta usando Gemini como juez.

    Args:
        case: Golden case (de `golden_cases.GOLDEN_CASES`).
        actual_response: dict con la respuesta del sistema.

    Returns:
        dict con:
            - case_id (str)
            - passed (bool)
            - score (float 0-1)
            - reasoning (str)
            - expected (str, copia del bloque esperado)
            - actual (str, copia del bloque real)
            - error (str, si hubo)
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {
            "case_id": case.get("case_id", ""),
            "passed": False,
            "score": 0.0,
            "reasoning": "GOOGLE_API_KEY no configurada",
            "expected": "",
            "actual": "",
            "error": "missing_api_key",
        }

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(JUDGE_MODEL)

        prompt = LLM_JUDGE_PROMPT.format(
            expected=_build_expected_block(case),
            actual=_build_actual_block(actual_response),
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                max_output_tokens=512,
            ),
        )
        raw_text = response.text or ""
    except Exception as e:
        return {
            "case_id": case.get("case_id", ""),
            "passed": False,
            "score": 0.0,
            "reasoning": f"error invocando Gemini: {e}",
            "expected": _build_expected_block(case),
            "actual": _build_actual_block(actual_response),
            "error": str(e),
        }

    parsed = _parse_judge_response(raw_text)

    return {
        "case_id": case.get("case_id", ""),
        "passed": bool(parsed.get("passed", False)),
        "score": float(parsed.get("score", 0.0)),
        "reasoning": str(parsed.get("reasoning", "")),
        "expected": _build_expected_block(case),
        "actual": _build_actual_block(actual_response),
        "error": "",
    }


__all__ = ["evaluate_with_llm_judge", "LLM_JUDGE_PROMPT", "JUDGE_MODEL"]


if __name__ == "__main__":
    # Test rápido: comparar una respuesta correcta contra GC001
    from evaluation.golden_cases import get_case_by_id
    case = get_case_by_id("GC001")
    fake_response = {
        "decision": "APPROVED",
        "invoice_id": "INV-001",
        "supplier_id": "SUP001",
        "amount": 50000.0,
        "rejection_reason": "",
        "confirmation_id": "PAY-ABC12345",
        "payment_status": "PENDING_PAYMENT",
        "contract_limit": 150000.0,
    }
    res = evaluate_with_llm_judge(case, fake_response)
    print(json.dumps(res, indent=2, ensure_ascii=False))