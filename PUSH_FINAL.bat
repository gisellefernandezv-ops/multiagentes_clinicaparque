@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================================
echo   INVOICEFLOW - PUSH A GITHUB
echo ========================================================
echo.

REM Verificar si es repo git
if not exist ".git" (
    echo [ERROR] No es un repositorio Git
    pause
    exit /b 1
)

echo [1] Agregando archivos...
git add -A

echo.
echo [2] Estado actual:
git status

echo.
echo [3] Haciendo commit...
git commit -m "feat: InvoiceFlow v1.0.0 - Sistema completo

- Multiagente con Google ADK
- 26 reglas de guardrail
- Frontend con sidebar
- Documentacion completa"

echo.
echo [4] Subiendo a GitHub...
git push -u origin main

echo.
echo ========================================================
echo   VERIFICAR EN:
echo   https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque
echo ========================================================
echo.
pause
