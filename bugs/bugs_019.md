# BUG-019: Chat no entiende "montos" + debe llamarse "Asistente IA" +自我介绍

## Severidad: **MEDIUM**
## Componente: `app/backend/chat_router.py` + `app/frontend/index.html` + `app/frontend/app.js`
## Detectado por: Chat falla con consultas naturales como "me podras decir los montos"
## Fecha: 2026-07-09

---

## Descripción

El usuario reporta 3 issues con el chat interno:

### 1. Chat no entiende "me podras decir los montos"
```
Operador: me podras decir los montos
IA: No entendí la instrucción. Probá con: • 'procesá todo el inbox'...
```

El intent parser actual solo reconoce 5 patrones:
- `process_all` (procesar todo)
- `process_one` (procesar factura X)
- `process_path` (path de archivo)
- `list_inbox` (listar facturas en inbox)
- `history` (historial)
- `unknown` (default)

NO entiende consultas como:
- "me podras decir los montos"
- "cuánto suman las facturas"
- "qué importes hay"
- "total facturado"
- "resumen del inbox"

### 2. El chat debe llamarse "Asistente IA"
Actualmente el header dice "Chat interno" pero debe decir **"Asistente IA"**.

### 3. Al entrar, el bot debe presentarse
"soy tu Asistente Inteligente GI" - mensaje de bienvenida.

## Fix Aplicado

### 1. Nuevos intents en `chat_router.py`
```python
INTENT_RE = [
    # Existentes
    (re.compile(r"(proces|aprueb|revis).*(todo|Todas|all|inbox)", re.I), "process_all"),
    (re.compile(r"(proces|aprueb|revis).*(?:la\s+)?(?:factura\s+)?([A-Z]{2,}-?\d+)", re.I), "process_one"),
    (re.compile(r"([\/\\]inbox[\/\\][^\s]+\.(?:json|txt))", re.I), "process_path"),
    (re.compile(r"(list|qu hay|pendientes|inbox)", re.I), "list_inbox"),
    (re.compile(r"(historial|pagos|procesad)", re.I), "history"),
    # NUEVOS (BUG-019)
    (re.compile(r"(monto|importe|cu[aá]nto|precio).*suman|total.*factur|total.*general", re.I), "totals"),
    (re.compile(r"(monto|importe|cu[aá]nto).*inbox|facturas.*inbox|pendientes.*monto", re.I), "inbox_amounts"),
    (re.compile(r"(monto|importe|cu[aá]nto).*historial|procesadas.*monto|pagadas.*monto", re.I), "history_amounts"),
    (re.compile(r"(resumen|total|estad|st|sumario).*general|sumario|cu[aá]nto.*hay", re.I), "summary"),
]
```

### 2. Handlers nuevos
```python
def handle_inbox_amounts() -> dict:
    items = handle_list_inbox()["data"]["items"]
    if not items:
        return {"intent": "inbox_amounts", "message": "Inbox vacío.", "data": {"total": 0, "count": 0}}
    total = sum(float(i.get("amount") or 0) for i in items)
    return {
        "intent": "inbox_amounts",
        "message": f"{len(items)} factura(s) en inbox, total: ${total:,.2f}",
        "data": {"items": items, "total": total, "count": len(items)}
    }

def handle_totals() -> dict:
    """Suma total de facturas procesadas."""
    # ... suma de APPROVED + REJECTED + ESCALATED
```

### 3. Header del chat: "Asistente IA"
`index.html`: Cambiar `<h2>💬 Chat interno</h2>` → `<h2>🤖 Asistente IA</h2>`

### 4. Mensaje de bienvenida
En `app.js` cuando se carga la página, agregar mensaje del sistema:
```js
addInternalChatMessage('system', '👋 ¡Hola! Soy tu Asistente Inteligente GI. ¿En qué puedo ayudarte?');
```

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

### 1. Nuevos intents en `chat_router.py` (ordenados por especificidad)
```python
INTENT_RE = [
    # 1. process_all
    # 2. process_one
    # 3. process_path
    # 4. history_amounts  (antes que history)
    # 5. inbox_amounts con "inbox" (antes que totals)
    # 6. totals
    # 7. history (genérico)
    # 8. summary
    # 9. help
    # 10. list_inbox
    # 11. inbox_amounts catch-all
]
```

### 2. Nuevos handlers
- `handle_inbox_amounts()` → montos de facturas en inbox + lista
- `handle_history_amounts()` → totales del historial
- `handle_totals()` → breakdown APPROVED/REJECTED/ESCALATED
- `handle_summary()` → overview del sistema
- `handle_help()` → ayuda con ejemplos

### 3. Header del chat
- `<span class="sidebar-text">Chat interno</span>` → **`<span class="sidebar-text">Asistente IA</span>`**
- `<h2 class="page-title">💬 Chat interno — ...` → **`<h2 class="page-title">🤖 Asistente IA — GI</h2>`**

### 4. Mensaje de bienvenida
Al entrar a la pestaña, el bot se presenta:
```
👋 ¡Hola! Soy tu Asistente Inteligente GI. Estoy acá para ayudarte con el sistema InvoiceFlow.

💡 Probalo con:
• "me podras decir los montos" → te muestro los montos del inbox
• "qué facturas hay en el inbox?" → lista las pendientes
• "mostrame el historial" → pagos registrados
• "cuánto suman las facturas" → totales por estado
• "resumen" → overview del sistema
• "procesá todo el inbox" → procesa las pendientes
```

## Verificación

```
=== Test: 'me podras decir los montos' ===
Intent: inbox_amounts
💰 Montos del inbox (24 factura(s), total **$11,399,720.00**):
• FC-0001-00000001 (SUP001): $635,250.00
• FC-0001-00000002 (SUP001): $526,350.00
• FC-0001-00000003 (SUP001): $80,000.00
• FC-0001-00000004 (SUP001): $155,000.00
• FC-0001-00000005 (SUP001): $225,000.00
... y 19 más.
```

12/12 tests PASAN:
- "me podras decir los montos" → inbox_amounts
- "cuanto suman las facturas del inbox" → inbox_amounts
- "importes del inbox" → inbox_amounts
- "montos del historial" → history_amounts
- "cuanto se facturo en el historial" → history_amounts
- "total facturado" → totals
- "resumen" → summary
- "ayuda" → help
- "procesa todo el inbox" → process_all
- "que facturas hay en el inbox" → list_inbox
- "mostrame el historial" → history
- "procesa la factura FC-0001-00000001" → process_one