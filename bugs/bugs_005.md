# BUG-005: Chat JS lee `data.response` pero backend devuelve `data.message`

## Severidad: **HIGH**
## Componente: `app/frontend/app.js` función `sendInternalChat()`
## Detectado por: Inspección del JS contra ChatResponse del backend
## Fecha: 2026-07-09

---

## Descripción

```javascript
// línea 336-344
const resp = await fetch(`${API}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
});

const data = await resp.json();
addInternalChatMessage('system', data.response || 'Mensaje procesado');  // ←
```

**Backend retorna** (`chat_router.py`):

```python
class ChatResponse(BaseModel):
    intent: str
    message: str          # ← campo correcto
    data: Optional[dict] = None
```

```json
{
  "intent": "history",
  "message": "8 pago(s) registrado(s).",
  "data": {"items": [...]}
}
```

## Impacto

- `data.response` siempre `undefined`
- El chat siempre muestra "Mensaje procesado" (texto fallback)
- **Pierde** toda la información útil que el backend sí calcula correctamente

## Fix

```javascript
addInternalChatMessage('system', data.message || 'Mensaje procesado');
```

Y opcionalmente, mostrar info del intent detectado:

```javascript
const prefix = data.intent && data.intent !== 'unknown' ? `[${data.intent}] ` : '';
addInternalChatMessage('system', prefix + (data.message || 'Sin respuesta'));
```

## Status: ✅ RESUELTO (2026-07-09)

## Fix Aplicado

```javascript
// app/frontend/app.js sendInternalChat()
- addInternalChatMessage('system', data.response || 'Mensaje procesado');
+ const prefix = data.intent && data.intent !== 'unknown' ? `[${data.intent}] ` : '';
+ addInternalChatMessage('system', prefix + (data.message || 'Sin respuesta'));
```

Ahora el chat muestra el intent detectado entre corchetes + el mensaje real del backend.

## Verificación

Mensajes de prueba enviados y respuestas obtenidas:
- "mostrame el historial" → `[history] 14 pago(s) registrado(s).`
- "qué facturas hay en el inbox?" → `[list_inbox] 15 factura(s) en el inbox.`
- "asdf qwerty" → `[unknown] No entendí la instrucción. Probá con: ...`