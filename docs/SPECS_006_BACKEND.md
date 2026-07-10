# SPECS 006 — Backend API

> **Proyecto**: InvoiceFlow  
> **Tipo**: Especificación de API  
> **Estado**: ✅ Implementado

---

## 1. Arquitectura de Servicios

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PUERTO 8000                                    │
│                         BACKEND PRINCIPAL                                │
│                        (FastAPI + Uvicorn)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐│
│  │  /inbox         │  │  /chat          │  │  /new-invoices         ││
│  │  (Router)       │  │  (Router)       │  │  (Router)               ││
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘│
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                    SUPPLIER PORTAL ROUTER                          ││
│  │  /supplier/validate  /supplier/invoices/{id}                       ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                    WATCHER (File System)                           ││
│  │  Monitorea carpeta /new-invoices                                   ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
┌───────────────┐            ┌───────────────┐
│ PUERTO 8001  │            │ PUERTO 8002  │
│ Supplier      │            │ Contract      │
│ Service       │            │ Service       │
└───────────────┘            └───────────────┘
```

---

## 2. Routers del Backend

### 2.1 inbox_router.py

**Prefijo**: `/inbox`

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/inbox` | Listar facturas pendientes |
| POST | `/inbox/upload` | Subir factura al inbox |
| POST | `/inbox/process/{filename}` | Procesar factura específica |
| POST | `/inbox/process-all` | Procesar todas las facturas |
| POST | `/invoices` | Procesar factura directamente |
| GET | `/invoices` | Listar facturas procesadas |
| GET | `/dashboard` | Estadísticas del dashboard |

### 2.2 chat_router.py

**Prefijo**: `/chat`

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| POST | `/chat` | Enviar mensaje de chat |

**Modelo de Request**:
```python
class ChatMessage(BaseModel):
    message: str
```

**Intenciones Soportadas**:
- `process_all` — Procesar todo el inbox
- `process_one` — Procesar factura específica
- `process_path` — Procesar por path
- `list_inbox` — Listar facturas
- `history` — Ver historial de pagos

### 2.3 new_invoices_router.py

**Prefijo**: `/new-invoices`

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/new-invoices` | Listar facturas |
| GET | `/new-invoices/content` | Ver contenido |
| POST | `/new-invoices/group-invoices` | Agrupar por proveedor |
| GET | `/new-invoices/folders` | Listar carpetas |

### 2.4 supplier_portal_router.py

**Prefijo**: `/supplier`

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/supplier/portal` | Página del portal |
| POST | `/supplier/validate` | Validar proveedor |
| GET | `/supplier/invoices/{supplier_id}` | Facturas del proveedor |

---

## 3. Modelos de Datos

### 3.1 InvoiceIn

```python
class InvoiceIn(BaseModel):
    invoice_id: str
    supplier_id: str
    supplier_name: Optional[str] = None
    amount: float
    currency: str = "ARS"
    invoice_date: str  # YYYY-MM-DD
```

### 3.2 InvoiceResult

```python
class InvoiceResult(BaseModel):
    decision: str
    invoice_id: str
    supplier_id: str
    amount: float
    rejection_reason: str
    confirmation_id: str
    payment_status: str
    guardrail_action: str
    guardrail_reason: str
    validation: dict = {}
    contract: dict = {}
```

### 3.3 ChatResponse

```python
class ChatResponse(BaseModel):
    intent: str
    message: str
    data: Optional[dict] = None
```

---

## 4. Microservicios

### 4.1 Supplier Service (Puerto 8001)

**Ubicación**: `app/services/supplier_service/main.py`

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/health` | Health check |
| GET | `/suppliers` | Listar todos los proveedores |
| GET | `/suppliers/{id}` | Obtener proveedor |
| POST | `/suppliers` | Crear proveedor |
| PUT | `/suppliers/{id}/status` | Actualizar estado |
| POST | `/suppliers/seed` | Cargar datos demo |

### 4.2 Contract Service (Puerto 8002)

**Ubicación**: `app/services/contract_service/main.py`

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/health` | Health check |
| POST | `/contracts/upload` | Subir contrato |
| GET | `/contracts` | Listar contratos |
| GET | `/contracts/{id}/check` | Verificar límite |
| POST | `/contracts/seed` | Cargar demo |

---

## 5. Settings del Backend

```python
class Settings(BaseSettings):
    # URLs de microservicios
    supplier_service_url: str = "http://127.0.0.1:8001"
    contract_service_url: str = "http://127.0.0.1:8002"

    # Watcher
    enable_watcher: bool = True
    watch_interval_seconds: float = 2.0

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Paths
    data_dir: Path          # app/data
    inbox_dir: Path         # app/data/inbox
    processed_dir: Path     # app/data/processed
    rejected_dir: Path      # app/data/rejected
    payments_db: Path       # data/payments.db
    frontend_dir: Path       # app/frontend
```

---

## 6. Rutas de Archivos

| Variable | Ruta Absoluta |
|---------|---------------|
| `PROJECT_ROOT` | `invoice_approval_system/` |
| `app/data/` | `invoice_approval_system/app/data/` |
| `inbox_dir` | `invoice_approval_system/app/data/inbox/` |
| `processed_dir` | `invoice_approval_system/app/data/processed/` |
| `rejected_dir` | `invoice_approval_system/app/data/rejected/` |
| `suppliers.db` | `invoice_approval_system/app/data/suppliers.db` |
| `payments.db` | `invoice_approval_system/data/payments.db` |

---

## 7. Health Check

### 7.1 Endpoint Principal (8000)

```bash
GET /health
```

**Respuesta**:
```json
{
  "service": "invoiceflow-backend",
  "status": "ok",
  "version": "1.0.0",
  "watcher_enabled": true,
  "microservices": {
    "supplier-service": {...},
    "contract-service": {...}
  },
  "paths": {
    "inbox": "...",
    "processed": "...",
    "rejected": "..."
  }
}
```

---

## 8. CORS

El backend tiene CORS habilitado para todos los orígenes:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 9. Referencias

| Documento | Descripción |
|-----------|-------------|
| `app/backend/main.py` | Punto de entrada |
| `app/backend/settings.py` | Configuración |
| `app/backend/orchestrator.py` | Orquestador HTTP |
| `SPECS_007_FRONTEND.md` | Frontend que consume esta API |

---

**Versión**: 2.0.0  
**Última actualización**: 2026-07-15
