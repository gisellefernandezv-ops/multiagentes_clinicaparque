# InvoiceFlow — Guía de Instalación

Bienvenido al sistema InvoiceFlow. Seleccioná tu sistema operativo para ver las instrucciones:

---

## 📘 [Guía para Windows](INSTALACION_WINDOWS.md)

Instalación paso a paso para usuarios de Windows 10/11.

**Contenido:**
- Cómo instalar Python
- Descargar el proyecto
- Instalar dependencias
- Iniciar el sistema
- Solución de problemas comunes

👉 [Ir a la guía de Windows](INSTALACION_WINDOWS.md)

---

## 🐧 [Guía para Linux](INSTALACION_LINUX.md)

Instalación paso a paso para distribuciones Ubuntu, Fedora, Arch, etc.

**Contenido:**
- Verificar Python
- Instalar con apt/dnf/pacman
- Clonar repositorio
- Crear entorno virtual
- Iniciar servicios

👉 [Ir a la guía de Linux](INSTALACION_LINUX.md)

---

## 🍎 [Guía para macOS](INSTALACION_MACOS.md)

Instalación paso a paso para Mac con chips Intel o Apple Silicon.

**Contenido:**
- Instalar Homebrew
- Instalar Python y Git
- Descargar el proyecto
- Crear entorno virtual
- Iniciar el sistema

👉 [Ir a la guía de macOS](INSTALACION_MACOS.md)

---

## 🚀 Inicio Rápido (Para usuarios avanzados)

```bash
# Clonar repositorio
git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git

# Entrar a la carpeta
cd invoice_approval_system

# Crear entorno virtual
python3 -m venv .venv

# Activar entorno
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Iniciar servicios
python -m platform.backend.main
python -m platform.services.supplier_service.main
python -m platform.services.contract_service.main
```

---

## 🌐 URLs del Sistema

Una vez iniciado, accedé desde el navegador:

| Servicio | URL |
|----------|-----|
| **Back Office** | http://localhost:8000/ |
| **Portal del Proveedor** | http://localhost:8000/supplier/ |
| **API Backend** | http://localhost:8001/docs |
| **API Contracts** | http://localhost:8002/docs |

---

## 🔑 Datos de Prueba

Para probar el sistema, usá estos IDs de proveedor:

| ID | Nombre | Estado |
|----|--------|--------|
| SUP001 | TechCorp SA | ACTIVE |
| SUP002 | Papeleria Norte SRL | ACTIVE |
| SUP003 | Servicios Rapidos SA | INACTIVE |
| SUP004 | Limpieza Total SRL | ACTIVE |
| SUP005 | Consultoria Digital SA | ACTIVE |

---

## ❓ Problemas Comunes

### "Python no encontrado"
- **Windows**: Reinstalar Python marcando "Add to PATH"
- **Linux**: `sudo apt install python3 python3-venv`
- **macOS**: `brew install python@3.12`

### "Puerto en uso"
```bash
# Linux/macOS
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### "Dependencias no instaladas"
```bash
pip install -r requirements.txt
```

---

## 📚 Documentación Adicional

- [README.md](../README.md) — Descripción general del sistema
- [CHANGELOG.md](../CHANGELOG.md) — Historial de cambios
- [CASOS_DE_USO.md](../CASOS_DE_USO.md) — Casos de uso y flujos

---

## 🆘 Necesitás ayuda?

1. Revisar la guía de tu sistema operativo
2. Verificar que Python esté instalado (`python --version`)
3. Asegurarte de activar el entorno virtual antes de instalar
4. Revisar los logs en la terminal para identificar errores

---

**Versión del sistema**: 1.0.0
**Última actualización**: 2025
