@echo off
REM ==========================================================
REM smoke_test.bat — Tests rápidos sin levantar UI
REM ==========================================================
echo.
echo === Smoke Tests ===
echo.

if not exist ".venv\" (
    echo [ERROR] No existe .venv. Corre setup.bat primero.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo [1/6] Guardrail ...
python -m guardrails.invoice_guardrail
echo.

echo [2/6] Supplier tool ...
python -m tools.supplier_mcp_tool
echo.

echo [3/6] RAG tool (requiere ingesta previa) ...
python -m tools.rag_tool
echo.

echo [4/6] Payment DB tool ...
python -m tools.payment_db_tool
echo.

echo [5/6] Creando agentes ...
python -m agents.validator_agent
python -m agents.contract_agent
python -m agents.payment_agent
python -m agents.orchestrator
echo.

echo [6/6] Session manager ...
python -m sessions.session_manager
echo.

echo === SMOKE TESTS COMPLETADOS ===
pause