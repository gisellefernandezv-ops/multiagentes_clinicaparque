# InvoiceFlow — Guía de Instalación

## Requisitos del Sistema

### Software Necesario
- **Python 3.12+** (recomendado: 3.12.x)
- **Git** (opcional, para clonar el repositorio)
- **Windows 10/11** o **Linux/macOS**

### Verificar Python
```bash
python --version
# Debe mostrar: Python 3.12.x
```

---

## Instalación Paso a Paso

### 1. Obtener el Proyecto

Si ya tienes el proyecto en tu máquina, navega al directorio:
```bash
cd C:\Users\gisel\OneDrive\Escritorio\tp_multiagentes\invoice_approval_system
```

### 2. Crear un Entorno Virtual (Recomendado)

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno (Windows)
.venv\Scripts\activate

# Activar entorno (Linux/macOS)
source .venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

El archivo `requirements.txt` incluye:
```
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
httpx>=0.24.0
chromadb>=0.4.0
google-adk>=0.1.0
google-generativeai>=0.3.0
watchdog>=3.0.0
python-multipart>=0.0.6
```

### 4. Configurar Variables de Entorno (Opcional)

Crea un archivo `.env` en la raíz del proyecto:

```env
# API Keys (requeridas para RAG y ADK)
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

### 5. Verificar la Instalación

```bash
# Ejecutar test de imports
python test_import.py
```

Deberías ver:
```
✓ FastAPI importado
✓ Pydantic importado
✓ ChromaDB importado
✓ Google ADK importado
✓ Todos los módulos principales OK
```

---

## Iniciar el Sistema

### Método Automático (Recomendado)

Simplemente ejecuta el script de inicio:

```bash
# Windows
INICIAR.bat

# Linux/macOS
chmod +x INICIAR.sh
./INICIAR.sh
```

Esto abrirá 3 ventanas de terminal con los servicios.

### Método Manual

Abre 3 terminales separadas y ejecuta en cada una:

**Terminal 1 - Supplier Service (Puerto 8001)**
```bash
cd C:\Users\gisel\OneDrive\Escritorio\tp_multiagentes\invoice_approval_system
python -m platform.services.supplier_service.main
```

**Terminal 2 - Contract Service (Puerto 8002)**
```bash
cd C:\Users\gisel\OneDrive\Escritorio\tp_multiagentes\invoice_approval_system
python -m platform.services.contract_service.main
```

**Terminal 3 - Backend (Puerto 8000)**
```bash
cd C:\Users\gisel\OneDrive\Escritorio\tp_multiagentes\invoice_approval_system
cd platform\backend
python main.py
```

---

## Verificar que Todo Funciona

### Health Checks

Abre tu navegador y verifica cada servicio:

| Servicio | URL | Respuesta Esperada |
|----------|-----|-------------------|
| Backend | http://localhost:8000/ | Página del Back Office |
| Supplier Portal | http://localhost:8000/supplier/ | Portal del Proveedor |
| Supplier Service | http://localhost:8001/health | `{"service":"supplier-service",...}` |
| Contract Service | http://localhost:8002/health | `{"service":"contract-service",...}` |

### API Documentation

- FastAPI Docs (Backend): http://localhost:8000/docs
- Supplier Service: http://localhost:8001/docs
- Contract Service: http://localhost:8002/docs

---

## Datos de Prueba

### Proveedores de Demo

El sistema incluye 5 proveedores de prueba:

| ID | Nombre | CUIT | Estado |
|----|---------|------|--------|
| SUP001 | TechCorp SA | 30-71234567-0 | ACTIVE |
| SUP002 | Papeleria Norte SRL | 30-69874523-1 | ACTIVE |
| SUP003 | Servicios Rapidos SA | 30-70111222-3 | INACTIVE |
| SUP004 | Limpieza Total SRL | 30-70555666-7 | ACTIVE |
| SUP005 | Consultoria Digital SA | 30-71234999-2 | ACTIVE |

### Facturas de Prueba

El directorio `data/new invoices/` contiene facturas de prueba:
- `FC-2026-SUP001-NUEVA-1.txt`
- `FC-2026-SUP002-NUEVA-1.txt`
- etc.

---

## Resolución de Problemas

### Error: "Module not found"

```bash
# Reinstalar dependencias
pip install --force-reinstall -r requirements.txt
```

### Error: "Port already in use"

```bash
# Ver qué proceso usa el puerto
netstat -ano | findstr :8000

# Matar el proceso (reemplazar PID con el número)
taskkill /PID <PID> /F
```

### Error: "ChromaDB not found"

```bash
pip install chromadb>=0.4.0
```

### Error: "Google ADK not found"

```bash
pip install google-adk>=0.1.0
```

### Los servicios no inician

1. Verifica que Python esté en el PATH:
```bash
python --version
```

2. Verifica las dependencias:
```bash
pip list
```

3. Revisa los logs de cada servicio en las terminales

---

## Estructura de Puertos

```
┌─────────────────────────────────────────────────────────────┐
│                     localhost                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Puerto 8000 ──────► Backend (FastAPI)                    │
│                        ├── Back Office (/static)             │
│                        ├── Supplier Portal (/supplier)       │
│                        └── API REST (/docs)                  │
│                                                              │
│  Puerto 8001 ──────► Supplier Service                     │
│                        └── API REST (/docs)                  │
│                                                              │
│  Puerto 8002 ──────► Contract Service                      │
│                        └── API REST (/docs)                  │
│                                                              │
│  Puerto 8003 ──────► External Auditor (A2A) [opcional]    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuración Avanzada

### Cambiar Puertos

Edita `platform/backend/settings.py`:

```python
class Settings(BaseSettings):
    port: int = 8000  # Cambiar aquí
    
    supplier_service_url: str = "http://127.0.0.1:8001"
    contract_service_url: str = "http://127.0.0.1:8002"
```

### Deshabilitar Watcher Automático

```env
INV_ENABLE_WATCHER=false
```

### Configurar ChromaDB

El directorio de ChromaDB se crea automáticamente en:
```
platform/data/chroma_db/
```

---

## Desinstalación

Para detener todos los servicios:
1. Cierra las ventanas de terminal
2. O ejecuta:
```bash
python stop_all.bat
```

Para eliminar el entorno virtual:
```bash
rmdir /s /q .venv
```

---

## Soporte

Si tienes problemas:
1. Revisa los logs en las terminales de servicios
2. Verifica que todos los puertos estén disponibles
3. Asegúrate de tener Python 3.12+ instalado
4. Comprueba que todas las dependencias estén instaladas

---

## Próximos Pasos

Una vez instalado, consulta:
- [README.md](README.md) — Descripción general del sistema
- [CHANGELOG.md](CHANGELOG.md) — Historial de cambios
- Documentos en [docs/](docs/) — Especificaciones técnicas
