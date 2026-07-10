# BUG-014: Sistema usa formato simplificado, no Factura B real

## Severidad: **MEDIUM**
## Componente: `data/new invoices/*.txt`, `app/backend/watcher.py`, `app/frontend/`
## Detectado por: Usuario envía imagen real de Factura B argentina como modelo
## Imagen: `../ej_fact/factura_b_ejemplo.jpg`
## Fecha: 2026-07-09

---

## Descripción

El usuario envió una imagen real de **Factura B argentina** (`factura_b_ejemplo.jpg`)
como modelo para el sistema. Esta es la factura estándar pre-impresa con código fiscal AFIP.

### Formato REAL de Factura B (campos que debe soportar el sistema)

```
[EMISOR]
- Razón Social (Apellido y Nombre)
- Rubro / Matrícula (opcional)
- Dirección
- Tel. / Email / Web (opcional)
- Condición IVA: "IVA Responsable Inscripto" / "Monotributo" / etc.
- CUIT
- Ingresos Brutos
- Inicio de Actividades

[IDENTIFICACIÓN DEL COMPROBANTE]
- Tipo: FACTURA A / B / C / NC / ND
- Código tipo: 01, 06, 11, etc.
- Punto de Venta: 0001
- Número: 0001-00000001

[FECHA]
- Fecha de emisión

[RECEPTOR]
- Señor/es (Razón Social)
- Dirección
- Localidad
- CUIT
- Condición frente al IVA: Cons. Final / Monotributo / Exento / No Resp.

[CONDICIONES DE VENTA]
- Contado / Cta. Cte.
- Remito Nº

[ITEMS]
- Cantidad
- Descripción
- Precio Unitario
- Importe (= Cantidad * P. Unitario)

[TOTALES]
- TOTAL $
- Subtotal
- IVA discriminado (para Factura A)

[FISCAL]
- CAI (Código de Autorización de Impresión) o CAE (Electrónica)
- Vencimiento del CAI/CAE
- Código de barras (28 dígitos)

[METADATA]
- Impreso por: Razón Social + CUIT
- Nº de Expediente
- Fecha de Impresión
- Rango de impresión (0001-0000001 al 0001-0000100)
- ORIGINAL / DUPLICADO / TRIPLICADO
```

### Lo que el sistema tiene HOY

- **Formato simplificado** en `data/new invoices/*.txt`:
  ```
  Numero: FC-2026-SUP001-NUEVA-1
  Fecha: 28/06/2026
  Vencimiento: 28/07/2026
  CUIT: 30-71234567-0
  TOTAL: ARS $     25,000.00
  ```
- Solo extrae: invoice_id, invoice_date, due_date, cuit, amount, supplier_id, currency
- NO soporta: punto de venta, items detallados, condición IVA emisor/receptor,
  tipo de comprobante (A/B/C), CAE/CAI, condición de venta, remito, etc.

### Impacto

- El sistema NO puede leer facturas reales del modelo argentino
- Cualquier factura que un proveedor suba REAL no se podrá parsear
- El modal muestra solo 8 campos, no los 25+ que tiene una Factura B real
- El "BackOffice" no es funcional para operación real

## Plan de Fix

### 1. Generar archivos de muestra con formato Factura B real
   - Script que genera 5 archivos .txt con el formato completo de Factura B
   - Uno por cada proveedor (SUP001, SUP002, SUP004, SUP005)
   - Cada uno con 3-5 items detallados, CAE, código de barras, etc.

### 2. Extender parser TXT para Factura B
   - Detectar formato con headers como "FACTURA B", "Punto de Venta", "C.U.I.T."
   - Extraer: tipo_comprobante, punto_venta, numero, fecha, items[], total,
     CAE/CAI, codigo_barras, condicion_venta, etc.
   - Mantener compatibilidad con formato simplificado anterior

### 3. Generar también archivos JSON estructurados
   - `data/inbox/*.json` con todos los campos en JSON
   - Parser JSON los lee y devuelve el dict completo

### 4. Extender modal del BackOffice
   - Mostrar TODOS los campos parseados
   - Sección "Items" con tabla
   - Sección "Fiscal" con CAE/CAI y código de barras
   - Sección "Emisor/Receptor" con datos completos

