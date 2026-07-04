"""Métricas de evaluación: BertScore + run_full_evaluation.

Corre todos los golden cases contra el sistema (vía `system_runner`), evalúa
con LLM as a Judge y calcula BertScore sobre la justificación.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from evaluation.golden_cases import GOLDEN_CASES
from evaluation.llm_judge import evaluate_with_llm_judge


# Tipo del runner: callable async (case) -> dict respuesta del sistema
SystemRunner = Callable[[Dict], Awaitable[Dict]]


# ----------------------------------------------------------------------
# BertScore
# ----------------------------------------------------------------------

_BERT_SCORER = None


def _get_bert_scorer():
    """Carga lazy del scorer de bert-score (es pesado, ~800MB)."""
    global _BERT_SCORER
    if _BERT_SCORER is None:
        try:
            from bert_score import BERTScorer
            _BERT_SCORER = BERTScorer(
                lang="es",
                model_type="xlm-roberta-base",
                num_layers=10,
                rescale_with_baseline=False,
            )
        except Exception as e:
            print(f"[metrics] WARN: no se pudo cargar bert-score: {e}")
            _BERT_SCORER = False  # marca de "no disponible"
    return _BERT_SCORER


def calculate_bert_score(reference: str, candidate: str) -> Dict[str, float]:
    """Calcula BertScore entre la justificación esperada y la real.

    Args:
        reference: texto de referencia (justificación esperada).
        candidate: texto candidato (justificación real).

    Returns:
        dict con precision, recall, f1 (floats). Si bert-score no está
        disponible, devuelve f1=0.0 y error explicativo.
    """
    if not reference or not candidate:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "error": "texto vacío"}

    scorer = _get_bert_scorer()
    if not scorer:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "error": "bert-score no disponible",
        }

    try:
        P, R, F1 = scorer.score([candidate], [reference])
        return {
            "precision": float(P[0]),
            "recall": float(R[0]),
            "f1": float(F1[0]),
            "error": "",
        }
    except Exception as e:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "error": str(e)}


# ----------------------------------------------------------------------
# Runner default (invoca el orquestador real de ADK)
# ----------------------------------------------------------------------


async def default_system_runner(case: Dict) -> Dict:
    """Runner por defecto: ejecuta el orquestador contra el caso.

    Crea una sesión, inyecta el state inicial con la factura, y deja correr
    al orquestador con sus sub-agentes.

    NOTA: este runner depende de que ChromaDB esté ingesta y .env configurado.
    """
    from google.adk.runners import Runner
    from google.genai.types import Content, Part

    from agents.orchestrator import create_orchestrator
    from sessions.session_manager import InvoiceSessionManager

    orchestrator = create_orchestrator()
    sm = InvoiceSessionManager(app_name="eval_app")

    sid = sm.create_session(
        invoice_id=case["input"].get("invoice_id", "INV-UNKNOWN"),
        initial=case["input"],
    )

    runner = Runner(
        agent=orchestrator,
        app_name="eval_app",
        session_service=sm.service,
    )

    # Mensaje inicial: el JSON de la factura en lenguaje natural para Gemini
    user_msg = (
        "Procesá la siguiente factura:\n\n"
        f"```json\n{json.dumps(case['input'], indent=2, ensure_ascii=False)}\n```"
    )

    final_state = {}
    try:
        events_async = runner.run_async(
            user_id=sm._user_id,
            session_id=sid,
            new_message=Content(role="user", parts=[Part(text=user_msg)]),
        )
        async for event in events_async:
            # Capturar el último evento "final"
            if hasattr(event, "actions") and event.actions and event.actions.state_delta:
                final_state.update(event.actions.state_delta)
            if hasattr(event, "is_final_response") and event.is_final_response():
                if hasattr(event, "content") and event.content:
                    text = "".join(p.text for p in event.content.parts if hasattr(p, "text"))
                    if text:
                        final_state["_final_text"] = text
    except Exception as e:
        return {
            "error": f"runner failed: {e}",
            "traceback": traceback.format_exc(),
            "decision": "ERROR",
        }

    # Merge con el state del session manager (más completo)
    try:
        sm_state = sm.get_session_state(sid)
        merged = {**sm_state, **final_state}
        return merged
    except Exception:
        return final_state or {"decision": "UNKNOWN"}


# ----------------------------------------------------------------------
# Runner de evaluación
# ----------------------------------------------------------------------


def _extract_justification(actual: Dict) -> str:
    """Extrae un texto de justificación de la respuesta del sistema."""
    parts = []
    for key in ("rejection_reason", "guardrail_reason", "_final_text"):
        v = actual.get(key)
        if v and isinstance(v, str):
            parts.append(v)
    return " ".join(parts).strip()


def _build_expected_justification(case: Dict) -> str:
    """Construye una justificación esperada aproximada para BertScore."""
    decision = case.get("expected_decision", "")
    desc = case.get("description", "")
    fields = case.get("expected_fields", [])
    base = f"Decisión esperada: {decision}. {desc}."
    if "rejection_reason" in fields:
        base += " Debe incluir un rejection_reason."
    if "confirmation_id" in fields:
        base += " Debe incluir un confirmation_id."
    return base


def run_full_evaluation(
    golden_cases: Optional[List[Dict]] = None,
    system_runner: Optional[SystemRunner] = None,
    use_bert: bool = True,
    use_judge: bool = True,
    verbose: bool = True,
) -> Dict:
    """Corre todos los golden cases y calcula métricas agregadas.

    Args:
        golden_cases: lista de casos (default: GOLDEN_CASES).
        system_runner: callable async (case) -> dict. Si None, usa el default.
        use_bert: si True, calcula BertScore.
        use_judge: si True, calcula LLM as a Judge.
        verbose: si True, imprime progreso.

    Returns:
        dict con:
            - total_cases (int)
            - passed (int)
            - failed (int)
            - pass_rate (float)
            - avg_bert_f1 (float)
            - avg_judge_score (float)
            - results (list[dict])
            - elapsed_seconds (float)
    """
    cases = golden_cases or GOLDEN_CASES
    runner = system_runner or default_system_runner

    if verbose:
        print(f"[eval] Corriendo {len(cases)} golden cases...")
        print(f"[eval] BertScore={'ON' if use_bert else 'OFF'} | Judge={'ON' if use_judge else 'OFF'}")

    results: List[Dict] = []
    judge_scores: List[float] = []
    bert_f1s: List[float] = []
    passed_count = 0
    start = time.time()

    for i, case in enumerate(cases, 1):
        cid = case["case_id"]
        if verbose:
            print(f"\n[eval] ({i}/{len(cases)}) {cid}: {case['description']}")

        # 1. Correr el sistema
        try:
            actual: Dict = asyncio.run(runner(case))
        except Exception as e:
            actual = {
                "error": f"runner exception: {e}",
                "traceback": traceback.format_exc(),
                "decision": "ERROR",
            }

        # 2. Comparación por campo (decision + expected_fields)
        decision_ok = actual.get("decision") == case["expected_decision"]
        missing_fields = [
            f for f in case.get("expected_fields", []) if not actual.get(f)
        ]
        decision_match = decision_ok and not missing_fields
        if decision_match:
            passed_count += 1

        # 3. LLM as a Judge
        judge_result: Dict = {"passed": False, "score": 0.0, "reasoning": "skipped"}
        if use_judge:
            try:
                judge_result = evaluate_with_llm_judge(case, actual)
                judge_scores.append(judge_result.get("score", 0.0))
            except Exception as e:
                judge_result = {"passed": False, "score": 0.0, "reasoning": f"judge error: {e}"}

        # 4. BertScore
        bert: Dict = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "error": "skipped"}
        if use_bert:
            try:
                ref = _build_expected_justification(case)
                cand = _extract_justification(actual)
                bert = calculate_bert_score(ref, cand)
                if bert.get("f1", 0.0) > 0:
                    bert_f1s.append(bert["f1"])
            except Exception as e:
                bert = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "error": str(e)}

        # Resultado del caso
        case_result = {
            "case_id": cid,
            "description": case["description"],
            "expected_decision": case["expected_decision"],
            "actual_decision": actual.get("decision"),
            "field_match": decision_match,
            "missing_fields": missing_fields,
            "judge": judge_result,
            "bert_score": bert,
            "actual_response": actual,
        }
        results.append(case_result)

        if verbose:
            status = "PASS" if decision_match else "FAIL"
            js = judge_result.get("score", 0.0)
            bf = bert.get("f1", 0.0)
            print(
                f"  {status} | judge={js:.2f} | bert_f1={bf:.2f} | "
                f"actual_decision={actual.get('decision')!r}"
            )
            if judge_result.get("reasoning"):
                print(f"  judge_reasoning: {judge_result['reasoning'][:150]}")

    elapsed = time.time() - start
    total = len(cases)
    failed = total - passed_count
    pass_rate = passed_count / total if total else 0.0
    avg_judge = sum(judge_scores) / len(judge_scores) if judge_scores else 0.0
    avg_bert_f1 = sum(bert_f1s) / len(bert_f1s) if bert_f1s else 0.0

    summary = {
        "total_cases": total,
        "passed": passed_count,
        "failed": failed,
        "pass_rate": pass_rate,
        "avg_judge_score": avg_judge,
        "avg_bert_f1": avg_bert_f1,
        "elapsed_seconds": elapsed,
        "results": results,
    }

    if verbose:
        print("\n" + "=" * 70)
        print(f"[eval] Pass rate: {passed_count}/{total} ({pass_rate * 100:.1f}%)")
        print(f"[eval] Avg LLM-judge score: {avg_judge:.3f}")
        print(f"[eval] Avg BertScore F1: {avg_bert_f1:.3f}")
        print(f"[eval] Elapsed: {elapsed:.1f}s")
        print("=" * 70)

    return summary


def main():
    """Entry point CLI: `python -m evaluation.metrics`"""
    summary = run_full_evaluation()
    # Salida JSON al final para integración con CI
    print("\n--- JSON SUMMARY ---")
    print(json.dumps(
        {k: v for k, v in summary.items() if k != "results"},
        indent=2,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()