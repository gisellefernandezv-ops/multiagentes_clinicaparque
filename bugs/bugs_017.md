# BUG-017: Columna "Categoria" muestra email + falta lapiz de editar

## Severidad: **MEDIUM**
## Componente: `app/frontend/app.js` `renderSuppliers()` + `app/frontend/index.html`
## Detectado por: Usuario ve email en columna Categoria + quiere lapiz de editar
## Fecha: 2026-07-09

---

## Descripción

El usuario reporta que en el listado de proveedores:

```
ID     Razón Social         CUIT             Condición    Categoría           Email                Contrato  Modo          Límite   Estado       Acciones
SUP001 TechCorp SA          30-71234567-0   Servicios IT  billing@techcorp... billing@techcorp... ✅        ≤ No superar  150.000  ✅ Activo   ✏️ 🔒
```

**Problema 1**: La columna "Categoría" muestra el email en vez de la categoría.
**Problema 2**: La columna "Email" está duplicada (también muestra email).
**Problema 3**: Falta asegurar lapiz visible para editar.

## Causa Raíz

En `renderSuppliers()` las columnas se renderizan así:

```js
<td>${(s.category || '').substring(0, 20)}</td>   // se muestra en columna "Condición" (MAL)
<td>${s.email || '-'}</td>                        // se muestra en columna "Categoría" (MAL)
<td>${s.email || '-'}</td>                        // se muestra en columna "Email" (DUPLICADO)
```

PERO los headers del HTML son:

```html
<th>ID</th>
<th>Razón Social</th>
<th>CUIT</th>
<th>Condición</th>     ← esperaba condicion_iva (no existe en modelo)
<th>Categoría</th>     ← esperaba category
<th>Email</th>           ← email
```

Resultado: las columnas están MAL ALINEADAS.

- Header "Condición" recibe `s.category` (muestra "Servicios IT")
- Header "Categoría" recibe `s.email` (muestra email)
- Header "Email" recibe `s.email` OTRA VEZ (duplicado)

## Fix Aplicado

### Opción elegida: Quitar columna "Condición" y corregir headers
- El modelo Supplier NO tiene `condicion_iva`
- Mejor alinear headers con los datos disponibles:
  - Eliminar columna "Condición" del header
  - Reorganizar para que cada header coincida con su campo
- Para futuro: agregar `condicion_iva` al modelo (mejora)

### Cambios

1. **index.html** - Corregir `<thead>`:
```html
<tr>
    <th>ID</th>
    <th>Razón Social</th>
    <th>CUIT</th>
    <th>Categoría</th>     <!-- ANTES: Condición -->
    <th>Email</th>           <!-- ANTES: Categoría (mostraba email) -->
    <th>Teléfono</th>       <!-- NUEVO -->
    <th>Contrato</th>
    <th>Modo</th>
    <th>Límite</th>
    <th>Estado</th>
    <th>Acciones</th>       <!-- YA EXISTE con lapiz (✏️) -->
</tr>
```

2. **app.js** - Reorganizar `renderSuppliers()`:
```js
<td><strong>${s.supplier_id}</strong></td>
<td>${s.name}</td>
<td class="mono">${s.cuit}</td>
<td>${s.category || '-'}</td>     <!-- AHORA muestra category -->
<td>${s.email || '-'}</td>        <!-- AHORA muestra email -->
<td>${s.phone || '-'}</td>        <!-- NUEVO -->
<td>${c ? '✅' : '❌'}</td>
...
```

3. **Pencil de editar** - ya existe, asegurar que sea visible:
```js
<button class="btn-icon" onclick='editSupplier(${JSON.stringify(s).replace(/'/g, "&apos;")})' title="Editar">✏️</button>
```

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

### 1. `app/frontend/index.html` - headers correctos
```html
<tr>
    <th>ID</th>
    <th>Razón Social</th>
    <th>CUIT</th>
    <th>Categoría</th>     <!-- ANTES era "Condición" -->
    <th>Email</th>           <!-- ANTES era "Categoría" -->
    <th>Teléfono</th>       <!-- NUEVO -->
    <th>Contrato</th>
    <th>Modo</th>
    <th>Límite</th>
    <th>Estado</th>
    <th>Acciones</th>
</tr>
```

### 2. `app/frontend/app.js` - `renderSuppliers()` corregido
```js
// ANTES (bug):
// <td>${(s.category || '').substring(0, 20)}</td>   <- en columna "Condición"
// <td>${s.email || '-'}</td>                        <- en columna "Categoría"
// <td>${s.email || '-'}</td>                        <- DUPLICADO

// DESPUÉS (fix):
<td>${s.category || '-'}</td>     // ahora en columna "Categoría" ✓
<td>${s.email || '-'}</td>        // ahora en columna "Email" ✓
<td>${s.phone || '-'}</td>        // NUEVO en columna "Teléfono" ✓
```

### 3. Bug extra: typo `s/supplier_id` → `s.supplier_id`
En el search filter había un typo que rompía la búsqueda por ID.

### 4. Lápiz de editar más visible
```html
<button class="btn-icon"
        onclick='editSupplier(...)'
        title="Editar proveedor"
        style="font-size:18px; padding:6px 10px;">✏️</button>
```

## Verificación

```
=== HTML HEADERS ===
ID | Razón Social | CUIT | Categoría | Email | Teléfono | Contrato | Modo | Límite | Estado | Acciones

=== JS renderSuppliers() - Verificaciones ===
  [OK] BUG: typo s/supplier_id (ya no existe)
  [OK] FIX: search por supplier_id
  [OK] FIX: columna categoria usa s.category
  [OK] FIX: columna telefono usa s.phone
  [OK] FIX: lapiz con title mas claro
  [OK] HTML: header Categoria
  [OK] HTML: header Telefono
  [OK] HTML: header Acciones (FIX lapiz)
  [OK] Icon ✏️ found
  [OK] Title 'Editar proveedor' found
```