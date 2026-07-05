@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo   INVOICEFLOW - PUSH A GITHUB
echo ========================================================
echo.

REM Verificar si es repo
if not exist ".git" (
    echo [ERROR] No es repositorio Git
    pause
    exit /b 1
)

REM Verificar remote
echo [1] Verificando remote...
git remote -v

REM Agregar archivos
echo.
echo [2] Agregando archivos...
git add -A

REM Commit
echo.
echo [3] Commitando cambios...
git commit -m "fix: limpiar credenciales del README.md"

REM Push
echo.
echo [4] Subiendo a GitHub...
echo.
git push origin main

echo.
echo ========================================================
echo   VERIFICAR EN:
echo   https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque
echo ========================================================
echo.
pause
