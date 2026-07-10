# InvoiceFlow — Guía de Instalación para Linux

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
| **Python** | 3.12+ | Viene preinstalado en la mayoría |
| **Git** | Opcional | `sudo apt install git` |
| **pip** | Gestor de paquetes | `sudo apt install python3-pip` |

### Verificar Python

```bash
python3 --version
```

Si no está instalado:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Fedora
sudo dnf install python3 python3-pip

# Arch
sudo pacman -S python python-pip
```

---

## 2. Instalación Paso a Paso

### Paso 1: Descargar el Proyecto

#### Opción A: Clonar con Git (Recomendado)

```bash
# Ir al directorio home
cd ~

# Clonar repositorio
git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git invoice_approval_system

# Entrar a la carpeta
cd invoice_approval_system
```

#### Opción B: Descargar ZIP

```bash
# Ir a Descargas
cd ~/Descargas

# Descargar
wget https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque/archive/refs/heads/main.zip -O invoiceflow.zip

# Extraer
unzip invoiceflow.zip -d ~/

# Mover carpeta
mv ~/multiagentes_clinicaparque-main ~/invoice_approval_system
```

### Paso 2: Crear Entorno Virtual

```bash
cd ~/invoice_approval_system

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

# Editar con nano/vim
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
cd ~/invoice_approval_system
source .venv/bin/activate
python -m platform.services.supplier_service.main
```

#### Terminal 2 — Contract Service (Puerto 8002)

```bash
cd ~/invoice_approval_system
source .venv/bin/activate
python -m platform.services.contract_service.main
```

#### Terminal 3 — Backend (Puerto 8000)

```bash
cd ~/invoice_approval_system/platform/backend
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

### Error: "python3: command not found"

**Solución**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv

# Agregar Python al PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

### Error: "No module named pip"

**Solución**:
```bash
sudo apt install python3-pip
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
sudo lsof -i :8000

# Matar el proceso (ejemplo: PID 1234)
sudo kill -9 1234
```

Para matar todos los procesos Python del proyecto:
```bash
pkill -f "python.*platform"
```

---

### Error de permisos en la carpeta

**Solución**:
```bash
# Cambiar dueño de la carpeta
sudo chown -R $USER:$USER ~/invoice_approval_system

# O cambiar permisos
chmod -R 755 ~/invoice_approval_system
```

---

## 6. Estructura de Archivos

```
~/invoice_approval_system/
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

### Método 1: Ctrl + C
En cada terminal, presionar `Ctrl + C`

### Método 2: Matar procesos
```bash
pkill -f "python.*platform"
```

---

## ✅ Checklist de Verificación

- [ ] Python 3.12+ instalado (`python3 --version`)
- [ ] pip instalado (`pip3 --version`)
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

## Enlaces Útiles

| Recurso | URL |
|---------|-----|
| Repositorio GitHub | https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque |
| Documentación ADK | https://google.github.io/adk-docs/ |

---

**Versión del sistema**: 1.0.0  
**Última actualización**: 2025-06-20
