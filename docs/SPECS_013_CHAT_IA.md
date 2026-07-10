# SPECS 013 — Asistente IA Conversacional con Memoria y Acciones

> **Proyecto**: InvoiceFlow
> **Tipo**: Especificación de Funcionalidad
> **Versión**: 2.0.0
> **Fecha**: 2026-07-15
> **Estado**: ✅ Implementado

---

## 1. Propósito

Esta spec describe el **Asistente IA "GI"** integrado en el BackOffice como un chat conversacional que:

1. Entiende consultas en lenguaje natural
2. **Mantiene memoria de la conversación** (contexto)
3. **Ejecuta acciones** sobre el sistema (modificar límites, activar proveedores, etc.)
4. Persiste las sesiones de chat en SQLite

## 2. Nombre y Personalidad

- **Nombre**: GI (Giselle Intelligence / Gestión Inteligente)
- **Tagline**: "Tu Asistente Inteligente para InvoiceFlow"
- **Tono**: Profesional, conciso, en español argentino
- **Mensaje de bienvenida**: "👋 ¡Hola! Soy tu **Asistente Inteligente GI**..."

## 3. Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│                     FRONTEND (Browser)                        │
│  BackOffice → 🤖 Asistente IA → input + chat-history         │
└────────────────────┬─────────────────────────────────────────┘
                     │ POST /chat {message, session_id?}
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                 BACKEND (chat_router.py)                       │
│  1. parse_intent(message) → intent + entities                │
│  2. load_context(session_id) → previous_messages            │
│  3. resolve_with_context(intent, entities, context)         │
│  4. execute_action(intent, entities) if action               │
│  5. format_response(intent, result)                          │
│  6. save_message(session_id, role, content)                  │
└──────┬───────────────────────────────────┬──────────────────┘
       │                                   │
       ▼                                   ▼
┌──────────────┐                  ┌──────────────────┐
│  In-memory   │                  │   chat_sessions  │
│  context     │                  │   .db (SQLite)   │
│  (últimos 5) │                  │  - sessions      │
│              │                  │  - messages      │
└──────────────┘                  └──────────────────┘
```

## 4. Tipos de Intent (15+ categorías)

### 4.1 Consultas (Read-only)

| Intent | Palabras clave | Handler |
|--------|----------------|---------|
| `list_inbox` | "qué hay", "pendientes", "archivos en" | Lista facturas pendientes |
| `history` | "historial", "pagos registrados" | Lista pagos |
| `inbox_amounts` | "monto", "importe", "precio", "cuánto", "suman" (sin historial) | Montos pendientes + total |
| `history_amounts` | "monto" + "historial/procesad" | Totales del historial |
| `totals` | "total facturado", "cuánto suman" (sin contexto) | Breakdown por decisión |
| `summary` | "resumen", "panorama", "overview" | Overview del sistema |
| `help` | "ayuda", "help" | Lista de comandos |

### 4.2 Acciones (Write/Modify)

| Intent | Palabras clave | Acción |
|--------|----------------|--------|
| `process_all` | "procesá todo" | Procesa todas las facturas del inbox |
| `process_one` | "procesá la factura X" | Procesa una factura específica |
| `set_contract_limit` | "cambiar límite", "modificar monto", "nuevo límite" | Modifica `contracts.contract_limit` |
| `set_contract_mode` | "cambiar modo a exacto" | Modifica `contracts.mode` |
| `activate_supplier` | "activar SUP00X" | `UPDATE suppliers SET status='ACTIVE'` |
| `deactivate_supplier` | "desactivar SUP00X" | `UPDATE suppliers SET status='INACTIVE'` |
| `update_supplier_field` | "cambiar email de SUP00X a X" | UPDATE específico |

## 5. Memoria Conversacional

### 5.1 Storage

- **Tabla `chat_sessions`**: id, title, created_at, last_active_at
- **Tabla `chat_messages`**: id, session_id, role (user/assistant/system), content, intent, created_at

### 5.2 Uso de Memoria

```python
# Al recibir un mensaje:
context = load_last_n_messages(session_id, n=5)
# context = [
#   {"role": "user", "content": "cuánto suman las facturas del inbox?"},
#   {"role": "assistant", "content": "$11,399,720 en 24 facturas..."},
#   {"role": "user", "content": "y del historial?"},  # ← mensaje actual
# ]

# Resolver referencias
if message_lower in ("y del historial?", "y los procesados?"):
    if context[-2]["intent"] == "inbox_amounts":
        intent = "history_amounts"