### 5. Documentar el modelo de Factura B
   - En `data/FACTURA_B_MODEL.md` con especificación completa
   - Como referencia para futuros desarrollos (PDF extractor, etc.)

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

### 1. Generador de Facturas B reales
`generar_facturas_b.py` - Crea 12 archivos TXT (3 por cada proveedor activo: SUP001, SUP002, SUP004, SUP005)
basados en el modelo `factura_b_ejemplo.jpg`. Incluyen:
- Razón social, CUIT, rubro, dirección, condición IVA, ingresos brutos, inicio act.
- Punto de venta, número de comprobante, código tipo
- Receptor con CUIT, domicilio, localidad, condición frente al IVA
- Condiciones de venta (Contado/Cta. Cte.)
- Items detallados (cantidad, descripción, P. unitario, importe)
- CAE, vencimiento, código de barras
- Datos del impresor

### 2. Parser completo de Factura B
`app/backend/watcher.py` `_parse_factura_txt()` ahora extrae:
- **Identificación**: tipo_comprobante, codigo_tipo, punto_venta, numero_comprobante, invoice_id, invoice_date
- **Emisor**: razon_social, rubro, direccion, cuit, ingresos_brutos, inicio_actividades, condicion_iva
- **Receptor**: razon_social, direccion, localidad, cuit, condicion_iva
- **Condiciones**: condicion_venta (Contado/Cta. Cte.), remito_numero
- **Items[]**: cantidad, descripcion, precio_unitario, importe
- **Totales**: amount, total, currency
- **Fiscal**: cae, cae_vencimiento, codigo_barras
- **Impresor**: razon_social, cuit, expediente, fecha, rango_desde, rango_hasta
- **supplier_id** del filename

Helper `_parse_amount_ar()` para formato argentino "1.234.567,89".

### 3. Endpoint `/inbox` enriquecido
`InboxItem` Pydantic model extendido con campos adicionales (punto_venta, numero_comprobante, emisor_razon_social, emisor_cuit, tipo_comprobante, cae, codigo_barras, items_count).

### 4. InvoiceResult extendido
El response de procesamiento ahora incluye `tipo_comprobante`, `punto_venta`, `numero_comprobante`, `emisor_razon_social`, `emisor_cuit`, `cae`, `codigo_barras`, `items[]`.

### 5. Modal con secciones (Factura B completa)
`app/frontend/app.js` `openInvoiceModal()` muestra:
- 📋 Identificación (tipo, PV, número, fecha, total)
- 🏢 Emisor (razón social, CUIT, condición IVA, domicilio, rubro, IIBB)
- 👤 Receptor (señor/es, CUIT, domicilio, localidad, condición IVA)
- 💳 Condiciones (cond. venta, remito, proveedor)
- 📦 Items (tabla con cantidad, descripción, P. unitario, importe, total)
- 🛡️ Datos Fiscales (CAE, vencimiento, código de barras)
- 🔍 Trazabilidad (decisión, status, confirmation_id, fecha registro)
- 🖨️ Impresor (razón social, CUIT, expediente, fecha, rango)
- 🔍 Auditoría Externa (findings del A2A si aplica)

### 6. CSS para items-table
`app/frontend/style.css` agregó `.modal-wide`, `.section-block`, `.items-table`, `.audit-findings`.

### 7. Cache-bust
`?v=2026070906` en JS y CSS.

## Verificación

```
=== TEST BUG-014: Factura B formato real ===
Total REAL: 12

=== FC-2026-SUP001-REAL-01.txt ===
  Tipo:       FACTURA B
  PV:         0001
  Numero:     00000001
  Invoice ID: FC-0001-00000001
  Emisor:     TechCorp Argentina SA
  CUIT:       30-71234567-0
  CAE:        91088215148115
  Items:      3
  Total:      $525,000

=== Procesando FC-2026-SUP004-REAL-01.txt ===
Decision:        REJECTED ($145k > $80k limit SUP004)
Amount:          $145,000
Supplier:        SUP004
Invoice ID:      FC-0001-00000007
Confirmation:    PAY-CF4FFC5D
Items parsed:    3
CAE:             95332317303466
Punto venta:     0001
Numero comp.:    00000007
```