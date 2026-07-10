@echo off
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Iniciando Contract Service en puerto 8002...
python -m platform.services.contract_service.main
