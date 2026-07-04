@echo off
REM ==========================================================
REM start_all.bat — Levanta los 3 servicios del producto
REM ==========================================================
echo.
echo === InvoiceFlow — Producto plataforma ===
echo.

if not exist "..\..\..\invoice_approval_system\.venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el venv. Corre setup.bat primero.
    pause
    exit /b 1
)

set ROOT=%~dp0..\..
set VENV_PY=%ROOT%\.venv\Scripts\python.exe

echo [1/3] Levantando Supplier Service (puerto 8001)...
start "supplier-service" cmd /k "cd /d %ROOT%\platform\services\supplier_service && %VENV_PY% main.py"

echo [2/3] Levantando Contract Service (puerto 8002)...
start "contract-service" cmd /k "cd /d %ROOT%\platform\services\contract_service && %VENV_PY% main.py"

echo Esperando 8 segundos para que arranquen los microservicios...
timeout /t 8 /nobreak >nul

echo [3/3] Levantando Backend + UI (puerto 8000)...
start "invoiceflow-backend" cmd /k "cd /d %ROOT%\platform\backend && %VENV_PY% main.py"

echo.
echo ============================================================
echo  ✓ Los 3 servicios deberian estar corriendo en:
echo    - Backend + UI:    http://localhost:8000
echo    - Supplier service: http://localhost:8001/docs
echo    - Contract service: http://localhost:8002/docs
echo.
echo  Para parar todo: cerrar las 3 ventanas o ejecutar stop_all.bat
echo ============================================================
echo.
pause