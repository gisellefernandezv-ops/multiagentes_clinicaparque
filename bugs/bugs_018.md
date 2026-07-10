# BUG-018: 500 al editar proveedor + falta responsive design

## Severidad: **HIGH** (500 error) + **MEDIUM** (responsive)
## Componente: `app/backend/main.py` `proxy-update` + `app/frontend/style.css`
## Detectado por: Usuario edita SUP001 → 500 Internal Server Error
## Fecha: 2026-07-09

---

## Descripción

El usuario reporta 2 issues:

### 1. **500 al editar SUP001**
```
:8000/suppliers/proxy-update/SUP001:1  Failed to load resource: the server responded with a status of 500 (Internal Server Error)
```

### 2. **Falta responsive design**
La UI no se adapta a mobile/tablet.

## Causa Raíz (Issue 1)

En `app/backend/main.py` el endpoint `proxy-update`:

```python
@app.put("/suppliers/proxy-update/{supplier_id}")
async def suppliers_proxy_update(supplier_id: str, payload: dict):
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.put(...)  # ← async con client
        if r.status_code >= 400:
            raise HTTPException(r.status_code, r.text)
    # ← cliente YA CERRADO al salir del `async with`
    if "contract" in payload and payload["contract"]:
        rc = await client.post(...)  # ← ERROR: cliente cerrado
```

**Bug**: el segundo `await client.post(...)` se hace **fuera** del bloque `async with`,
donde el cliente ya fue cerrado. Genera un error `httpx.ClosedResourceError` que se
convierte en 500.

## Fix (Issue 1)

Mover ambas llamadas dentro del mismo `async with` y limpiar el payload:

```python
@app.put("/suppliers/proxy-update/{supplier_id}")
async def suppliers_proxy_update(supplier_id: str, payload: dict):
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Filtrar campos que no van en update del supplier
        supplier_data = {k: v for k, v in payload.items()
                         if k not in ("contract", "supplier_id")}
        r = await client.put(
            f"{settings.supplier_service_url}/suppliers/{supplier_id}",
            json=supplier_data,
        )
        if r.status_code >= 400:
            raise HTTPException(r.status_code, r.text)
        if "contract" in payload and payload["contract"]:
            rc = await client.post(
                f"{settings.supplier_service_url}/suppliers/{supplier_id}/contract",
                json=payload["contract"],
            )
            if rc.status_code >= 400:
                raise HTTPException(rc.status_code, rc.text)
    return {"ok": True}
```

## Fix (Issue 2 - Responsive)

Agregados media queries comprehensivos en `app/frontend/style.css`:

### Tablet (≤1024px)
- Sidebar colapsa a **iconos horizontales** arriba
- Stats grid: 2 columnas
- Form grid: 1 columna

### Mobile (≤768px)
- Sidebar oculto (solo iconos)
- Modal ocupa 95% del ancho
- Tablas con scroll horizontal
- Action bar wrap
- Form grid: 1 columna
- Agents grid: 1 columna

### Mobile pequeño (≤480px)
- Header simplificado (sin "Agentes" ni "User")
- Stats grid: 1 columna
- **Tabla proveedores**: oculta columnas Categoría y Teléfono
- Page title más pequeño

### Print
- Sidebar/header/buttons ocultos

## Status: ✅ RESUELTO