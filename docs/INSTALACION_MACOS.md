# InvoiceFlow — Guía de Instalación para macOS

## 📋 Requisitos Previos

### Software Necesario
1. **Python 3.12+** — Se instala con Homebrew
2. **Git** — Se instala con Homebrew
3. **Homebrew** — Gestor de paquetes para macOS

---

## 🚀 Instalación Paso a Paso

### Paso 1: Instalar Homebrew

1. **Abrir Terminal**:
   - Presionar `Cmd + Espacio`
   - Buscar "Terminal" y abrirla

2. **Instalar Homebrew** (si no lo tenés):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. **Verificar** instalación:
   ```bash
   brew --version
   ```

---

### Paso 2: Instalar Python y Git

1. **Instalar** Python:
   ```bash
   brew install python@3.12
   ```

2. **Instalar** Git (si no lo tenés):
   ```bash
   brew install git
   ```

3. **Verificar** versiones:
   ```bash
   python3 --version
   git --version
   ```

---

### Paso 3: Descargar el Proyecto

#### Opción A: Clonar con Git (Recomendado)

1. **En Terminal**, navegar al escritorio:
   ```bash
   cd ~/Desktop
   ```

2. **Clonar** el repositorio:
   ```bash
   git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git invoice_approval_system
   ```

3. **Entrar** a la carpeta:
   ```bash
   cd invoice_approval_system
   ```

#### Opción B: Descargar ZIP

1. **Ir a** [GitHub](https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque)

2. **Click** en el botón verde **"<> Code"**

3. **Click** en **"Download ZIP"**

4. **Extraer** el archivo:
   ```bash
   cd ~/Desktop
   unzip multiagentes_clinicaparque-main.zip -d ~/Desktop
   mv ~/Desktop/multiagentes_clinicaparque-main ~/Desktop/invoice_approval_system
   ```

---

### Paso 4: Crear Entorno Virtual

1. **Navegar** a la carpeta del proyecto:
   ```bash
   cd ~/Desktop/invoice_approval_system
   ```

2. **Crear** entorno virtual:
   ```bash
   python3 -m venv .venv
   ```

3. **Activar** el entorno:
   ```bash
   source .venv/bin/activate
   ```

   > ✅ Verás que aparece `(.venv)` al inicio de la línea

---

### Paso 5: Instalar Dependencias

1. **Con el entorno virtual activado**, instalar:
   ```bash
   pip install -r requirements.txt
   ```

   > ⏳ Esto puede tardar 3-5 minutos

2. **Verificar** instalación:
   ```bash
   pip list | grep -E "fastapi|uvicorn|chromadb"
   ```

---

### Paso 6: Iniciar el Sistema

#### Método Automático

1. **Dar permisos** al script:
   ```bash
   chmod +x INICIAR.sh
   ```

2. **Ejecutar**:
   ```bash
   ./INICIAR.sh
   ```

#### Método Manual (3 terminales)

**Terminal 1 — Supplier Service (puerto 8001)**:
```bash
cd ~/Desktop/invoice_approval_system
source .venv/bin/activate
python3 -m platform.services.supplier_service.main
```

**Terminal 2 — Contract Service (puerto 8002)**:
```bash
cd ~/Desktop/invoice_approval_system
source .venv/bin/activate
python3 -m platform.services.contract_service.main
```

**Terminal 3 — Backend (puerto 8000)**:
```bash
cd ~/Desktop/invoice_approval_system/platform/backend
source .venv/bin/activate
python3 main.py
```

---

## 🌐 Acceso al Sistema

Abrir el navegador Safari, Chrome o Firefox y visitar:

| Servicio | URL |
|----------|-----|
| **Back Office** | [http://localhost:8000/](http://localhost:8000/) |
| **Portal del Proveedor** | [http://localhost:8000/supplier/](http://localhost:8000/supplier/) |
| **API Backend** | [http://localhost:8001/docs](http://localhost:8001/docs) |
| **API Contracts** | [http://localhost:8002/docs](http://localhost:8002/docs) |

---

## 🧪 Probar el Sistema

### Login como Proveedor

1. Abrir [http://localhost:8000/supplier/](http://localhost:8000/supplier/)

2. Ingresar uno de estos IDs:
   ```
   SUP001
   SUP002
   SUP003
   SUP004
   SUP005
   ```

3. Hacer clic en "Ingresar"

---

## 🔧 Solución de Problemas

### Error: "Command not found: python3"

**Solución**:
```bash
# Agregar Python al PATH
echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

### Error: "xcrun: error: invalid active developer path"

**Solución**:
```bash
xcode-select --install
```

Luego seguir las instrucciones en pantalla.

---

### Error: "Permission denied"

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

# Matar el proceso (reemplazar PID)
kill -9 <PID>
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

## 📁 Estructura de Archivos

```
~/Desktop/invoice_approval_system/
├── README.md
├── requirements.txt
├── INICIAR.sh               ← Script de inicio
├── platform/
│   ├── backend/            ← Servidor principal (8000)
│   ├── frontend/          ← Back Office
│   └── services/         ← Microservicios
├── supplier_portal/      ← Portal del proveedor
├── agents/               ← Agentes del sistema
├── tools/                 ← Herramientas
├── guardrails/            ← Reglas de validación
└── data/                  ← Base de datos
```

---

## 🛑 Detener el Sistema

En cada terminal, presionar `Cmd + C`

O matar todos los procesos Python:
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
- [ ] 3 terminales corriendo
- [ ] Navegador en `http://localhost:8000/`

---

## 📞 Necesitas Ayuda?

1. Revisar la sección de [Solución de Problemas](#-solución-de-problemas)
2. Verificar que cumples todos los [requisitos previos](#-requisitos-previos)
3. Revisar el archivo CHANGELOG.md para cambios recientes

---

**Última actualización**: 2025
**Versión del sistema**: 1.0.0
