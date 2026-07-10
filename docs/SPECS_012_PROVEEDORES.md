# SPECS 012 — ABM de Proveedores y Contratos

> **Proyecto**: InvoiceFlow
> **Tipo**: Especificación de Funcionalidad
> **Versión**: 2.0.0
> **Fecha**: 2026-07-15
> **Estado**: ✅ Implementado

---

## 1. Propósito

Esta spec describe el sistema de **Alta, Baja y Modificación (ABM)** de proveedores y sus contratos, integrado con el flujo de validación de facturas.

## 2. Alcance

### 2.1 Incluido

- CRUD completo de proveedores
- Asignación de contrato con modo de validación (EXACTO / NO_SUPERAR)
- Búsqueda y filtrado de proveedores
- Estados: ACTIVE / INACTIVE / SUSPENDED
- Validación de CUIT único
- Auto-generación de supplier_id (SUP00X)
- UI en BackOffice con modal de alta/edición

### 2.2 No Incluido

- Búsqueda por geolocalización
- Subida real de archivos PDF del contrato (sólo se guarda el nombre)
- Multi-idioma
- ABM desde Supplier Portal (los proveedores no se auto-registran)

## 3. Modelo de Datos

### 3.1 Tabla `suppliers`

```sql
CREATE TABLE suppliers (
    supplier_id   TEXT PRIMARY KEY,    -- SUP00X (auto-generado)
    name          TEXT NOT NULL,
    cuit          TEXT NOT NULL UNIQUE,
    status        TEXT NOT NULL CHECK(status IN ('ACTIVE','INACTIVE','SUSPENDED')),
    category      TEXT,
    email         TEXT,
    phone         TEXT,
    registered_at TEXT NOT NULL         -- ISO 8601
);
```

### 3.2 Tabla `contracts` (NUEVA - BUG-016)

```sql
CREATE TABLE contracts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id     TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE CASCADE,
    contract_limit  REAL NOT NULL,
    mode            TEXT NOT NULL CHECK(mode IN ('EXACTO','NO_SUPERAR')),
    start_date      TEXT,
    end_date        TEXT,
    file_path       TEXT,
    uploaded_at     TEXT NOT NULL
);
```

### 3.3 Reglas de Negocio

1. **CUIT único**: no puede haber dos proveedores con el mismo CUIT
2. **supplier_id único**: generado automáticamente (SUP001, SUP002, ...)
3. **Baja lógica**: DELETE marca `status = INACTIVE` (no borra el registro)
4. **Contrato único por proveedor**: PUT/POST en `/suppliers/{id}/contract` reemplaza el anterior
5. **Modo EXACTO**: la factura debe ser **EXACTAMENTE** igual al límite
6. **Modo NO_SUPERAR** (default): la factura puede ser **menor o igual** al límite

## 4. API REST

### 4.1 Endpoints del Supplier Service (8001)

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/suppliers` | Lista todos (con filtros `?status=&q=`) |
| GET | `/suppliers/{id}` | Obtiene uno por ID |
| POST | `/suppliers` | Alta (con contrato opcional en body) |
| PUT | `/suppliers/{id}` | Modificar datos |
| DELETE | `/suppliers/{id}` | Baja lógica (status=INACTIVE) |
| PUT | `/suppliers/{id}/status` | Cambio rápido de estado |
| GET | `/suppliers/{id}/contract` | Obtener contrato |
| POST | `/suppliers/{id}/contract` | Crear/reemplazar contrato |
| GET | `/contracts` | Listar todos los contratos |
| **GET** | **`/suppliers/{id}/check?amount=N`** | **Validar factura contra contrato** |

### 4.2 Proxy Endpoints (Backend 8000)

Para evitar CORS, el backend expone estos endpoints same-origin:

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/suppliers/proxy-list` | Lista todos |
| GET | `/suppliers/proxy-contracts` | Lista contratos |
| POST | `/suppliers/proxy-create` | Alta |
| PUT | `/suppliers/proxy-update/{id}` | Modificar (incluye contrato) |
| DELETE | `/suppliers/proxy-delete/{id}` | Baja lógica |

## 5. Flujos de Uso

