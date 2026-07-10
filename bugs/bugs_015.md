# BUG-015: Nomenclatura uniforme FC-PV-NRO + soporte A/B/C + listado mejorado

## Severidad: **MEDIUM**
## Componente: `data/` + `watcher.py` + `app.js` + `inbox_router.py`
## Detectado por: Usuario quiere listado claro y soporte A/B/C
## Fecha: 2026-07-09

---

## Descripción

El usuario pide:

### 1. **Nomenclatura uniforme**: `FC-0001-00000007`
   - Formato: `FC-<punto_venta>-<numero_comprobante>`
   - Siempre con padding: PV 4 dígitos, Número 8 dígitos
   - Aplicar tanto al `invoice_id` como al nombre de archivo

### 2. **Soporte para tipos de factura A, B, C**
   - **Factura A**: entre IVA Responsable Inscripto (discrimina IVA)
   - **Factura B**: emisor Responsable Inscripto → consumidor final / exento (IVA incluido)
   - **Factura C**: monotributo / exento (sin IVA)
   - Cada tipo tiene estructura diferente:
     - A: Subtotal + IVA 21% + Total (IVA discriminado)
     - B: Total (IVA incluido)
     - C: Total (sin IVA)

### 3. **Items legibles**
   - Tabla con columnas: Cantidad, Descripción, P. Unitario, Importe
   - Subtítulo: "X items, total $Y"

### 4. **Modal con 2 subsecciones claras**

```
[SECCIÓN 1: 📄 FACTURA ORIGINAL]
  - Todo lo que vino del PDF/TXT
  - Datos del emisor completos
  - Datos del comprobante (PV, número, fecha, tipo)
  - Receptor completo
  - Items (tabla)
  - CAE / Código de barras
  - Datos del impresor

[SECCIÓN 2: 🔍 DECISIÓN DEL SISTEMA]
  - Decisión final (APPROVED/REJECTED/ESCALATED)
  - Status de pago
  - Confirmation ID
  - Razón de rechazo (si aplica)
  - Regla que se aplicó (BR-XX, VR-XX, etc.)
  - Steps del flujo de validación
  - Audit del A2A (si fue escalada)
  - Hallazgos del auditor
```

### 5. **Listado del Inbox/Historial debe mostrar**

| Columna | Descripción |
|---------|-------------|
| Proveedor | SUP00X + nombre |
| CUIT | Del emisor |
| Nº Factura | FC-PV-NRO |
| Moneda | ARS / USD |
| Monto | $XX,XXX.XX |
| Estado | APPROVED / REJECTED / ESCALATED / PENDING |
| Ojito | 👁️ Abre modal |

## Plan de Fix

### 1. Generar Facturas A, B, C de muestra
- Script que genera 3 facturas A, 3 facturas B, 3 facturas C
- Diferentes proveedores y montos
- Estructura correcta para cada tipo (A discrimina IVA, B y C no)

### 2. Actualizar parser
- Detectar tipo (A, B, C) según código 01/06/11
- Para tipo A: extraer subtotal + IVA por separado
- Para tipo B: total = importe directo (IVA incluido)
- Para tipo C: total = importe directo (sin IVA)

### 3. Refactorizar modal
- Sección 1: "📄 FACTURA ORIGINAL" con todos los campos parseados
- Sección 2: "🔍 DECISIÓN DEL SISTEMA" con decisión + razón + steps
- Tabla de items con formato claro

### 4. Mejorar listado
- Headers de columnas claras
- Datos completos en cada fila
- Botón ojo funcional

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

### 1. Nomenclatura uniforme `FC-<PV>-<NRO>`
Todos los archivos nuevos siguen el formato:
- `FC-0001-00000001.txt`, `FC-0001-00000002.txt`, etc.
- `invoice_id` se construye como `FC-0001-00000001` (parser)

### 2. Soporte para tipos A, B, C
`generar_facturas_abc.py` genera 24 archivos (8 de cada tipo):
- **A** (cód 01): discrimina IVA → `Subtotal + 21% + Total`
- **B** (cód 06): IVA incluido → solo `Total`
- **C** (cód 11): sin IVA → solo `Total`

Parser actualizado con:
- Detección por header `[FACTURA X]` y código AFIP
- Cálculo de subtotal e IVA para tipo A
- subtotal = total para tipo B y C (IVA 0)

### 3. Supplier_id por CUIT
Como el filename ya no incluye SUP00X, agregué `_resolve_supplier_by_cuit()` en
`watcher.py` que busca en `suppliers.db` por CUIT (con/sin guiones).

### 4. Modal con 2 secciones claras
`openInvoiceModal()` ahora tiene 2 headers visuales distintos:

**📄 FACTURA ORIGINAL** (gradiente azul)
- Identificación del Comprobante (tipo, código AFIP, PV, número, fecha)
- 🏢 Emisor (razón social, CUIT, condición IVA, domicilio, rubro, IIBB)
- 👤 Receptor (señor/es, CUIT, domicilio, localidad, condición IVA)
- 💳 Condiciones Comerciales (cond. venta, remito)
- 📦 Items (tabla con cant/desc/p.unit/importe + total destacado)
- 🛡️ Datos Fiscales (CAE, vencimiento, código barras)
- 🖨️ Impresor

**🔍 DECISIÓN DEL SISTEMA** (gradiente púrpura)
- Decisión final (✅/❌/⏫), Status, Confirmation ID, Fecha registro
- ⚠️ Motivo de Decisión (razón rechazo, regla aplicada, acción guardrail)
- 🔄 Flujo de Validación Ejecutado (steps con ✅/❌)
- 🔍 Auditoría Externa A2A (si fue escalada)
- 📁 Origen

### 5. Listado del Inbox muestra
- Tipo (A/B/C)
- Emisor (razón social)
- CUIT
- Nº Factura (FC-PV-NRO)
- Moneda (ARS)
- Monto
- Estado (decision)
- 👁️ (botón ojo)

## Verificación

```
=== PROCESAR Factura A (FC-0001-00000001.txt) ===
  Decision:      ESCALATED  (> $500k)
  Tipo:          FACTURA A
  Invoice ID:    FC-0001-00000001
  PV/Nro:        0001/00000001
  Supplier:      SUP001  (resuelto por CUIT)
  Subtotal:      $525,000.00
  IVA 21%:       $110,250.00
  Total:         $635,250.00
  Items:         3
  Confirmation:  PAY-1701A002

=== Factura C ===
  Subtotal:      $845,000  (= total, sin IVA)
  IVA 21%:       $0
  Total:         $845,000
```