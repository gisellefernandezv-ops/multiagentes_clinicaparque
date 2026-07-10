@echo off
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Iniciando Supplier Service en puerto 8001...
python -m platform.services.supplier_service.main
