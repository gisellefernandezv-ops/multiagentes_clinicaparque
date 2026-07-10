@echo off
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Iniciando Backend en puerto 8000...
python main.py
