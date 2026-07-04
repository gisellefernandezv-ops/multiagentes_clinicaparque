@echo off
REM ==========================================================
REM Push al repositorio GitHub
REM ==========================================================
echo.
echo Subiendo proyecto a GitHub...
echo.

cd /d "%~dp0"

git init
git add .
git commit -m "feat: Sistema de aprobacion de facturas multiagente"
git branch -M main
git remote add origin https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git
git push -u origin main

echo.
echo Listo!
pause
