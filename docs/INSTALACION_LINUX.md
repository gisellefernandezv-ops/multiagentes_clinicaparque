# InvoiceFlow — Guía de Instalación para Linux

## 📋 Requisitos Previos

### Software Necesario
1. **Python 3.12+** — Ya viene instalado en la mayoría de distribuciones
2. **Git** — Para clonar el repositorio
3. **pip** — Gestor de paquetes de Python

---

## 🚀 Instalación Paso a Paso

### Paso 1: Verificar Python

1. **Abrir Terminal**:
   - Presionar `Ctrl + Alt + T` o buscar "Terminal" en el menú de aplicaciones

2. **Verificar** Python instalado:
   ```bash
   python3 --version
   ```

3. **Si no está instalado**, instalar:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3 python3-pip python3-venv

   # Fedora
   sudo dnf install python3 python3-pip

   # Arch
   sudo pacman -S python python-pip
   ```

4. **Verificar pip**:
   ```bash
   pip3 --version
   ```

---

### Paso 2: Descargar el Proyecto

#### Opción A: Clonar con Git (Recomendado)

1. **Abrir Terminal**

2. **Navegar** a la carpeta home:
   ```bash
   cd ~
   ```

3. **Clonar** el repositorio:
   ```bash
   git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git invoice_approval_system
   ```

4. **Entrar** a la carpeta:
   ```bash
   cd invoice_approval_system
   ```

#### Opción B: Descargar ZIP

1. **Ir a** [GitHub](https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque)

2. **Click** en el botón verde **"<> Code"**

3. **Click** en **"Download ZIP"**

4. **Extraer** el archivo:
   ```bash
   cd ~/Descargas
   unzip multiagentes_clinicaparque-main.zip -d ~/
   mv ~/multiagentes_clinicaparque-main ~/invoice_approval_system
   ```

---

### Paso 3: Crear Entorno Virtual

1. **Navegar** a la carpeta del proyecto:
   ```bash
   cd ~/invoice_approval_system
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

### Paso 4: Instalar Dependencias

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

### Paso 5: Iniciar el Sistema

#### Método Automático

1. **Dar permisos de ejecución** al script:
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
cd ~/invoice_approval_system
source .venv/bin/activate
python3 -m platform.services.supplier_service.main
```

**Terminal 2 — Contract Service (puerto 8002)**:
```bash
cd ~/invoice_approval_system
source .venv/bin/activate
python3 -m platform.services.contract_service.main
```

**Terminal 3 — Backend (puerto 8000)**:
```bash
cd ~/invoice_approval_system/platform/backend
source .venv/bin/activate
python3 main.py
```

---

## 🌐 Acceso al Sistema

Abrir el navegador y visitar:

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

# Matar el proceso (reemplazar PID)
sudo kill -9 <PID>
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

## 📁 Estructura de Archivos

```
~/invoice_approval_system/
├── README.md
├── requirements.txt
├── INICIAR.sh              ← Script de inicio
├── platform/
│   ├── backend/            ← Servidor principal (8000)
│   ├── frontend/           ← Back Office
│   └── services/          ← Microservicios
├── supplier_portal/       ← Portal del proveedor
├── agents/                ← Agentes del sistema
├── tools/                 ← Herramientas
├── guardrails/            ← Reglas de validación
└── data/                  ← Base de datos
```

---

## 🛑 Detener el Sistema

En cada terminal, presionar `Ctrl + C`

O matar todos los procesos Python:
```bash
pkill -f "python.*platform"
```

---

## ✅ Checklist de Verificación

- [ ] Python 3.12+ instalado (`python3 --version`)
- [ ] pip instalado (`pip3 --version`)
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
