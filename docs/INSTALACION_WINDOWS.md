# InvoiceFlow — Guía de Instalación para Windows

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

| Software | Versión Mínima | Descarga |
|----------|---------------|----------|
| **Python** | 3.12+ | [python.org](https://www.python.org/downloads/windows/) |
| **Git** | 2.0+ (opcional) | [git-scm.com](https://git-scm.com/download/win) |

### Verificar Python

1. Abrir Command Prompt o PowerShell
2. Escribir:
```bash
python --version
```
3. Debería mostrar: `Python 3.12.x`

---

## 2. Instalación Paso a Paso

### Paso 1: Instalar Python

1. **Descargar** Python desde [python.org/downloads/windows/](https://www.python.org/downloads/windows/)

2. **Ejecutar** el instalador (`python-3.12.x-amd64.exe`)

3. **IMPORTANTE**: Antes de instalar, marcar:
```
☑ Add Python to PATH
```

4. **Instalar** clicking "Install Now"

5. **Verificar** en CMD:
```bash
python --version
```

### Paso 2: Descargar el Proyecto

#### Opción A: Descargar ZIP (Recomendado para principiantes)

1. Ir a [GitHub](https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque)

2. Click en botón verde **"<> Code"**

3. Click en **"Download ZIP"**

4. Guardar en Escritorio

5. **Extraer** el ZIP:
   - Click derecho → "Extraer todo..."
   - Elegir destino: Escritorio

6. **Renombrar** carpeta a: `invoice_approval_system`

#### Opción B: Clonar con Git

```bash
cd Desktop
git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git invoice_approval_system
```

### Paso 3: Crear Entorno Virtual

1. **Abrir** PowerShell o CMD en la carpeta del proyecto:
```bash
cd Desktop\tp_multiagentes\invoice_approval_system
```

2. **Crear** entorno virtual:
```bash
python -m venv .venv
```

3. **Activar** el entorno:
```bash
.venv\Scripts\activate
```

> ✅ Verás `(.venv)` al inicio de la línea

### Paso 4: Instalar Dependencias

```bash
pip install -r requirements.txt
```

> ⏳ Puede tardar 3-5 minutos

### Paso 5: Configurar Variables de Entorno

```bash
# Copiar plantilla
copy .env.example .env

# Editar con bloc de notas
notepad .env
```

Agregar tu API Key de Google:
```env
GOOGLE_API_KEY=tu_api_key_aqui
```

### Paso 6: Indexar Contratos (Primera vez)

```bash
python rag/ingest.py
```

---

## 3. Inicio del Sistema

### Método Automático (Recomendado)

1. **Abrir** el Explorador de Archivos
2. **Navegar** a la carpeta del proyecto
3. **Doble clic** en `INICIAR.bat`
4. **Esperar** a que se abran 3 ventanas de terminal

### Método Manual (3 terminales)

#### Terminal 1 — Supplier Service (Puerto 8001)

```bash
cd Desktop\invoice_approval_system
.venv\Scripts\activate
python -m platform.services.supplier_service.main
```

#### Terminal 2 — Contract Service (Puerto 8002)

```bash
cd Desktop\invoice_approval_system
.venv\Scripts\activate
python -m platform.services.contract_service.main
```

#### Terminal 3 — Backend (Puerto 8000)

```bash
cd Desktop\invoice_approval_system\platform\backend
.venv\Scripts\activate
python main.py
```

---

## 4. Acceso y Verificación

### URLs del Sistema

| Servicio | URL | Verificación |
|----------|-----|--------------|
| **Back Office** | http://localhost:8000/ | Página principal de administración |
| **Supplier Portal** | http://localhost:8000/supplier/ | Portal del proveedor |
| **API Backend** | http://localhost:8000/docs | Documentación Swagger |
| **API Supplier** | http://localhost:8001/docs | API de proveedores |
| **API Contract** | http://localhost:8002/docs | API de contratos |

### Health Checks

```bash
# Verificar servicios
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

Respuesta esperada:
```json
{"status": "ok", "service": "..."}
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

3. Click en "Ingresar"

---

## 5. Solución de Problemas

### Error: "Python no encontrado"

```
'python' is not recognized
```

**Solución**:
1. Cerrar y reabrir terminal
2. Reiniciar PC
3. Si persiste, desinstalar y reinstallar Python marcando "Add to PATH"

---

### Error: "Port already in use" (Error 10048)

```
OSError: [WinError 10048]
```

**Solución**:
```bash
# Identificar proceso
netstat -ano | findstr :8000

# Matar proceso (ejemplo: PID 1234)
taskkill /PID 1234 /F
```

Para todos los puertos:
```bash
taskkill /F /IM python.exe
```

---

### Error: "pip no reconocido"

```
'pip' is not recognized
```

**Solución**:
```bash
python -m pip install -r requirements.txt
```

---

### Error: "ModuleNotFoundError"

```
ModuleNotFoundError: No module named '...'
```

**Solución**:
```bash
# Asegurarse que el entorno virtual está activo
.venv\Scripts\activate

# Reinstalar dependencias
pip install --force-reinstall -r requirements.txt
```

---

### Las ventanas se cierran inmediatamente

**Solución**:
1. Abrir PowerShell manualmente
2. Ejecutar comando para ver error:
```bash
cd Desktop\invoice_approval_system
.venv\Scripts\activate
python -m platform.services.supplier_service.main
```

---

### Error de Encoding (tildes)

```
UnicodeEncodeError: 'charmap' codec
```

**Solución**:
Agregar al inicio de scripts `.bat`:
```batch
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
```

---

## 6. Estructura de Archivos

```
invoice_approval_system/
├── README.md                   # Documentación principal
├── CHANGELOG.md               # Historial de cambios
├── requirements.txt           # Dependencias Python
│
├── INICIAR.bat               # Script de inicio automático
├── setup.bat                 # Script de instalación
├── smoke_test.bat            # Verificación de componentes
│
├── platform/                  # Backend y servicios
│   ├── backend/              # Servidor principal (8000)
│   │   └── main.py
│   ├── frontend/            # Back Office
│   └── services/            # Microservicios
│       ├── supplier_service/
│       └── contract_service/
│
├── agents/                   # Agentes ADK
│   ├── orchestrator.py
│   ├── validator_agent.py
│   ├── contract_agent.py
│   ├── payment_agent.py
│   ├── router_agent.py
│   └── invoice_manager_agent.py
│
├── tools/                   # Herramientas
│   ├── supplier_mcp_tool.py
│   ├── rag_tool.py
│   ├── payment_db_tool.py
│   └── ...
│
├── guardrails/             # Sistema de guardrails
│   ├── rules.yaml
│   └── guardrail_engine.py
│
├── rag/                    # RAG (ChromaDB)
│   ├── ingest.py
│   └── retriever.py
│
├── ml/                     # Machine Learning
│   └── risk_model.py
│
├── supplier_portal/        # Portal del proveedor
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── a2a/                    # Agente A2A externo
│   └── external_auditor_agent/
│
├── data/                   # Datos persistentes
│   ├── payments.db         # SQLite (auto-generado)
│   ├── chroma_db/         # Vector store (auto-generado)
│   ├── contracts/         # Contratos .txt
│   └── new_invoices/      # Facturas pendientes
│
└── docs/                   # Documentación adicional
    ├── especificacion_sistema_invoiceflow.md
    ├── documento_guardrails_invoiceflow.md
    ├── GUIA_RAPIDA.md
    ├── INSTALACION_WINDOWS.md
    ├── INSTALACION_LINUX.md
    └── INSTALACION_MACOS.md
```

---

## 🛑 Detener el Sistema

### Método 1: Cerrar ventanas
Cerrar las 3 ventanas de terminal

### Método 2: Matar procesos
```bash
taskkill /F /IM python.exe
```

### Método 3: Script incluido
Ejecutar `stop_all.bat` en la carpeta del proyecto

---

## ✅ Checklist de Verificación

Antes de reportar problemas, verificar:

- [ ] Python 3.12+ instalado (`python --version`)
- [ ] Entorno virtual activado (`(.venv)` visible)
- [ ] Dependencias instaladas (`pip list`)
- [ ] Archivo `.env` creado con `GOOGLE_API_KEY`
- [ ] 3 terminales corriendo
- [ ] Navegador en `http://localhost:8000/`

---

## 📞 Necesitas Ayuda?

1. Revisar la sección de [Solución de Problemas](#5-solución-de-problemas)
2. Verificar que cumples todos los requisitos
3. Revisar logs en las terminales para identificar errores
4. Consultar [README.md](../README.md) para documentación completa

---

## Enlaces Útiles

| Recurso | URL |
|---------|-----|
| Repositorio GitHub | https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque |
| Documentación ADK | https://google.github.io/adk-docs/ |
| API Gemini | https://ai.google.dev/ |
| FastAPI | https://fastapi.tiangolo.com/ |

---

**Versión del sistema**: 1.0.0  
**Última actualización**: 2025-06-20
