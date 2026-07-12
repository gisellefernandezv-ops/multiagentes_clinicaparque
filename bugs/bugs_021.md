# BUG-021 — Parser de facturas no extrae datos

## Resumen

| Campo | Valor |
|-------|-------|
| **ID** | BUG-021 |
| **Severidad** | HIGH |
| **Componente** | `app/backend/watcher.py` |
| **Fecha** | 2026-07-15 |
| **Estado** | ✅ RESUELTO |

## Descripción

Cuando se subía una factura con formato `FC-2026-SUP001-NUEVA-3.txt`, el inbox mostraba:
- `invoice_id`: null
- `invoice_date`: null
- `amount`: ""

Los datos de número de factura, fecha de emisión y monto no se extraían correctamente.

## Causa Raíz

1. **Parser no reconocía formato `Numero:`**: El regex esperaba `N° XXXX-XXXXXXXX` pero el formato nuevo usaba `Numero: FC-2026-SUP001-NUEVA-3`

2. **Parser no reconocía `Fecha:`**: El regex esperaba `FECHA:` (mayúsculas) pero había archivos con `Fecha:` (mayúscula inicial)

3. **Error en `_parse_amount_ar()`**: Para montos como `25,000.00`, la función hacía `replace(".", "").replace(",", ".")` resultando en `25000.` y luego `25.0`

## Solución

### 1. Parser de IDENTIFICACION (`watcher.py`)

```python
# Formato 2: Numero: FC-XXXX-SUP001-NUEVA-X (formato nuevo)
if "invoice_id" not in result:
    m = re.search(r"Numero:\s*([A-Z0-9\-]+)", text)
    if m:
        result["invoice_id"] = m.group(1).strip()

# Fecha: Fecha: DD/MM/YYYY (formato alternativo)
if "invoice_date" not in result:
    m = re.search(r"^Fecha:\s*(\d{1,2})/(\d{1,2})/(\d{4})", text, re.MULTILINE)
    if m:
        d, mo, y = m.groups()
        result["invoice_date"] = f"{y}-{int(mo):02d}-{int(d):02d}"
```

### 2. Parser de TOTAL alternativo

```python
# Formato alternativo: TOTAL: ARS $ XXX,XXX.XX
if "amount" not in result or result.get("amount") == 0:
    m = re.search(r"TOTAL:\s*ARS\s*\$\s*([\d.,]+)", text)
    if m:
        total = _parse_amount_ar(m.group(1))
        if total is not None:
            result["amount"] = total
            result["total"] = total
```

### 3. Función `_parse_amount_ar()` corregida

```python
def _parse_amount_ar(s: str) -> Optional[float]:
    """Parsea monto en formato argentino o inglés."""
    if not s:
        return None
    s = s.strip()
    has_comma = ',' in s
    has_dot = '.' in s
    if has_comma and has_dot:
        comma_pos = s.rfind(',')
        dot_pos = s.rfind('.')
        if comma_pos > dot_pos:
            # Formato argentino: 1.234.567,89
            s = s.replace('.', '').replace(',', '.')
        else:
            # Formato inglés: 1,234.56
            s = s.replace(',', '')
    elif has_comma:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) == 2:
            # Es decimal: 25,000.00 → 25000.0
            s = s.replace(',', '.')
        else:
            # Son miles: 10,000 → 10000
            s = s.replace(',', '')
    try:
        return float(s)
    except ValueError:
        return None
```

## Resultado

| Campo | Antes | Después |
|-------|-------|---------|
| `invoice_id` | null | "FC-2026-SUP001-NUEVA-3" |
| `invoice_date` | null | "2026-06-28" |
| `amount` | "" | 25000.0 |

## Formatos de Factura Soportados

### Formato 1: Estándar AFIP
```
[FACTURA A]
Numero: 0001-00000025
Fecha: 28/06/2026
...
TOTAL: $ 150,000.00
```

### Formato 2: Formato Nuevo
```
FACTURA A
Numero: FC-2026-SUP001-NUEVA-3
Fecha: 28/06/2026
...
TOTAL: ARS $ 25,000.00
```

### Formato 3: Key:Value
```
invoice_id: FC-001-00000001
supplier_id: SUP001
amount: 50000
invoice_date: 2025-06-01
```

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `app/backend/watcher.py` | Parser mejorado + `_parse_amount_ar()` corregido |
| `app/backend/inbox_router.py` | Modelo `InboxItem` con campos adicionales |

## Verificación

```python
# Test
from app.backend.watcher import parse_invoice_file
result = parse_invoice_file(Path("app/data/inbox/FC-2026-SUP001-NUEVA-3.txt"))
print(result["invoice_id"])  # "FC-2026-SUP001-NUEVA-3"
print(result["invoice_date"])  # "2026-06-28"
print(result["amount"])  # 25000.0
```
