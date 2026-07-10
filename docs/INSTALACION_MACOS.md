# InvoiceFlow — Guía de Instalación para macOS

## Tabla de Contenidos

1. [Requisitos Previos](#1-requisitos-previos)
2. [Instalación Paso a Paso](#2-instalación-paso-a-paso)
3. [Inicio del Sistema](#3-inicio-del-sistema)
4. [Acceso y Verificación](#4-acceso-y-verificación)
5. [Solución de Problemas](#5-solución-de-problemas)
6. [Estructura de Archivos](#6-estructura-de-archivos)

---

## 1. Requisitos Previos

### Software Necesario

| Software | Instalación | Comando |
|----------|-------------|---------|
| **Homebrew** | Gestor de paquetes | [brew.sh](https://brew.sh/) |
| **Python** | 3.12+ | `brew install python@3.12` |
| **Git** | Opcional | `brew install git` |

### Instalar Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Instalar Python y Git

```bash
brew install python@3.12
brew install git
```

### Verificar Instalación

```bash
python3 --version
git --version
brew --version
```

---

## 2. Instalación Paso a Paso

### Paso 1: Descargar el Proyecto

#### Opción A: Clonar con Git (Recomendado)

```bash
# Ir al escritorio
cd ~/Desktop

# Clonar repositorio
git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git invoice_approval_system

# Entrar a la carpeta
cd invoice_approval_system
```

#### Opción B: Descargar ZIP

1. Ir a [GitHub](https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque)
2. Click en **"<> Code"** → **"Download ZIP"**
3. Guardar en Escritorio
4. Extraer el ZIP

### Paso 2: Crear Entorno Virtual

```bash
cd ~/Desktop/invoice_approval_system

# Crear entorno virtual
python3 -m venv .venv

# Activar entorno
source .venv/bin/activate
```

> ✅ Verás `(.venv)` al inicio de la línea

### Paso 3: Instalar Dependencias

```bash
# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt
```

> ⏳ Puede tardar 3-5 minutos

### Paso 4: Configurar Variables de Entorno

```bash
# Copiar plantilla
cp .env.example .env

# Editar
nano .env
```

Agregar tu API Key de Google:
```env
GOOGLE_API_KEY=tu_api_key_aqui
```

Guardar con `Ctrl + O`, `Enter`, `Ctrl + X`

### Paso 5: Indexar Contratos (Primera vez)

```bash
python rag/ingest.py
```

---

## 3. Inicio del Sistema

### Método Automático

```bash
# Dar permisos al script
chmod +x INICIAR.sh

# Ejecutar
./INICIAR.sh
```

### Método Manual (3 terminales)

#### Terminal 1 — Supplier Service (Puerto 8001)

```bash
cd ~/Desktop/invoice_approval_system
source .venv/bin/activate
python -m platform.services.supplier_service.main
```

#### Terminal 2 — Contract Service (Puerto 8002)

```bash
cd ~/Desktop/invoice_approval_system
source .venv/bin/activate
python -m platform.services.contract_service.main
```

#### Terminal 3 — Backend (Puerto 8000)

```bash
cd ~/Desktop/invoice_approval_system/platform/backend
source .venv/bin/activate
python main.py
```

---

## 4. Acceso y Verificación

### URLs del Sistema

| Servicio | URL |
|----------|-----|
| **Back Office** | http://localhost:8000/ |
| **Supplier Portal** | http://localhost:8000/supplier/ |
| **API Backend** | http://localhost:8000/docs |
| **API Supplier** | http://localhost:8001/docs |
| **API Contract** | http://localhost:8002/docs |

### Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Login como Proveedor

1. Abrir http://localhost:8000/supplier/

2. Ingresar ID de prueba:

| ID | Nombre | Estado |
|----|--------|--------|
| SUP001 | TechCorp SA | ACTIVE |
| SUP002 | Papeleria Norte SRL | ACTIVE |
| SUP003 | Servicios Rapidos SA | INACTIVE |
| SUP004 | Limpieza Total SRL | ACTIVE |
| SUP005 | Consultoria Digital SA | ACTIVE |

---

## 5. Solución de Problemas

### Error: "Command not found: python3"

**Solución**:
```bash
# Agregar Python al PATH (para Apple Silicon)
echo 'export PATH="/opt/homebrew/opt/python@3.12/bin:$PATH"' >> ~/.zshrc

# O para Intel Mac
echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.zshrc

source ~/.zshrc
```

---

### Error: "xcrun: error: invalid active developer path"

**Solución**:
```bash
xcode-select --install
```

---

### Error: "Permission denied" al ejecutar script

**Solución**:
```bash
chmod +x INICIAR.sh
./INICIAR.sh
```

---

### Error: "Port already in use"

**Solución**:
```bash
# Ver qué usa el puerto
lsof -i :8000

# Matar el proceso (ejemplo: PID 1234)
kill -9 1234
```

Para matar todos los procesos Python del proyecto:
```bash
pkill -f "python.*platform"
```

---

### Error con Homebrew

**Solución**:
```bash
# Actualizar Homebrew
brew update

# Reparar
brew doctor
```

---

## 6. Estructura de Archivos

```
~/Desktop/invoice_approval_system/
├── README.md                   # Documentación principal
├── CHANGELOG.md               # Historial de cambios
├── requirements.txt           # Dependencias Python
│
├── INICIAR.sh                # Script de inicio automático
├── setup.sh                  # Script de instalación
│
├── platform/                  # Backend y servicios
│   ├── backend/              # Servidor principal (8000)
│   ├── frontend/            # Back Office
│   └── services/            # Microservicios
│
├── agents/                   # Agentes ADK
├── tools/                   # Herramientas
├── guardrails/              # Sistema de guardrails
├── rag/                     # RAG (ChromaDB)
├── ml/                      # Machine Learning
├── supplier_portal/         # Portal del proveedor
├── a2a/                     # Agente A2A externo
├── data/                    # Datos persistentes
└── docs/                    # Documentación adicional
```

---

## 🛑 Detener el Sistema

### Método 1: Cmd + C
En cada terminal, presionar `Cmd + C`

### Método 2: Matar procesos
```bash
pkill -f "python.*platform"
```

---

## ✅ Checklist de Verificación

- [ ] Homebrew instalado (`brew --version`)
- [ ] Python 3.12+ instalado (`python3 --version`)
- [ ] Git instalado (`git --version`)
- [ ] Entorno virtual activado (`.venv` visible)
- [ ] Dependencias instaladas (`pip list`)
- [ ] Archivo `.env` con `GOOGLE_API_KEY`
- [ ] 3 terminales corriendo
- [ ] Navegador en `http://localhost:8000/`

---

## 📞 Necesitas Ayuda?

1. Revisar la sección de [Solución de Problemas](#5-solución-de-problemas)
2. Verificar que cumples todos los requisitos
3. Revisar logs en las terminales para identificar errores

---

## Notas para Apple Silicon (M1/M2/M3)

Si tienes un Mac con chip Apple Silicon, algunos paquetes binarios pueden necesitar Rosetta:

```bash
# Instalar Rosetta (si es necesario)
softwareupdate --install-rosetta
```

---

## Enlaces Útiles

| Recurso | URL |
|---------|-----|
| Repositorio GitHub | https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque |
| Documentación ADK | https://google.github.io/adk-docs/ |
| Homebrew | https://brew.sh/ |

---

**Versión del sistema**: 1.0.0  
**Última actualización**: 2025-06-20
