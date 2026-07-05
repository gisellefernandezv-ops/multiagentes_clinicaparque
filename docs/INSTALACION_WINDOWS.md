# InvoiceFlow — Guía de Instalación para Windows

## 📋 Requisitos Previos

### Software Necesario
1. **Python 3.12+** — [Descargar aquí](https://www.python.org/downloads/windows/)
2. **Git** (opcional) — [Descargar aquí](https://git-scm.com/download/win)

---

## 🚀 Instalación Paso a Paso

### Paso 1: Descargar e Instalar Python

1. **Abrí tu navegador** y visitá: [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)

2. **Hacé clic** en el botón **"Download Python 3.12.x"** (o la versión más reciente)

3. **Ejecutá el archivo descargado** (ejemplo: `python-3.12.x-amd64.exe`)

4. **IMPORTANTE**: Antes de hacer clic en "Install Now", marcá la opción:
   ```
   ☑ Add Python to PATH
   ```

5. **Hacé clic** en "Install Now"

6. **Esperá** a que termine la instalación (puede tardar 2-3 minutos)

7. **Verificá** la instalación:
   - Abrí el menú Inicio
   - Buscá "cmd" o "PowerShell"
   - Escribí:
   ```
   python --version
   ```
   - Debería mostrar: `Python 3.12.x`

---

### Paso 2: Descargar el Proyecto

#### Opción A: Descargar ZIP (más fácil)

1. **Ir a GitHub**: [https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque](https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque)

2. **Hacer clic** en el botón verde **"<> Code"**

3. **Hacer clic** en **"Download ZIP"**

4. **Guardar** el archivo en el Escritorio

5. **Extraer** el ZIP:
   - Clic derecho en el archivo `.zip`
   - "Extraer todo..."
   - Elegí el Escritorio como destino

6. **Renombrar** la carpeta a: `invoice_approval_system`

#### Opción B: Clonar con Git

1. **Abrir** PowerShell o Git Bash

2. **Navegar** al escritorio:
   ```
   cd Desktop
   ```

3. **Clonar** el repositorio:
   ```
   git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git invoice_approval_system
   ```

---

### Paso 3: Abrir la Carpeta del Proyecto

1. **Abrir** el Explorador de Archivos

2. **Navegar** a la carpeta del proyecto:
   ```
   Desktop/invoice_approval_system
   ```

3. **Verificar** que contiene archivos como:
   - `README.md`
   - `requirements.txt`
   - `INICIAR.bat`

---

### Paso 4: Instalar las Dependencias

1. **Abrir** PowerShell o Terminal:
   - Presioná `Win + X`
   - Seleccioná "Terminal de Windows" o "PowerShell"

2. **Navegar** a la carpeta del proyecto:
   ```
   cd Desktop/invoice_approval_system
   ```

3. **Crear un entorno virtual** (recomendado):
   ```
   python -m venv .venv
   ```

4. **Activar** el entorno virtual:
   ```
   .venv\Scripts\activate
   ```

5. **Instalar dependencias**:
   ```
   pip install -r requirements.txt
   ```

   > ⚠️ Esto puede tardar 3-5 minutos

---

### Paso 5: Iniciar el Sistema

#### Método Automático (Recomendado para principiantes)

1. **En el Explorador de Archivos**, navegar a la carpeta del proyecto

2. **Doble clic** en el archivo `INICIAR.bat`

3. **Se abrirán 3 ventanas** de terminal con los servicios

4. **Esperar** hasta ver mensajes como:
   ```
   [backend] Iniciando InvoiceFlow backend en puerto 8000
   ```

#### Método Manual

1. **Abrir** 3 terminales separadas (PowerShell)

2. **En la Terminal 1** — Supplier Service:
   ```
   cd Desktop/invoice_approval_system
   .venv\Scripts\activate
   python -m platform.services.supplier_service.main
   ```

3. **En la Terminal 2** — Contract Service:
   ```
   cd Desktop/invoice_approval_system
   .venv\Scripts\activate
   python -m platform.services.contract_service.main
   ```

4. **En la Terminal 3** — Backend:
   ```
   cd Desktop/invoice_approval_system\platform\backend
   .venv\Scripts\activate
   python main.py
   ```

---

## 🌐 Acceso al Sistema

Una vez iniciado, abrir el navegador y visitar:

| Servicio | URL |
|----------|-----|
| **Back Office** | [http://localhost:8000/](http://localhost:8000/) |
| **Portal del Proveedor** | [http://localhost:8000/supplier/](http://localhost:8000/supplier/) |
| **Documentación API (Backend)** | [http://localhost:8001/docs](http://localhost:8001/docs) |
| **Documentación API (Contracts)** | [http://localhost:8002/docs](http://localhost:8002/docs) |

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

### Error: "Python no encontrado"

```
'python' is not recognized
```

**Solución**:
1. Cerrar y reabrir la terminal
2. Si no funciona, reiniciar la PC
3. Verificar que Python esté en PATH

---

### Error: "Port already in use"

```
OSError: [WinError 10048]
```

**Solución**:
1. Cerrar otras aplicaciones que usen puertos (8000, 8001, 8002)
2. O ejecutar en CMD como administrador:
   ```
   netstat -ano | findstr :8000
   taskkill /PID <NUMERO> /F
   ```

---

### Error: "pip no reconocido"

```
'pip' is not recognized
```

**Solución**:
1. Usar `python -m pip` en vez de `pip`:
   ```
   python -m pip install -r requirements.txt
   ```

---

### Las ventanas se cierran inmediatamente

**Solución**:
1. Abrir PowerShell
2. Ejecutar manualmente para ver el error:
   ```
   cd Desktop/invoice_approval_system
   python -m platform.backend.main
   ```

---

## 📁 Estructura de Archivos

Después de instalar, deberías ver esta estructura:

```
invoice_approval_system/
├── README.md              ← Este archivo
├── requirements.txt       ← Dependencias de Python
├── INICIAR.bat          ← Script para iniciar (doble clic)
├── platform/
│   ├── backend/         ← Servidor principal (puerto 8000)
│   ├── frontend/       ← Interfaz del Back Office
│   └── services/       ← Microservicios
├── supplier_portal/    ← Portal del proveedor
├── agents/             ← Agentes del sistema
├── tools/              ← Herramientas
├── guardrails/         ← Reglas de validación
└── data/               ← Base de datos
```

---

## 🛑 Detener el Sistema

1. **Cerrar** las 3 ventanas de terminal

O ejecutar:
```
taskkill /F /IM python.exe
```

---

## ✅ Checklist de Verificación

Antes de reportar problemas, verificar:

- [ ] Python 3.12+ instalado (`python --version`)
- [ ] Entorno virtual activado (`.venv\Scripts\activate`)
- [ ] Dependencias instaladas (`pip list`)
- [ ] 3 terminales corriendo (o 1 con `INICIAR.bat`)
- [ ] Navegador abierto en `http://localhost:8000/`

---

## 📞 Necesitas Ayuda?

1. **Revisar** la sección de [Solución de Problemas](#-solución-de-problemas)
2. **Verificar** que cumples todos los [requisitos previos](#-requisitos-previos)
3. **Revisar** el archivo [CHANGELOG.md](CHANGELOG.md) para cambios recientes

---

**Última actualización**: 2025
**Versión del sistema**: 1.0.0