### 5.1 Alta de Proveedor con Contrato EXACTO

```
1. Usuario abre BackOffice → 🏢 Proveedores → ➕ Nuevo Proveedor
2. Completa formulario:
   - Razón Social: "TechCorp SA"
   - CUIT: "30-12345678-9" (validado que no exista)
   - Modo contrato: ⦿ Monto exacto
   - Límite: $150,000
   - Fechas: 2026-01-01 a 2027-01-01
3. Click "Crear proveedor"
4. Backend: POST /suppliers/proxy-create
5. supplier-service: INSERT suppliers + INSERT contracts (con mode=EXACTO)
6. Auto-genera supplier_id: SUP006
7. Respuesta: {supplier_id: "SUP006", ...}
8. UI: toast "Proveedor creado" + recarga la tabla
```

### 5.2 Validación de Factura (Modo EXACTO)

```
1. Proveedor SUBE factura de $50,000
2. orchestrator llama supplier_client.check_contract("SUP006", 50000)
3. supplier-service consulta contracts WHERE supplier_id = 'SUP006'
4. Encuentra: contract_limit=150000, mode='EXACTO'
5. Validación: abs(50000 - 150000) > 0.01 → NO EXACTO
6. Retorna: {found: true, within_limit: false, mode: 'EXACTO'}
7. orchestrator: REJECTED con razón "Contrato modo EXACTO: el monto $50,000 debe ser exactamente $150,000"
```

## 6. Frontend

### 6.1 Página "Proveedores" en BackOffice

- **URL**: BackOffice → sidebar → 🏢 Proveedores
- **Tabla con**: ID, Razón Social, CUIT, Categoría, Email, Teléfono, Contrato (✅/❌), Modo (🎯 Exacto / ≤ No superar), Límite, Estado, Acciones
- **Búsqueda** en tiempo real (filtra por nombre/CUIT/ID)
- **Botones por fila**:
  - ✏️ Editar (abre modal con datos pre-cargados)
  - 🔒/🔓 Activar/Desactivar
- **Botón ➕ Nuevo Proveedor** (abre modal vacío)

### 6.2 Modal de Alta/Edición

```html
<form id="supplier-form">
  <fieldset>
    <legend>📋 Datos del Proveedor</legend>
    <input id="f-supplier_id" placeholder="SUP00X (autogenerado)">
    <input id="f-name" required>           <!-- Razón Social -->
    <input id="f-cuit" required>           <!-- CUIT -->
    <select id="f-status">                 <!-- ACTIVE/INACTIVE -->
    <input id="f-category">                <!-- Categoría -->
    <input id="f-email">                   <!-- Email -->
    <input id="f-phone">                   <!-- Teléfono -->
  </fieldset>
  
  <fieldset>
    <legend>📋 Contrato (opcional)</legend>
    <input type="radio" name="mode" value="NO_SUPERAR" checked>
      ≤ No superar monto
    <input type="radio" name="mode" value="EXACTO">
      🎯 Monto exacto
    
    <input id="f-contract_limit" type="number">
    <input id="f-start_date" type="date">
    <input id="f-end_date" type="date">
    <input id="f-contract_file" type="file" accept=".txt,.pdf">
  </fieldset>
</form>
```

## 7. Integración con otros Componentes

- **Orchestrator** (BUG-016): usa `supplier_client.check_contract()` en lugar de ChromaDB
- **Chat IA** (BUG-019 → SPEC_013): comandos para "modificar límite de SUP00X a $200k"
- **PDF Extractor** (futuro): al subir factura, identifica supplier_id por CUIT
- **Evaluación** (SPEC_010): agrega golden cases para CRUD de proveedores

## 8. BUGs Resueltos relacionados

- **BUG-016**: Implementación inicial del ABM
- **BUG-017**: Columnas desalineadas en tabla de proveedores
- **BUG-018**: 500 al editar (cliente httpx cerrado prematuramente)

## 9. Métricas

| Métrica | Valor esperado |
|---------|----------------|
| Latencia de alta | < 200ms |
| Latencia de validación de factura | < 50ms |
| Disponibilidad del servicio | > 99% |
| Tasa de error en alta | < 1% |
