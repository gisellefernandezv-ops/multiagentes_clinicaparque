# InvoiceFlow — Guía de Instalación Completa

> Instalación paso a paso para Windows, Linux y macOS.

---

## Tabla de Contenidos

1. [Requisitos del Sistema](#1-requisitos-del-sistema)
2. [Instalación en Windows](#2-instalación-en-windows)
3. [Instalación en Linux](#3-instalación-en-linux)
4. [Instalación en macOS](#4-instalación-en-macos)
5. [Configuración Inicial](#5-configuración-inicial)
6. [Inicio del Sistema](#6-inicio-del-sistema)
7. [Verificación](#7-verificación)
8. [Resolución de Problemas](#8-resolución-de-problemas)

---

## 1. Requisitos del Sistema

### Software Requerido

| Componente | Versión Mínima | Notas |
|------------|---------------|-------|
| **Python** | 3.12+ | Requerido por google-adk >=1.0.0 |
| **pip** | Última | Gestor de paquetes Python |
| **Git** | 2.0+ | Opcional, para clonar repositorio |

### Verificar Python

```bash
# Windows
python --version

# Linux/macOS
python3 --version
```

Debería mostrar: `Python 3.12.x`

---

## 2. Instalación en Windows

### Paso 1: Instalar Python

1. Descargar desde [python.org/downloads/windows/](https://www.python.org/downloads/windows/)
2. Ejecutar el instalador
3. **IMPORTANTE**: Marcar `☑ Add Python to PATH`
4. Click en "Install Now"

### Paso 2: Descargar el Proyecto

**Opción A: ZIP**
1. Descargar desde GitHub
2. Extraer en Escritorio
3. Renombrar a `invoice_approval_system`

**Opción B: Git**
```batch
cd %USERPROFILE%\Desktop
git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git invoice_approval_system
```

### Paso 3: Crear Entorno Virtual

```batch
cd %USERPROFILE%\Desktop\invoice_approval_system
python -m venv .venv
.venv\Scripts\activate
```

### Paso 4: Instalar Dependencias

```batch
pip install -r requirements.txt
```

### Paso 5: Scripts Automatizados

| Script | Función |
|--------|---------|
| `setup.bat` | Instala todo automáticamente |
| `start_servers.py` | Inicia todos los servicios |
| `smoke_test.bat` | Verifica componentes |

---

## 3. Instalación en Linux

### Paso 1: Verificar/Instalar Python

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Fedora
sudo dnf install python3 python3-pip

# Arch
sudo pacman -S python python-pip
```

### Paso 2: Descargar el Proyecto

```bash
cd ~
git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git invoice_approval_system
```

### Paso 3: Crear Entorno Virtual

```bash
cd ~/invoice_approval_system
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 4: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 5: Scripts Automatizados

```bash
chmod +x start_servers.py INICIAR.bat setup.bat smoke_test.bat
./start_servers.py
```

---

## 4. Instalación en macOS

### Paso 1: Instalar Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Paso 2: Instalar Python y Git

```bash
brew install python@3.12
brew install git
```

### Paso 3: Descargar el Proyecto

```bash
cd ~/Desktop
git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git invoice_approval_system
```

### Paso 4: Crear Entorno Virtual

```bash
cd ~/Desktop/invoice_approval_system
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 5: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 6: Scripts Automatizados

```bash
chmod +x start_servers.py
python start_servers.py
```

---

## 5. Configuración Inicial

### 5.1 Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```bash
# Copiar plantilla
cp .env.example .env

# Editar
notepad .env
```

### 5.2 Archivo .env

```env
# API Keys (requerida)
GOOGLE_API_KEY=tu_api_key_de_google_ai_studio

# Configuración de servicios (opcional, defaults funcionan)
INV_SUPPLIER_SERVICE_URL=http://127.0.0.1:8001
INV_CONTRACT_SERVICE_URL=http://127.0.0.1:8002
INV_PORT=8000
INV_HOST=127.0.0.1
INV_ENABLE_WATCHER=true
```

### 5.3 Indexar Contratos (Primera vez)

```bash
python rag/ingest.py
```

Esto carga los contratos demo en ChromaDB para el RAG.

---

## 6. Inicio del Sistema

### Arquitectura de Puertos

```
┌─────────────────────────────────────────────────────────────┐
│                     localhost                               │
├─────────────────────────────────────────────────────────────┤
│  Puerto 8000 ──────► Backend (FastAPI)                    │
│                        ├── Back Office                       │
│                        ├── Supplier Portal                   │
│                        └── API REST                         │
│                                                              │
│  Puerto 8001 ──────► Supplier Service (ABM)               │
│                                                              │
│  Puerto 8002 ──────► Contract Service (RAG)               │
│                                                              │
│  Puerto 8003 ──────► External Auditor (A2A)               │
│                                                              │
│  Puerto 5000 ──────► MCP Toolbox Server                    │
└─────────────────────────────────────────────────────────────┘
```

### Método Automático (Recomendado)

```bash
python start_servers.py
```

Este script inicia todos los servicios en paralelo.

### Método Manual (4 terminales)

```bash
# Terminal 1 - Supplier Service (Puerto 8001)
python -m uvicorn app.services.supplier_service.main:app --host 127.0.0.1 --port 8001

# Terminal 2 - Contract Service (Puerto 8002)
python -m uvicorn app.services.contract_service.main:app --host 127.0.0.1 --port 8002

# Terminal 3 - MCP Toolbox (Puerto 5000)
python -m uvicorn app.services.toolbox_server.main:app --host 127.0.0.1 --port 5000

# Terminal 4 - Backend (Puerto 8000)
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### URLs del Sistema

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Back Office** | http://localhost:8000/ | Panel de administración |
| **Supplier Portal** | http://localhost:8000/supplier/ | Portal del proveedor |
| **API Docs** | http://localhost:8000/docs | Documentación Swagger |

---

## 7. Verificación

### Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:5000/health
curl http://localhost:8000/agents/health
```

### Login de Prueba

| ID | Nombre | Estado | Límite Contractual |
|----|--------|--------|-------------------|
| SUP001 | TechCorp SA | ACTIVE | $150,000 |
| SUP002 | Papeleria Norte SRL | ACTIVE | $30,000 |
| SUP003 | Servicios Rapidos SA | INACTIVE | — |
| SUP004 | Limpieza Total SRL | ACTIVE | $80,000 |
| SUP005 | Consultoria Digital SA | ACTIVE | $200,000 |

### Smoke Tests

```bash
# Verificar imports de agentes
python -c "from agents.orchestrator import create_orchestrator; print('Agents OK')"

# Verificar base de datos
python -c "import sqlite3; c=sqlite3.connect('data/payments.db'); print(c.execute('SELECT COUNT(*) FROM payments').fetchone()[0], 'pagos')"

# Verificar ChromaDB
python -c "import chromadb; c=chromadb.PersistentClient('app/data/chroma_db'); print('ChromaDB OK:', c.list_collections())"

# Verificar guardrails
python -c "from guardrails.invoice_guardrail import apply_invoice_guardrail; print('Guardrails OK')"
```

---

## 8. Resolución de Problemas

### Error: "ModuleNotFoundError"

```bash
# Asegurarse que el entorno virtual está activo
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Reinstalar dependencias
pip install --force-reinstall -r requirements.txt
```

### Error: "Port already in use"

**Windows**:
```batch
netstat -ano | findstr :8000
taskkill /PID <NUMERO> /F
```

**Linux/macOS**:
```bash
lsof -i :8000
kill -9 <PID>
```

### Error: "Python no encontrado"

Reinstalar Python marcando "Add to PATH"

### Error: "pip no reconocido"

```bash
python -m pip install -r requirements.txt
```

### Error de Encoding (Windows)

Agregar al inicio de scripts `.bat`:
```batch
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
```

---

## Estructura de Archivos Final

```
invoice_approval_system/
├── README.md              ← Documentación principal
├── CHANGELOG.md          ← Historial de cambios
├── INSTALL.md            ← Esta guía
├── requirements.txt      ← Dependencias
├── .env.example          ← Plantilla variables
│
├── agents/               ← Agentes ADK (6 agentes)
├── tools/                ← Herramientas (9 tools)
├── guardrails/           ← Sistema de guardrails (26 reglas)
├── rag/                  ← RAG (ChromaDB)
├── ml/                   ← Machine Learning
├── sessions/             ← Gestión de sesiones ADK
├── evaluation/           ← Evaluación (Golden Cases + LLM Judge)
├── mcp_config/           ← Configuración MCP
│
├── app/                  ← Aplicación principal
│   ├── backend/         # Puerto 8000
│   │   ├── main.py
│   │   ├── chat_router.py
│   │   ├── inbox_router.py
│   │   └── watcher.py
│   ├── frontend/        # Back Office UI
│   ├── services/
│   │   ├── supplier_service/  # Puerto 8001
│   │   ├── contract_service/ # Puerto 8002
│   │   └── toolbox_server/   # Puerto 5000
│   └── data/
│       ├── suppliers.db
│       ├── inbox.db
│       ├── adk_sessions.db
│       └── chroma_db/
│
├── supplier_portal/      ← Portal del proveedor UI
├── a2a/                  ← Agente A2A externo (puerto 8003)
│
├── data/                 ← Datos persistentes
│   ├── payments.db
│   ├── chat_sessions.db
│   └── contracts/
│
├── docs/                 ← Documentación técnica
└── bugs/                 ← Registro de bugs
```

---

## Guías Detalladas por Sistema Operativo

| Guía | Ubicación |
|------|-----------|
| Windows | `docs/INSTALACION_WINDOWS.md` |
| Linux | `docs/INSTALACION_LINUX.md` |
| macOS | `docs/INSTALACION_MACOS.md` |
| Guía Rápida | `docs/GUIA_RAPIDA.md` |

---

## Documentación Relacionada

| Archivo | Descripción |
|---------|-------------|
| [README.md](README.md) | Descripción general y arquitectura |
| [CHANGELOG.md](CHANGELOG.md) | Historial de cambios |
| [docs/SPECS_*.md](docs/) | Especificaciones técnicas completas |

---

**Versión del sistema**: 3.0.0  
**Última actualización**: 2026-07-18
