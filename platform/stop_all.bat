@echo off
REM ==========================================================
REM stop_all.bat — Para los 3 servicios del producto
REM ==========================================================
echo.
echo === Deteniendo servicios InvoiceFlow ===
echo.

echo [1/3] Cerrando Backend (puerto 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
    echo    Cerrado PID %%a
)

echo [2/3] Cerrando Supplier Service (puerto 8001)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
    echo    Cerrado PID %%a
)

echo [3/3] Cerrando Contract Service (puerto 8002)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8002 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
    echo    Cerrado PID %%a
)

echo.
echo === Servicios detenidos ===
pause