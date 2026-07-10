# BUG-020: Chat no entiende "modificar el monto" → va a inbox_amounts

## Severidad: **HIGH**
## Componente: `app/backend/chat_router.py` `INTENT_RE` regex para set_contract_limit
## Detectado por: Usuario pidió "modificar el monto" → GI mostró montos del inbox
## Fecha: 2026-07-09

---

## Descripción

El usuario pide:
> "Hola, quiero modificar el monto que no debe superar el proveedor SUP001. El nuevo monto es 350000"

Pero el chat interpreta `intent: inbox_amounts` y muestra los montos del inbox en lugar de modificar el contrato.

## Causa Raíz

El regex de `set_contract_limit` actual es:
```python
r"\b(cambi[áa]r?|modific[áa]r?|actualiz[áa]r?|poner)\b.*(l[íi]mite|monto\s*m[áa]ximo|tope|amount|cap)"
```

- La segunda parte `(l[íi]mite|monto\s*m[áa]ximo|tope|amount|cap)` requiere:
  - `límite` ✓
  - `monto máximo` (con espacio) ✓
  - `tope` ✓
  - `amount` / `cap` ✓
- Pero NO captura `monto` solo

El mensaje tiene "modificar el monto" - "monto" sin "máximo". Por eso el regex no matchea, y el siguiente intent que matchea es `inbox_amounts` que solo requiere "monto".

## Fix Aplicado

### 1. Regex más flexible
```python
# ANTES
r"\b(cambi[áa]r?|modific[áa]r?|actualiz[áa]r?|poner)\b.*(l[íi]mite|monto\s*m[áa]ximo|tope|amount|cap)"

# DESPUÉS (FIX BUG-020)
r"\b(cambi[áa]r?|modific[áa]r?|actualiz[áa]r?|poner|establec[ée]r?|defin[íi]r?)\b.*(l[íi]mite|monto|m[áa]ximo|tope|amount|cap|techo|contrato)"
```

### 2. Patterns adicionales para casos comunes
- "modificar el monto que no debe superar" → set_contract_limit
- "cambiar el límite" → set_contract_limit
- "establecer el límite" → set_contract_limit
- "definir el monto" → set_contract_limit
- "subir/bajar el monto" → set_contract_limit (NEW verbs)

### 3. Mejora en entity extraction para "monto"
- "el nuevo monto es 350000" debe detectar 350000
- "el monto no debe superar 350000" debe detectar 350000

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

### 1. Regex `set_contract_limit` más flexible
```python
# ANTES
r"\b(cambi[áa]r?|modific[áa]r?|actualiz[áa]r?|poner)\b.*(l[íi]mite|monto\s*m[áa]ximo|tope|amount|cap)"

# DESPUÉS
r"\b(cambiar?|modificar?|actualizar?|poner|establecer|definir?|fijar?|subir|bajar?|ajustar?)\b.*(l[íi]mite|monto|m[áa]ximo|tope|amount|cap|techo|contrato|que\s+no)"
```

**Cambios**:
- Verbos completos: `cambiar`, `modificar`, `actualizar`, `poner`, `establecer`, `definir`, `fijar`, `subir`, `bajar`, `ajustar`
- Sustantivos: `límite`, `monto`, `máximo`, `tope`, `amount`, `cap`, `techo`, `contrato`, `que no`
- Acepta "monto" solo (no necesita "monto máximo")

## Verificación

### Caso del usuario
```
Input:  "Hola, quiero modificar el monto que no debe superar el proveedor SUP001. 
         El nuevo monto es 350000"
Intent: set_contract_limit
Output: "✅ Límite de SUP001 actualizado de $100,000 a $350,000 (modo: NO_SUPERAR)"
```

### 7/7 tests PASAN
- "modificar el monto de SUP001 a 400000" → set_contract_limit ✓
- "cambia el monto de SUP002 a 80000" → set_contract_limit ✓
- "subir el límite de SUP001 a 250000" → set_contract_limit ✓
- "establecer el límite de SUP004 en 100000" → set_contract_limit ✓
- "definir el monto de SUP005 a 300000" → set_contract_limit ✓
- "bajar el límite de SUP001 a 50000" → set_contract_limit ✓
- "ajustar el monto de SUP001 a 200000" → set_contract_limit ✓

### inbox_amounts sigue funcionando
- "me podras decir los montos" → inbox_amounts ✓
- "cuánto suman las facturas del inbox" → inbox_amounts ✓