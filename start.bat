@echo off
REM ==========================================================
REM start.bat — Levanta la UI de ADK
REM ==========================================================
echo.
echo === Invoice Approval System - ADK UI ===
echo.

REM Verificar venv
if not exist ".venv\" (
    echo [ERROR] No existe .venv. Corre setup.bat primero.
    pause
    exit /b 1
)

REM Activar venv
call .venv\Scripts\activate.bat

REM Ir al directorio padre y lanzar ADK
cd ..
echo Levantando ADK en http://localhost:8000 ...
echo.
adk web invoice_approval_system