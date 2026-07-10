# BUG-016: ABM de Proveedores + fecha emisión + validación de contrato con modo

## Severidad: **HIGH**
## Componente: `app/frontend/` + `app/services/supplier_service/` + `app/backend/orchestrator.py` + `tools/`
## Detectado por: Usuario quiere gestión completa de proveedores
## Fecha: 2026-07-09

---

## Descripción

El usuario pide **3 features críticas** que faltan en el sistema:

### 1. **Mostrar fecha de emisión en el listado**
- En el Inbox/Historial/Dashboard, agregar columna "Fecha emisión"
- Tomar el campo `invoice_date` que ya parsea el sistema

### 2. **ABM de Proveedores (CRUD completo)**
- Página nueva "🏢 Proveedores" en el sidebar del BackOffice
- Alta: formulario con CUIT, Razón Social, Condición IVA, Email, Teléfono, Rubro
- Lista: tabla con todos los proveedores
- Modificar: editar datos
- Eliminar: dar de baja lógica
- Búsqueda/filtros

### 3. **Alta de proveedor con contrato**
- En el formulario de alta, sección "📋 Contrato":
  - **Modo de validación** (radio buttons o checkbox):
    - ☐ **Monto exacto** - la factura debe ser EXACTAMENTE igual al límite contractual
    - ☑ **No superar monto** - la factura puede ser menor o igual al límite (default)
  - **Monto límite** del contrato (input numérico)
  - **Fecha inicio** / **Fecha vencimiento**
  - **Subir archivo** del contrato (TXT o PDF)
- Al guardar el proveedor, también se crea el contrato

### 4. **Validación de agente con modo de contrato**
- En `orchestrator.py`, leer el modo de validación del contrato del proveedor
- Si modo == "EXACTO": rechazar si `amount != contract_limit`
- Si modo == "NO_SUPERAR": rechazar si `amount > contract_limit` (lógica actual)

## Plan de Fix

### Backend
1. **`supplier_service/main.py`** - Agregar endpoints CRUD:
   - `POST /suppliers` - Alta con contrato
   - `PUT /suppliers/{id}` - Modificar
   - `DELETE /suppliers/{id}` - Baja lógica
   - `GET /suppliers` (mejorado) - con filtros
2. **Nueva tabla `contracts`** en `suppliers.db`:
   - `id`, `supplier_id`, `contract_limit`, `mode` (EXACTO/NO_SUPERAR), `start_date`, `end_date`, `file_path`, `uploaded_at`
3. **`orchestrator.py`** - Usar `mode` del contrato:
   - Si mode == "EXACTO" y amount != limit → REJECT
   - Si mode == "NO_SUPERAR" y amount > limit → REJECT
4. **Migración** de `invoices` table en suppliers.db para incluir `invoice_date`

### Frontend
5. **Nueva página `#page-proveedores`** con:
   - Lista de proveedores (tabla con CUIT, Razón Social, Estado, Contrato)
   - Botón "➕ Nuevo Proveedor"
   - Modal/form con todos los campos
6. **Sidebar** - agregar item "🏢 Proveedores"
7. **Listado de facturas** - agregar columna "Fecha emisión"

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

### 1. `app/services/supplier_service/main.py` - v2.0.0
- **Nueva tabla `contracts`** en `suppliers.db`:
  - `id`, `supplier_id`, `contract_limit`, `mode` (EXACTO/NO_SUPERAR), fechas, archivo
- **CRUD completo**:
  - `GET /suppliers` (con filtros q, status)
  - `POST /suppliers` (alta con `contract` opcional en el body)
  - `PUT /suppliers/{id}` (modificar)
  - `DELETE /suppliers/{id}` (baja lógica)
  - `GET /suppliers/{id}/contract`
  - `POST /suppliers/{id}/contract` (upsert)
  - `GET /contracts` (todos)
- **Endpoint clave `GET /suppliers/{id}/check?amount=N`** que valida con `mode`:
  - `EXACTO`: `within = abs(amount - limit) < 0.01`
  - `NO_SUPERAR`: `within = amount <= limit`
- Auto-generación de `supplier_id` (SUP006, SUP007, ...)
- Validación de CUIT duplicado

### 2. `app/backend/orchestrator.py` - usa supplier-service
- Reemplazado `contract_client.check_contract()` por `supplier_client.check_contract()`
- **Validación según modo**:
  - `EXACTO`: REJECT si `amount != contract_limit`
  - `NO_SUPERAR`: REJECT si `amount > contract_limit`

### 3. `app/backend/main.py` - proxy endpoints
- `GET /suppliers/proxy-list` (mismo origen, evita CORS)
- `GET /suppliers/proxy-contracts`
- `POST /suppliers/proxy-create`
- `PUT /suppliers/proxy-update/{id}` (incluye contrato)
- `DELETE /suppliers/proxy-delete/{id}`

### 4. Frontend - Nueva página "🏢 Proveedores"
- Sidebar: nuevo item
- **Lista** con tabla: ID, Razón Social, CUIT, Condición, Categoría, Email, Contrato, Modo, Límite, Estado, Acciones
- **Búsqueda** en tiempo real
- **Modal de Alta/Edición** con:
  - Datos del proveedor (ID opcional, Razón Social, CUIT, Estado, Categoría, Email, Teléfono)
  - **Sección Contrato**:
    - ☐ **No superar monto** (default)
    - ☑ **Monto exacto** (radio buttons)
    - Input de límite, fecha inicio/vencimiento, archivo
- **Acciones** por fila: Editar (✏️), Activar/Desactivar (🔒/🔓)

### 5. Fecha de emisión
- `InboxItem` Pydantic model incluye `invoice_date`
- Columna "Fecha emisión" en listado de Inbox
- Visible en la UI (header `Fecha emisión` agregado al `<thead>`)

## Verificación

```
=== ABM funciona ===
POST /suppliers/proxy-create (alta con contrato):
  Created: SUP010 - Proveedor Test SRL

=== Validación EXACTO ===
Created SUP011 con contrato EXACTO $100k
  Invoice $50k:  decision=REJECTED, reason="Contrato modo EXACTO: el monto $50,000 debe ser exactamente $100,000"
  Invoice $100k: decision=APPROVED, confirmation=PAY-8A953381

=== Fecha de emision ===
FC-0001-00000002.txt -> inv=FC-0001-00000002 date=2026-06-28
FC-0001-00000004.txt -> inv=FC-0001-00000004 date=2026-06-28
```

## Menú Sidebar actualizado

```
📊 Dashboard
📥 Inbox
📜 Historial
💬 Chat interno
🏢 Proveedores         <-- NUEVO
📡 Estado de Agentes
✅ Evaluación
📖 Docs
```