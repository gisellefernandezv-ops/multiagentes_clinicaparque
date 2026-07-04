@echo off
REM ==========================================================
REM setup.bat — Setup completo del proyecto
REM Crea venv, instala deps, indexa contratos
REM ==========================================================
echo.
echo === Invoice Approval System - Setup ===
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado.
    echo.
    echo Instalá Python 3.11+ desde https://www.python.org/downloads/
    echo IMPORTANTE: tildar "Add Python to PATH" en el instalador.
    echo.
    pause
    exit /b 1
)

echo [1/5] Python encontrado:
python --version
echo.

REM Crear venv
if not exist ".venv\" (
    echo [2/5] Creando entorno virtual .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el venv
        pause
        exit /b 1
    )
) else (
    echo [2/5] venv ya existe, salteando ...
)
echo.

REM Activar venv
call .venv\Scripts\activate.bat
echo [3/5] venv activado
echo.

REM Upgrade pip
echo        Actualizando pip ...
python -m pip install --upgrade pip --quiet
echo.

REM Instalar deps
echo [4/5] Instalando dependencias (esto puede tardar varios minutos) ...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo instalando dependencias
    pause
    exit /b 1
)
echo.

REM Verificar .env
if not exist ".env" (
    echo [WARN] No existe .env — copiando desde .env.example
    copy .env.example .env >nul
    echo        Edita .env con tu GOOGLE_API_KEY real antes de usar el sistema.
)
echo.

REM Ingesta de contratos
echo [5/5] Indexando contratos en ChromaDB ...
python rag\ingest.py
if errorlevel 1 (
    echo [WARN] Fallo la ingesta RAG. Verifica tu GOOGLE_API_KEY en .env
    echo        Puedes reintentar luego con: python rag\ingest.py
) else (
    echo.
    echo === SETUP COMPLETADO ===
    echo.
    echo Para levantar la UI:
    echo    cd ..
    echo    adk web invoice_approval_system
    echo.
    echo O con doble click en: start.bat
)
echo.
pause