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
| **Python** | 3.12+ | Requerido por google-adk 2.3 |
| **pip** |Última | Gestor de paquetes Python |
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
```bash
cd Desktop
git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git invoice_approval_system
```

### Paso 3: Crear Entorno Virtual

```bash
cd Desktop\invoice_approval_system
python -m venv .venv
.venv\Scripts\activate
```

### Paso 4: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 5: Scripts Automatizados

| Script | Función |
|--------|---------|
| `setup.bat` | Instala todo automáticamente |
| `INICIAR.bat` | Inicia los 3 servicios |
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
chmod +x INICIAR.sh
./INICIAR.sh
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
chmod +x INICIAR.sh
./INICIAR.sh
```

---

## 5. Configuración Inicial

### 5.1 Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```bash
# Copiar plantilla
cp .env.example .env

# Editar
# Agregar: GOOGLE_API_KEY=tu_api_key
```

### 5.2 Archivo .env

```env
# API Keys (requeridas)
GOOGLE_API_KEY=tu_api_key_de_google

# Configuración de servicios
INV_SUPPLIER_SERVICE_URL=http://127.0.0.1:8001
INV_CONTRACT_SERVICE_URL=http://127.0.0.1:8002

# Puerto del backend
INV_PORT=8000
INV_HOST=127.0.0.1

# Habilitar watcher automático
INV_ENABLE_WATCHER=true
```

### 5.3 Indexar Contratos (Primera vez)

```bash
python rag/ingest.py
```

---

## 6. Inicio del Sistema

### Arquitectura de Puertos

```
┌─────────────────────────────────────────────────────────────┐
│                     localhost                               │
├─────────────────────────────────────────────────────────────┤
│  Puerto 8000 ──────► Backend (FastAPI)                     │
│                        ├── Back Office                       │
│                        ├── Supplier Portal                   │
│                        └── API REST                         │
│                                                              │
│  Puerto 8001 ──────► Supplier Service                       │
│                                                              │
│  Puerto 8002 ──────► Contract Service                       │
│                                                              │
│  Puerto 8003 ──────► External Auditor (A2A) [opcional]     │
└─────────────────────────────────────────────────────────────┘
```

### Método Automático

Ejecutar el script correspondiente:
- **Windows**: `INICIAR.bat`
- **Linux/macOS**: `./INICIAR.sh`

### Método Manual (3 terminales)

```bash
# Terminal 1 - Supplier Service
python -m platform.services.supplier_service.main
# Puerto: 8001

# Terminal 2 - Contract Service
python -m platform.services.contract_service.main
# Puerto: 8002

# Terminal 3 - Backend
cd platform/backend
python main.py
# Puerto: 8000
```

---

## 7. Verificación

### URLs del Sistema

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Back Office** | http://localhost:8000/ | Panel de administración |
| **Supplier Portal** | http://localhost:8000/supplier/ | Portal del proveedor |
| **API Docs** | http://localhost:8000/docs | Documentación Swagger |

### Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Login de Prueba

| ID | Nombre | Estado |
|----|--------|--------|
| SUP001 | TechCorp SA | ACTIVE |
| SUP002 | Papeleria Norte SRL | ACTIVE |
| SUP003 | Servicios Rapidos SA | INACTIVE |
| SUP004 | Limpieza Total SRL | ACTIVE |
| SUP005 | Consultoria Digital SA | ACTIVE |

### Smoke Tests

```bash
python -m guardrails.invoice_guardrail
python -m evaluation.metrics
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
```bash
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
├── agents/               ← Agentes ADK
├── tools/                ← Herramientas
├── guardrails/           ← Sistema de guardrails
├── rag/                  ← RAG (ChromaDB)
├── ml/                   ← Machine Learning
├── sessions/             ← Gestión de sesiones
├── evaluation/           ← Evaluación y testing
│
├── platform/             ← Backend y Frontend
│   ├── backend/          # Puerto 8000
│   ├── frontend/         # Back Office
│   └── services/         # Microservicios
│
├── supplier_portal/      ← Portal del proveedor
├── a2a/                  ← Agente A2A externo
│
├── data/                 ← Datos persistentes
│   ├── payments.db       # SQLite
│   ├── chroma_db/        # Vector store
│   ├── contracts/        # Contratos .txt
│   └── new_invoices/     # Facturas pendientes
│
└── docs/                 ← Documentación adicional
```

---

## Guías Detalladas por Sistema Operativo

| Guía | Ubicación |
|------|-----------|
| Windows | [docs/INSTALACION_WINDOWS.md](docs/INSTALACION_WINDOWS.md) |
| Linux | [docs/INSTALACION_LINUX.md](docs/INSTALACION_LINUX.md) |
| macOS | [docs/INSTALACION_MACOS.md](docs/INSTALACION_MACOS.md) |
| Guía Rápida | [docs/GUIA_RAPIDA.md](docs/GUIA_RAPIDA.md) |

---

## Documentación Relacionada

| Archivo | Descripción |
|---------|-------------|
| [README.md](README.md) | Descripción general y arquitectura |
| [CHANGELOG.md](CHANGELOG.md) | Historial de cambios |
| [docs/especificacion_sistema_invoiceflow.md](docs/especificacion_sistema_invoiceflow.md) | Especificación técnica |

---

**Versión del sistema**: 1.0.0  
**Última actualización**: 2025-06-20
