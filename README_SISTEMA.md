# Sistema de Aprobación de Facturas - InvoiceFlow

## 📋 Descripción General

Sistema multiagente de aprobación de facturas de proveedores, desarrollado con Google ADK (Agent Development Kit). Gestiona el flujo completo desde la recepción de facturas hasta su aprobación o rechazo.

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
├─────────────────────────────────────────────────────────────────┤
│  🏢 Portal del Proveedor          📊 Back Office Empresa       │
│  (supplier_portal/)              (platform/frontend/)           │
│  - Login con CUIT/ID              - Dashboard                   │
│  - Ver facturas                   - Ver facturas pendientes     │
│  - Chat con empresa               - Agrupar facturas (IA)       │
│  - Estado de facturas             - Chat para procesar          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                        BACKEND (FastAPI)                        │
│  Puerto 8000                                                   │
│  - /supplier/*         → Portal proveedor                       │
│  - /new-invoices/*     → Gestión facturas                       │
│  - /inbox/*            → Inbox empresarial                      │
│  - /chat               → Chat con IA                            │
│  - /health             → Estado del sistema                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                   GOOGLE ADK - AGENTES IA                        │
│  Puerto 8000 (adk web)                                          │
│                                                                  │
│  ┌─────────────────┐                                            │
│  │ invoice_orchestrator │  ← Agente principal                    │
│  │  (Root Agent)     │                                          │
│  └────────┬────────┘                                            │
│           │                                                     │
│  ┌────────┴────────┬──────────┬──────────────┐                 │
│  │                 │          │              │                 │
│  ▼                 ▼          ▼              ▼                 │
│ validator_    contract_   payment_     invoice_              │
│ agent         agent        agent       manager_agent            │
│               │                                     │            │
│               ▼                                     ▼            │
│           ChromaDB                           new invoices       │
│           (RAG)                              (carpetas)         │
└─────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                   BASE DE DATOS (SQLite)                        │
│  payments.db                                                   │
│  - suppliers    → Proveedores registrados                       │
│  - invoices    → Facturas históricas con estados               │
│  - payments    → Registros de aprobación/rechazo              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agentes IA (Google ADK)

### 1. invoice_orchestrator (Root Agent)
Agente principal que coordina todo el flujo.

**Flujo:**
1. Identificar proveedor (CUIT/Nombre/ID)
2. Extraer datos del PDF
3. Aplicar guardrail estructural
4. Validar proveedor (validator_agent)
5. Verificar contrato (contract_agent)
6. Registrar pago (payment_agent)

### 2. validator_agent
Valida que el proveedor exista y esté activo en el sistema.

**Herramientas:**
- `supplier_lookup_tool` → Consulta base de datos SQLite

**Respuesta al usuario:**
```
"Hola TechCorp SA, este es el portal para la gestión de facturación. 
¿Querés adjuntar una factura? o ¿Querés consultar el estado de una factura ya enviada?"
```

### 3. contract_agent
Verifica el contrato vigente del proveedor y el límite de facturación.

**Herramientas:**
- `rag_tool` → Búsqueda en ChromaDB de contratos

### 4. payment_agent
Registra el resultado de la aprobación en la base de datos.

**Herramientas:**
- `register_payment_tool` → Inserta en tabla payments

### 5. invoice_manager_agent
Gestiona las facturas entrantes en la carpeta `new invoices`.

**Herramientas:**
- `list_pending_invoices` → Lista facturas pendientes
- `create_supplier_folder` → Crea carpeta por CUIT
- `move_invoice_to_folder` → Mueve facturas
- `group_invoices_by_supplier` → Agrupa automáticamente

---

## 🗄️ Base de Datos

### Tabla: suppliers
```sql
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY,
    supplier_id TEXT UNIQUE,      -- ej: "SUP001"
    name TEXT,                   -- ej: "TechCorp SA"
    cuit TEXT UNIQUE,            -- ej: "30-71234567-0"
    status TEXT DEFAULT 'ACTIVE',-- ACTIVE/INACTIVE
    category TEXT,
    registration_date TEXT,
    email TEXT,
    phone TEXT,
    address TEXT
);
```

### Tabla: invoices
```sql
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    invoice_id TEXT UNIQUE,      -- ej: "FC-2026-SUP001-001"
    supplier_id TEXT,
    amount REAL,
    currency TEXT DEFAULT 'ARS',
    invoice_date TEXT,           -- formato: YYYY-MM-DD
    state TEXT,                  -- APPROVED/REJECTED/PENDING/ESCALATED
    rejection_reason TEXT,
    confirmation_id TEXT,
    registered_at TIMESTAMP
);
```

### Proveedores de Prueba
| ID | Nombre | CUIT | Estado |
|----|--------|------|--------|
| SUP001 | TechCorp SA | 30-71234567-0 | ACTIVE |
| SUP002 | Papeleria Norte SRL | 30-69874523-1 | ACTIVE |
| SUP003 | Servicios Rapidos SA | 30-70111222-3 | INACTIVE |
| SUP004 | Limpieza Total SRL | 30-70555666-7 | ACTIVE |
| SUP005 | Consultoria Digital SA | 30-71234999-2 | ACTIVE |

---

## 📁 Estructura de Archivos

```
invoice_approval_system/
├── agent.py                      # Entry point ADK
├── agents/
│   ├── orchestrator.py          # Agente principal
│   ├── validator_agent.py        # Valida proveedores
│   ├── contract_agent.py         # Verifica contratos (RAG)
│   ├── payment_agent.py          # Registra pagos
│   └── invoice_manager_agent.py  # Gestor de facturas
├── tools/
│   ├── supplier_mcp_tool.py     # Consulta proveedores (SQLite)
│   ├── payment_db_tool.py        # Registra pagos
│   ├── rag_tool.py              # Búsqueda RAG
│   ├── folder_manager_tool.py    # Gestor de carpetas
│   └── pdf_extractor_tool.py     # Extrae datos de PDF
├── guardrails/
│   └── invoice_guardrail.py      # Validación estructural
├── data/
│   ├── payments.db              # Base de datos SQLite
│   ├── chroma_db/              # Vector DB para RAG
│   ├── contracts/               # Contratos PDF
│   └── new invoices/            # Facturas pendientes
│       ├── FC-2026-SUP001-NUEVA-1.txt
│       ├── ...
│       └── CUIT-30712345670/    # Carpetas por proveedor
├── platform/                    # Backend + Frontend
│   ├── backend/
│   │   ├── main.py
│   │   ├── supplier_portal_router.py
│   │   ├── new_invoices_router.py
│   │   └── inbox_router.py
│   └── frontend/
│       ├── index.html
│       ├── app.js
│       └── style.css
└── supplier_portal/            # Portal del proveedor
    ├── index.html
    └── style.css
```

---

## 🌐 URLs del Sistema

### Backend API
- **http://localhost:8000** → Frontend Back Office
- **http://localhost:8000/supplier/portal** → Portal del Proveedor
- **http://localhost:8000/health** → Estado del sistema
- **http://localhost:8000/new-invoices** → Lista facturas pendientes
- **http://localhost:8000/supplier/invoices/{id}** → Facturas de proveedor

### Agente ADK
- **http://localhost:8000** → UI de Google ADK (si se usa `adk web`)

---

## 🚀 Cómo Iniciar

### Opción 1: Backend + Frontend
```batch
cd invoice_approval_system
python run_platform.py
```
Acceder a: http://localhost:8000

### Opción 2: Agente ADK (Chat con IA)
```batch
cd invoice_approval_system
adk web .
```
Acceder a: http://localhost:8000

---

## 📊 Funcionalidades por Portal

### 🏢 Portal del Proveedor
- ✅ Login con CUIT, nombre o ID de proveedor
- ✅ Ver lista de facturas propias con estados
- ✅ Filtrar por estado (Aprobadas/Pendientes/Rechazadas)
- ✅ Ver detalle de cada factura
- ✅ Chat con el departamento de cuentas a pagar

### 📊 Back Office Empresa
- ✅ Dashboard con estadísticas
- ✅ Subir y procesar facturas
- ✅ Ver inbox de facturas pendientes
- ✅ Botón "Ver facturas" → Abre modal con facturas en `new invoices`
- ✅ Botón "Agrupar facturas" → Ejecuta agente agrupador (crea carpetas por CUIT)
- ✅ Chat para procesar facturas con IA
- ✅ Historial de pagos procesados

---

## 🔄 Flujo de Agrupación de Facturas

```
1. Proveedor envía factura → carpeta "new invoices"
         ↓
2. Usuario ejecuta "Agrupar facturas"
         ↓
3. Sistema extrae CUIT de cada factura
         ↓
4. Crea carpeta "CUIT-XXXXXXXXXXX"
         ↓
5. Mueve factura a la carpeta correspondiente
         ↓
Resultado:
├── new invoices/
│   ├── CUIT-30712345670/
│   │   ├── FC-2026-SUP001-NUEVA-1.txt
│   │   └── FC-2026-SUP001-NUEVA-2.txt
│   ├── CUIT-30698745231/
│   │   └── FC-2026-SUP002-NUEVA-1.txt
│   └── ... (más carpetas)
```

---

## 📝 Reglas de Negocio (Guardrails)

1. **Monto > $500.000** → ESCALATED (revisión humana obligatoria)
2. **Monto <= 0** → REJECTED
3. **Campos obligatorios faltantes** → REJECTED
4. **Fecha mal formada** → REJECTED
5. **Proveedor inactivo** → REJECTED
6. **Monto excede límite contractual** → REJECTED

---

## 🔧 Tecnologías

- **Google ADK** - Framework de agentes de IA
- **Gemini 2.5 Flash** - Modelo de lenguaje
- **FastAPI** - Backend REST
- **SQLite** - Base de datos
- **ChromaDB** - Vector store para RAG
- **Python 3.12** - Runtime

---

## 📄 Facturas de Prueba

Se generaron **15 facturas históricas** en la base de datos y **15 facturas nuevas** en `data/new invoices/`:

### Históricas (en BD)
| Proveedor | Aprobadas | Rechazadas | Pendientes |
|-----------|-----------|------------|------------|
| SUP001 | 1 | 1 | 1 |
| SUP002 | 1 | 1 | 1 |
| SUP003 | 1 | 1 | 1 |
| SUP004 | 1 | 1 | 1 |
| SUP005 | 1 | 1 | 1 |

### Nuevas (en carpeta)
```
data/new invoices/
├── FC-2026-SUP001-NUEVA-1.txt
├── FC-2026-SUP001-NUEVA-2.txt
├── FC-2026-SUP001-NUEVA-3.txt
├── FC-2026-SUP002-NUEVA-1.txt
├── FC-2026-SUP002-NUEVA-2.txt
├── FC-2026-SUP002-NUEVA-3.txt
├── FC-2026-SUP003-NUEVA-1.txt
├── FC-2026-SUP003-NUEVA-2.txt
├── FC-2026-SUP003-NUEVA-3.txt
├── FC-2026-SUP004-NUEVA-1.txt
├── FC-2026-SUP004-NUEVA-2.txt
├── FC-2026-SUP004-NUEVA-3.txt
├── FC-2026-SUP005-NUEVA-1.txt
├── FC-2026-SUP005-NUEVA-2.txt
└── FC-2026-SUP005-NUEVA-3.txt
```

---

## 👥 Usuarios de Prueba

### Proveedores
Ingresá cualquiera de estos identificadores en el portal:
- `SUP001`, `SUP002`, `SUP003`, `SUP004`, `SUP005`
- `30-71234567-0`, `30-69874523-1`, etc.
- `TechCorp`, `Papeleria`, etc.

### Empresa (Back Office)
El sistema valida automáticamente con la base de datos de proveedores.

---

## 📞 Soporte

Para consultas técnicas o de uso, contactar al departamento de sistemas.