```

### 5.3 Entity Memory

El chat recuerda entidades mencionadas:

```python
# Si usuario dice "cambia el límite de SUP001 a 200k"
# y luego dice "ahora a 250k"
# → debe recordar que SUP001 es la entidad objetivo

last_supplier = get_last_supplier_in_context(session_id)
if "supplier_id" in entities:
    entities["supplier_id"] = entities["supplier_id"] or last_supplier
```

## 6. Ejecución de Acciones

### 6.1 Patrón General

```python
def handle_set_contract_limit(entities):
    sid = entities["supplier_id"]
    new_limit = entities["amount"]
    mode = entities.get("mode", "NO_SUPERAR")
    
    # Validar
    if not sid or not new_limit:
        return {"ok": False, "error": "Falta supplier_id o amount"}
    
    # Ejecutar via supplier-service
    r = httpx.post(f"http://localhost:8001/suppliers/{sid}/contract", 
                   json={"contract_limit": new_limit, "mode": mode})
    
    if r.status_code == 200:
        return {"ok": True, "message": f"✅ Límite de {sid} actualizado a ${new_limit:,.0f}"}
    else:
        return {"ok": False, "error": r.text}
```

### 6.2 Confirmaciones

Para acciones destructivas, pedir confirmación:

```
Usuario: "eliminá SUP003"
GI:      "¿Confirmás eliminar (dar de baja) al proveedor SUP003? 
         Esta acción no se puede deshacer. 
         Respondé 'sí' o 'no'."
Usuario: "sí"
GI:      "✅ SUP003 marcado como INACTIVE."
```

## 7. Patrones Regex para Entities

```python
ENTITY_PATTERNS = {
    "supplier_id": r"\bSUP\d{3}\b",
    "invoice_id": r"\b(?:FC-\d{4}-\d{8}|[A-Z]{2,}-?\d{2,})\b",
    "amount": r"\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*[kKmM]?",
    "mode": r"\b(exacto|no\s+superar|strict)\b",
    "field": r"\b(email|teléfono|nombre|categoría|cuit)\b",
    "value": r"a\s+['\"]?([^'\"]+)['\"]?",
}
```

## 8. Frontend

### 8.1 Header

```html
<h2>🤖 Asistente IA — GI</h2>
<p>Tu Asistente Inteligente para InvoiceFlow.</p>
```

### 8.2 Mensaje de Bienvenida (al entrar)

```
👋 ¡Hola! Soy tu Asistente Inteligente GI. Estoy acá para ayudarte.

💡 Probalo con:
• "me podras decir los montos" → montos del inbox
• "qué facturas hay en el inbox?" → lista pendientes
• "mostrame el historial" → pagos registrados
• "cuánto suman las facturas" → totales por estado
• "resumen" → overview
• "cambia el límite de SUP001 a 200000" → modifica contrato
• "desactivá SUP003" → cambia estado
• "procesá todo el inbox" → procesa pendientes

¿En qué te puedo ayudar?
```

### 8.3 Sesiones (futuro)

- Lista de sesiones en el sidebar del chat
- Crear nueva sesión
- Cambiar entre sesiones

## 9. Storage

### 9.1 chat_sessions.db

```python
CHAT_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT NOT NULL,
    last_active_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    intent TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""
```

## 10. API REST

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/chat` | Enviar mensaje (acepta `session_id` opcional) |
| GET | `/chat/sessions` | Listar sesiones |
| POST | `/chat/sessions` | Crear nueva sesión |
| GET | `/chat/sessions/{id}` | Obtener mensajes de la sesión |
| DELETE | `/chat/sessions/{id}` | Eliminar sesión |

### 10.1 Request/Response

```json
// POST /chat
{
  "message": "cambia el límite de SUP001 a 200000",
  "session_id": "uuid-optional"
}

// Response
{
  "intent": "set_contract_limit",
  "message": "✅ Límite de SUP001 actualizado a $200,000.00",
  "data": {
    "supplier_id": "SUP001",
    "old_limit": 150000,
    "new_limit": 200000,
    "mode": "NO_SUPERAR"
  },
  "session_id": "uuid"
}
```

## 11. BUGs Resueltos relacionados

- **BUG-019**: Chat no entendía "montos" + debe llamarse "Asistente IA"

## 12. Métricas

| Métrica | Objetivo |
|---------|----------|
| Latencia de respuesta | < 500ms (queries), < 2s (actions) |
| Tasa de intents reconocidos | > 90% |
| Satisfacción de acciones | > 95% exitosas |
| Memoria de sesión | últimos 5 mensajes |
