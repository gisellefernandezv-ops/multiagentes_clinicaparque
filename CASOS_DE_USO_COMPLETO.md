# InvoiceFlow — Casos de Uso Completos

> **Versión**: 1.0 | **Última actualización**: 2026-07-18
> **Sistema**: InvoiceFlow - Aprobación Automatizada de Facturas

---

## Tabla de Contenidos

1. [Actores del Sistema](#1-actores-del-sistema)
2. [Casos de Uso — Portal del Proveedor](#2-casos-de-uso--portal-del-proveedor)
3. [Casos de Uso — Back Office](#3-casos-de-uso--back-office)
4. [Casos de Uso — Sistema Automático](#4-casos-de-uso--sistema-automático)
5. [Casos de Uso — Agentes y Chat](#5-casos-de-uso--agentes-y-chat)
6. [Matriz de Respuestas](#6-matriz-de-respuestas)
7. [Códigos de Error y Estados](#7-códigos-de-error-y-estados)

---

## 1. Actores del Sistema

| Actor | Código | Descripción | Permisos |
|-------|--------|-------------|----------|
| **Proveedor** | ACT-001 | Empresa que emite facturas | Subir facturas, consultar estados propios |
| **Administrador** | ACT-002 | Equipo de cuentas a pagar | Gestionar inbox, aprobar escaladas, consultar todo |
| **Sistema** | ACT-003 | Procesos automáticos | Validar, aprobar, rechazar, escalar |
| **Auditor Externo** | ACT-004 | Agente A2A para facturas >$500k | Evaluar y recomendar aprobación/rechazo |

---

## 2. Casos de Uso — Portal del Proveedor

---

### CU-P01: Iniciar Sesión en Portal

| Campo | Valor |
|-------|-------|
| **Código** | CU-P01 |
| **Nombre** | Iniciar Sesión en Portal |
| **Actor** | Proveedor |
| **Precondiciones** | Proveedor registrado en el sistema |
| **Postcondiciones** | Acceso al dashboard personalizado |

#### Flujo Principal
1. Proveedor abre `http://localhost:8000/supplier/`
2. Sistema muestra pantalla de login
3. Proveedor ingresa identificador (CUIT, nombre o ID)
4. Sistema valida contra `supplier-service`
5. Sistema muestra dashboard del proveedor

#### Respuesta Esperada

| Escenario | Input | Respuesta |
|-----------|-------|-----------|
| Login exitoso | `SUP001` | ✅ Dashboard con datos del proveedor |
| Identificador no existe | `SUP999` | ❌ "Proveedor no encontrado" |
| Proveedor inactivo | `SUP999` (inactivo) | ❌ "Proveedor inactivo, contacte a soporte" |
| Campo vacío | (vacío) | ❌ "Ingrese un identificador" |

#### Mensajes de Respuesta
```
ÉXITO: Redirigir a dashboard con datos del proveedor
ERROR: "Proveedor no encontrado"
ERROR: "Proveedor inactivo, contacte a soporte"
```

---

### CU-P02: Subir Factura (Flujo A)

| Campo | Valor |
|-------|-------|
| **Código** | CU-P02 |
| **Nombre** | Subir Factura |
| **Actor** | Proveedor |
| **Precondiciones** | Proveedor autenticado |
| **Postcondiciones** | Factura procesada, decisión registrada |

#### Flujo Principal
1. Proveedor navega a "Subir factura"
2. Arrastra archivo PDF o selecciona
3. Sistema valida formato y tamaño
4. Sistema extrae datos de factura
5. Sistema ejecuta pipeline de guardrails
6. Sistema muestra resultado

#### Respuesta Esperada por Tipo de Factura

| Escenario | Input | Validación que pasa/falla | Respuesta |
|-----------|-------|---------------------------|-----------|
| Factura válida | PDF correcto | Todas pasan | ✅ "Factura aprobada automáticamente" |
| Formato inválido | Archivo .jpg | VR-01 falla | ❌ "Formato de archivo no válido. Solo PDF." |
| Archivo muy grande | PDF 15MB | VR-02 falla | ❌ "Archivo demasiado grande. Máximo 10MB." |
| Campos faltantes | PDF incompleto | VR-03 falla | ❌ "Faltan campos obligatorios en la factura." |
| CUIT no existe | CUIT inexistente | VR-04 falla | ❌ "CUIT de proveedor no válido." |
| Fecha futura | Fecha > hoy | VR-05 falla | ❌ "La fecha de la factura no puede ser futura." |
| Monto cero | $0.00 | VR-06 falla | ❌ "El monto debe ser mayor a cero." |
| Factura duplicada | Mismo número | VR-07 falla | ❌ "Esta factura ya fue enviada." |
| Proveedor no existe | Supplier ID inválido | BR-01 falla | ❌ "Proveedor no registrado en el sistema." |
| Proveedor inactivo | Supplier inactivo | BR-02 falla | ❌ "Proveedor inactivo. Contacte a soporte." |
| Factura vencida | Fecha < 30 días | BR-03 falla | ❌ "Factura vencida. No se aceptan facturas de más de 30 días." |
| Razón social no coincide | Razón social diferente | BR-04 falla | ❌ "La razón social no coincide con el proveedor registrado." |
| Excede límite contractual | Monto > límite | BR-05 falla | ❌ "El monto excede el límite contractual de $X." |
| Contrato no vigente | Contrato expirado | BR-06 pasa/evalúa | ⚠️ "Factura escaladas para revisión manual" |
| Monto alto | > $500,000 | BR-07 | ⚠️ "Factura escaladas para auditoría externa" |
| Riesgo alto | Score > umbral | BR-08 | ⚠️ "Factura escaladas - riesgo elevado detectado" |
| Fraccionamiento | Múltiples facturas | BR-09 | ⚠️ "Posible fraccionamiento detectado" |

#### Mensajes de Guardrails

**Validaciones Estructurales (VR)**
```
VR-01: "Formato de archivo no válido. Solo se acepta PDF."
VR-02: "Archivo demasiado grande. El límite es 10MB."
VR-03: "Faltan campos obligatorios: [lista de campos]."
VR-04: "El CUIT de la factura no es válido."
VR-05: "La fecha de la factura es inválida o está en el futuro."
VR-06: "El monto debe ser mayor a cero."
VR-07: "Esta factura ya existe en el sistema."
```

**Validaciones de Negocio (BR)**
```
BR-01: "El proveedor no está registrado en el sistema."
BR-02: "El proveedor está inactivo."
BR-03: "La factura está vencida (más de 30 días)."
BR-04: "La razón social no coincide con el proveedor."
BR-05: "El monto excede el límite contractual de $X."
BR-06: "El contrato no está vigente."
BR-07: "Monto mayor a $500,000 - requiere auditoría externa."
BR-08: "Nivel de riesgo elevado detectado."
BR-09: "Se detectó posible fraccionamiento de facturas."
```

---

### CU-P03: Consultar Estado de Factura (Flujo B)

| Campo | Valor |
|-------|-------|
| **Código** | CU-P03 |
| **Nombre** | Consultar Estado de Factura |
| **Actor** | Proveedor |
| **Precondiciones** | Proveedor autenticado |
| **Postcondiciones** | Visualización del estado actual |

#### Flujo Principal
1. Proveedor navega a "Mis facturas"
2. Sistema muestra lista de facturas del proveedor
3. Proveedor filtra por año/mes/estado
4. Proveedor hace clic en "Ver"
5. Sistema muestra modal de detalle

#### Respuesta Esperada por Estado

| Estado | Información Mostrada | Color Indicador |
|--------|---------------------|----------------|
| **Pendiente** | Factura, Fecha, Monto, "En revisión" | 🟡 Amarillo |
| **Aprobada** | Factura, Fecha, Monto, "Aprobada", Mensaje | 🟢 Verde |
| **Escalada** | Factura, Fecha, Monto, "En revisión manual", Recomendación del auditor | 🟠 Naranja |
| **Rechazada** | Factura, Fecha, Monto, "Rechazada", **Motivo específico** | 🔴 Rojo |
| **Pagada** | Factura, Fecha, Monto, CBU, Fecha pago, N° comprobante | 🔵 Azul |

#### Detalle del Modal

**Para facturas RECHAZADAS:**
```
┌─────────────────────────────────────────────┐
│  ❌ FACTURA RECHAZADA                        │
├─────────────────────────────────────────────┤
│  Número: FC-2026-SUP001-001                 │
│  Fecha: 15/07/2026                          │
│  Monto: $45,000.00                          │
│  Estado: RECHAZADA                          │
├─────────────────────────────────────────────┤
│  MOTIVO DEL RECHAZO:                        │
│  ───────────────────                        │
│  El monto excede el límite contractual      │
│  de $40,000 para el período actual.         │
│                                              │
│  Para más información, contacte a su         │
│  representante de cuentas a pagar.           │
└─────────────────────────────────────────────┘
```

**Para facturas APROBADAS:**
```
┌─────────────────────────────────────────────┐
│  ✅ FACTURA APROBADA                         │
├─────────────────────────────────────────────┤
│  Número: FC-2026-SUP001-002                 │
│  Fecha: 16/07/2026                          │
│  Monto: $35,000.00                          │
│  Estado: APROBADA                           │
├─────────────────────────────────────────────┤
│  La factura ha sido aprobada y se encuentra  │
│  en proceso de pago.                        │
│  Estimación de pago: 30 días corridos.       │
└─────────────────────────────────────────────┘
```

---

### CU-P04: Usar Chat de Soporte (Proveedor)

| Campo | Valor |
|-------|-------|
| **Código** | CU-P04 |
| **Nombre** | Usar Chat de Soporte |
| **Actor** | Proveedor |
| **Precondiciones** | Proveedor autenticado |
| **Postcondiciones** | Respuesta a consulta |

#### Consultas y Respuestas Esperadas

| Consulta del Proveedor | Respuesta del Sistema |
|------------------------|----------------------|
| "Hola" | "¡Hola! Soy el asistente de InvoiceFlow. ¿En qué puedo ayudarte hoy?" |
| "¿Cuál es el estado de mi factura FC-2026-SUP001-001?" | "Tu factura FC-2026-SUP001-001 está: [APROBADA/RECHAZADA/ESCALADA/PENDIENTE]. [Detalle adicional]" |
| "¿Cuándo voy a cobrar?" | "Las facturas aprobadas tienen un plazo estimado de 30 días para el pago." |
| "¿Por qué fue rechazada mi factura?" | "Tu factura fue rechazada porque: [MOTIVO ESPECÍFICO]. Puedes contactarte con soporte para más información." |
| "Lista mis facturas pendientes" | "Tienes [N] facturas pendientes de revisión." |
| "¿Cuál es mi límite de crédito?" | "Tu límite de crédito actual es de $X.XX." |
| "Tengo un problema técnico" | "Para problemas técnicos, por favor contacta a soporte@empresa.com incluyendo tu ID de proveedor." |
| "¿Cómo subo una factura?" | "Para subir una factura, ve a la sección 'Subir Factura' y arrastra tu archivo PDF." |
| [Info interna del sistema] | "No puedo compartir esa información. ¿Hay algo más en lo que pueda ayudarte?" |

---

### CU-P05: Cerrar Sesión

| Campo | Valor |
|-------|-------|
| **Código** | CU-P05 |
| **Nombre** | Cerrar Sesión |
| **Actor** | Proveedor |
| **Precondiciones** | Proveedor autenticado |
| **Postcondiciones** | Sesión terminada |

#### Respuesta Esperada
```
ÉXITO: Redirigir a pantalla de login
Sesión limpiada correctamente
```

---

## 3. Casos de Uso — Back Office

---

### CU-B01: Ver Dashboard

| Campo | Valor |
|-------|-------|
| **Código** | CU-B01 |
| **Nombre** | Ver Dashboard |
| **Actor** | Administrador |
| **Precondiciones** | Acceso al Back Office |
| **Postcondiciones** | Visualización de estadísticas |

#### Información Mostrada en Dashboard

**Tarjetas de Estado (5 badges)**
| Tarjeta | Descripción | Ejemplo |
|---------|-------------|---------|
| En Inbox | Facturas pendientes | 12 facturas |
| Aprobadas (mes) | Facturas aprobadas este mes | 45 facturas |
| Escaladas | En revisión manual | 3 facturas |
| Rechazadas (mes) | Rechazadas este mes | 8 facturas |
| Total Aprobado | Suma de montos | $2,450,000.00 |

**Tabla de Últimos Pagos**
| Columna | Ejemplo |
|---------|---------|
| Fecha | 18/07/2026 |
| Factura | FC-2026-SUP001-001 |
| Proveedor | Proveedor Demo SA |
| Monto | $45,000.00 |
| Decisión | APPROVED |
| Comprobante | INV-2026-001234 |

#### Respuesta Esperada
```
Dashboard carga con:
- 5 tarjetas de métricas actualizadas
- Tabla con últimos 10 pagos
- Datos actualizados en tiempo real
```

---

### CU-B02: Gestionar Inbox

| Campo | Valor |
|-------|-------|
| **Código** | CU-B02 |
| **Nombre** | Gestionar Inbox |
| **Actor** | Administrador |
| **Precondiciones** | Acceso al Back Office |
| **Postcondiciones** | Facturas procesadas o movidas |

#### Sub-funcionalidades

**B-B02.1: Ver Facturas Pendientes**
```
Entrada: Ninguna (carga automática)
Salida: Lista de facturas en inbox con:
  - Nombre archivo
  - Número factura
  - Proveedor
  - Monto
  - Tamaño
  - Fecha recepción
```

**B-B02.2: Subir Factura Manualmente**
```
Entrada: Archivo (JSON o TXT)
Validación: Formato correcto
Salida Éxito: "Factura agregada al inbox"
Salida Error: "Formato no válido. Use JSON o TXT."
```

**B-B02.3: Procesar Factura Individual**
```
Entrada: Seleccionar factura del inbox
Acción: Click en "Procesar"
Salida Éxito: 
  - Factura aprobada → "Factura aprobada"
  - Factura rechazada → "Factura rechazada: [MOTIVO]"
  - Factura escalada → "Factura escalada para revisión"
Salida Error: "Error al procesar: [DESCRIPCIÓN]"
```

**B-B02.4: Procesar Todas**
```
Entrada: Click en "Procesar todo"
Acción: Itera sobre todas las facturas del inbox
Salida: 
  - "Procesadas X de Y facturas"
  - "X aprobadas, Y rechazadas, Z escaladas"
```

**B-B02.5: Agrupar por Proveedor**
```
Entrada: Click en "Agrupar"
Acción: Crea carpetas por CUIT
Salida Éxito: "X carpetas creadas"
```

---

### CU-B03: Revisar Historial

| Campo | Valor |
|-------|-------|
| **Código** | CU-B03 |
| **Nombre** | Revisar Historial |
| **Actor** | Administrador |
| **Precondiciones** | Acceso al Back Office |
| **Postcondiciones** | Visualización del historial completo |

#### Filtros Disponibles
| Filtro | Opciones |
|--------|----------|
| Proveedor | Lista / Texto libre |
| Año | Todos, 2025, 2026 |
| Mes | Todos, Enero-Diciembre |
| Estado | Todos, Aprobada, Rechazada, Escalada, Pendiente |

#### Columnas del Historial
| Columna | Descripción | Ejemplo |
|---------|-------------|---------|
| Fecha | Procesamiento | 18/07/2026 |
| Factura | Número | FC-2026-SUP001-001 |
| Proveedor | ID/Nombre | SUP001 - Demo SA |
| Monto | Importe | $45,000.00 |
| Decisión | Resultado | APPROVED |
| Confirmación | ID | INV-2026-001234 |
| Estado | Pago | PENDIENTE |
| Motivo | Razón | Límite excedido |

#### Respuesta Esperada
```
Historial muestra:
- Tabla con todas las facturas procesadas
- Totales por estado
- Exports disponibles (si implementado)
```

---

### CU-B04: Usar Chat Interno (Administrador)

| Campo | Valor |
|-------|-------|
| **Código** | CU-B04 |
| **Nombre** | Usar Chat Interno |
| **Actor** | Administrador |
| **Precondiciones** | Acceso al Back Office |
| **Postcondiciones** | Acciones ejecutadas o información proporcionada |

#### Comandos y Respuestas

| Comando | Acción | Respuesta |
|---------|--------|-----------|
| "procesá todo el inbox" | Procesa todas las facturas | "Procesando X facturas..." + resultado |
| "procesá FC-XXX" | Procesa factura específica | "Factura procesada: [RESULTADO]" |
| "mostrame las rechazadas" | Lista rechazadas | Tabla con facturas rechazadas |
| "mostrame las aprobadas" | Lista aprobadas | Tabla con facturas aprobadas |
| "calculá el total aprobado" | Suma montos aprobados | "Total aprobado este mes: $X" |
| "¿cuántas facturas hay en inbox?" | Cuenta inbox | "Hay X facturas pendientes" |
| "resumen del día" | Estadísticas diarias | Resumen con métricas del día |

#### Ejemplo de Respuesta

**Input:** "procesá todo el inbox"
```
Procesando inbox...
─────────────────────
FC-001: ✅ Aprobada
FC-002: ❌ Rechazada (monto excedido)
FC-003: ⚠️ Escalada (requiere auditoría)
FC-004: ✅ Aprobada
─────────────────────
Total: 4 facturas
Aprobadas: 2 | Rechazadas: 1 | Escaladas: 1
```

---

### CU-B05: Monitorear Sistema (Observabilidad)

| Campo | Valor |
|-------|-------|
| **Código** | CU-B05 |
| **Nombre** | Monitorear Sistema |
| **Actor** | Administrador |
| **Precondiciones** | Acceso al Back Office → Pestaña Observabilidad |
| **Postcondiciones** | Visualización del estado de servicios |

#### Estado de Servicios

| Servicio | Puerto | Estado Esperado | Color |
|----------|--------|-----------------|-------|
| Backend FastAPI | 8000 | ✅ Online | Verde |
| Supplier Service | 8001 | ✅ Online | Verde |
| Contract Service | 8002 | ✅ Online | Verde |
| MCP Toolbox | 5000 | ⚪ Opcional | Gris |
| External Auditor | 8003 | ⚪ Opcional | Gris |

#### Información de Logs

| Nivel | Color | Significado |
|-------|-------|------------|
| INFO | Verde | Evento normal |
| WARNING | Amarillo | Atención requerida |
| ERROR | Rojo | Problema detectado |
| DEBUG | Gris | Información de depuración |

#### Respuesta Esperada
```
Observabilidad muestra:
- Health Score: [0-100]%
- Estado de servicios: [ONLINE/OFFLINE]
- Últimos 500 logs en detalle
- Métricas de bases de datos
- Estado de archivos
```

---

### CU-B06: Ver Logs en Detalle

| Campo | Valor |
|-------|-------|
| **Código** | CU-B06 |
| **Nombre** | Ver Logs en Detalle |
| **Actor** | Administrador |
| **Precondiciones** | Acceso al Back Office |
| **Postcondiciones** | Visualización de logs |

#### Respuesta Esperada

```
┌──────────────────────────────────────────────────────┐
│  📜 TODOS LOS LOGS (últimas 500 entradas)           │
├──────────────────────────────────────────────────────┤
│  🟢 2026-07-18 14:30:25 [INFO] Sistema iniciado    │
│  🟢 2026-07-18 14:30:26 [INFO] Puerto 8000 listo  │
│  🟢 2026-07-18 14:31:00 [INFO] Factura procesada  │
│  🟡 2026-07-18 14:32:15 [WARNING] Timeout servicio │
│  🔴 2026-07-18 14:33:00 [ERROR] Conexión perdida   │
│  ...                                                 │
└──────────────────────────────────────────────────────┘
```

---

### CU-B07: Revisar Documentación

| Campo | Valor |
|-------|-------|
| **Código** | CU-B07 |
| **Nombre** | Revisar Documentación |
| **Actor** | Administrador |
| **Precondiciones** | Acceso al Back Office |
| **Postcondiciones** | Acceso a documentación |

#### Contenido Disponible
- Guía de uso del sistema
- Formatos de archivo aceptados
- Endpoints de la API
- Especificaciones técnicas

---

## 4. Casos de Uso — Sistema Automático

---

### CU-S01: Validación Automática de Facturas

| Campo | Valor |
|-------|-------|
| **Código** | CU-S01 |
| **Nombre** | Validación Automática de Facturas |
| **Actor** | Sistema |
| **Trigger** | Archivo放入 inbox |
| **Postcondiciones** | Factura validada y decisión tomada |

#### Pipeline de Validación

```
1. VALIDACIÓN ESTRUCTURAL (VR)
   ├── VR-01: Formato PDF
   ├── VR-02: Tamaño ≤10MB
   ├── VR-03: Campos obligatorios
   ├── VR-04: CUIT válido
   ├── VR-05: Fecha válida
   ├── VR-06: Monto > 0
   └── VR-07: No duplicada

2. VALIDACIÓN DE PROVEEDOR (BR)
   ├── BR-01: Proveedor existe
   └── BR-02: Proveedor activo

3. VALIDACIÓN CONTRACTUAL (BR)
   ├── BR-03: Factura no vencida
   ├── BR-04: Razón social coincide
   ├── BR-05: Dentro del límite
   └── BR-06: Contrato vigente

4. EVALUACIÓN DE RIESGO (BR)
   ├── BR-07: Monto ≤ $500k
   ├── BR-08: Riesgo bajo
   └── BR-09: Sin fraccionamiento
```

#### Posibles Decisiones

| Decisión | Condición | Archivo destino |
|----------|-----------|-----------------|
| APPROVED | Todas las validaciones pasan | `data/processed/` |
| REJECTED | Alguna validación estructural falla | `data/rejected/` |
| ESCALATED | BR-06, BR-07, BR-08, o BR-09 falla | Mantener en inbox |

---

### CU-S02: Escalado a Auditor Externo (A2A)

| Campo | Valor |
|-------|-------|
| **Código** | CU-S02 |
| **Nombre** | Escalado a Auditor Externo |
| **Actor** | Sistema / Auditor Externo |
| **Trigger** | Monto > $500,000 o BR-07 |
| **Postcondiciones** | Recomendación del auditor |

#### Flujo A2A
1. Sistema detecta factura > $500k
2. Sistema envía solicitud A2A a External Auditor
3. Auditor evalúa con contexto adicional
4. Auditor retorna recomendación
5. Sistema aplica recomendación

#### Respuesta del Auditor
```
{
  "invoice_id": "FC-2026-SUP001-001",
  "recommendation": "APPROVED" | "REJECTED" | "ESCALATE",
  "reason": "Justificación de la recomendación",
  "confidence": 0.95,
  "risk_factors": ["lista de factores"]
}
```

---

### CU-S03: File Watcher Automático

| Campo | Valor |
|-------|-------|
| **Código** | CU-S03 |
| **Nombre** | File Watcher Automático |
| **Actor** | Sistema |
| **Trigger** | Nuevo archivo en inbox |
| **Postcondiciones** | Factura procesada automáticamente |

#### Respuesta Esperada
```
[Watcher] Nuevo archivo detectado: factura.txt
[Watcher] Moviendo a procesamiento...
[Watcher] Ejecutando pipeline de validación...
[Watcher] Resultado: APPROVED
[Watcher] Moviendo a /processed/
```

---

### CU-S04: RAG - Consulta de Contratos

| Campo | Valor |
|-------|-------|
| **Código** | CU-S04 |
| **Nombre** | Consulta de Contratos (RAG) |
| **Actor** | Sistema / Contract Agent |
| **Trigger** | Validación de límite contractual |
| **Postcondiciones** | Límite obtenido de ChromaDB |

#### Consulta Típica
```
Input: "límite de crédito proveedor SUP001"
RAG Output: "El proveedor SUP001 tiene un límite de $100,000 
            con modo EXACTO para el período 2026."
```

---

## 5. Casos de Uso — Agentes y Chat

---

### CU-A01: Clasificación de Intenciones (Router Agent)

| Campo | Valor |
|-------|-------|
| **Código** | CU-A01 |
| **Nombre** | Clasificación de Intenciones |
| **Actor** | Router Agent |
| **Trigger** | Mensaje de chat recibido |
| **Postcondiciones** | Intención identificada |

#### Intenciones Reconocidas

| Intención | Ejemplo de Input | Respuesta del Agente |
|-----------|------------------|---------------------|
| `list_invoices` | "listar mis facturas" | Lista de facturas |
| `check_status` | "estado de factura X" | Estado de factura |
| `payment_date` | "¿cuándo cobro?" | Fecha estimada |
| `rejection_reason` | "¿por qué rechazaron?" | Motivo de rechazo |
| `summary` | "resumen" | Resumen general |
| `help` | "ayuda" | Guía de uso |
| `greeting` | "hola" | Saludo amigable |
| `unknown` | [cualquier otro] | "No entendí" |

---

### CU-A02: Validación de Proveedor (Validator Agent)

| Campo | Valor |
|-------|-------|
| **Código** | CU-A02 |
| **Nombre** | Validación de Proveedor |
| **Actor** | Validator Agent |
| **Trigger** | Nueva factura recibida |
| **Postcondiciones** | Validación completada |

#### Respuesta del Validator
```
{
  "supplier_id": "SUP001",
  "exists": true,
  "active": true,
  "credit_limit": 100000,
  "current_usage": 45000,
  "available_credit": 55000,
  "validation_passed": true,
  "validation_errors": []
}
```

---

### CU-A03: Búsqueda en Contratos (Contract Agent)

| Campo | Valor |
|-------|-------|
| **Código** | CU-A03 |
| **Nombre** | Búsqueda en Contratos |
| **Actor** | Contract Agent |
| **Trigger** | Consulta de límite o contrato |
| **Postcondiciones** | Información del contrato retornada |

#### Respuesta del Contract Agent
```
{
  "supplier_id": "SUP001",
  "contract_found": true,
  "contract_mode": "EXACTO",
  "credit_limit": 100000,
  "period": "2026",
  "status": "ACTIVE",
  "remaining_credit": 55000,
  "rag_context": "Contexto del contrato encontrado..."
}
```

---

## 6. Matriz de Respuestas

### 6.1 Respuestas del Sistema — Back Office

| Acción | Respuesta Exitosa | Respuesta con Error |
|--------|-------------------|---------------------|
| Ver Dashboard | Dashboard con métricas | "Error al cargar dashboard" |
| Subir factura manual | "Archivo agregado" | "Formato no válido" |
| Procesar factura | "[APROBADA/RECHAZADA/ESCALADA]" | "Error en el procesamiento" |
| Procesar inbox | "X/Y procesadas" | "Error parcial: X fallidas" |
| Consultar historial | Tabla con resultados | "No se encontraron resultados" |
| Usar chat | Respuesta del agente | "Servicio de chat no disponible" |
| Ver observabilidad | Panel con métricas | "Error al conectar con servicios" |

### 6.2 Respuestas del Portal Proveedor

| Acción | Respuesta Exitosa | Respuesta con Error |
|--------|-------------------|---------------------|
| Login | Redirigir a dashboard | Mensaje de error específico |
| Subir factura | Resultado de validación | Mensaje de validación |
| Consultar estado | Modal con detalle | "Factura no encontrada" |
| Usar chat | Respuesta del agente | "Servicio no disponible" |
| Cerrar sesión | Redirigir a login | (N/A) |

---

## 7. Códigos de Error y Estados

### 7.1 Estados de Factura

| Estado | Código | Descripción |
|--------|--------|-------------|
| Pendiente | `PENDING` | Factura en cola de procesamiento |
| En Proceso | `PROCESSING` | Factura siendo procesada |
| Aprobada | `APPROVED` | Factura aprobada automáticamente |
| Rechazada | `REJECTED` | Factura rechazada por validaciones |
| Escalada | `ESCALATED` | Factura pendiente de revisión manual |
| Pagada | `PAID` | Factura con pago realizado |
| Cancelada | `CANCELLED` | Factura cancelada por el proveedor |

### 7.2 Estados de Pago

| Estado | Descripción |
|--------|-------------|
| `PENDING` | Pendiente de pago |
| `IN_PROGRESS` | Pago en proceso |
| `PAID` | Pagada |
| `OVERDUE` | Vencida |
| `CANCELLED` | Cancelada |

### 7.3 Códigos de Error

| Código | Mensaje | Causa |
|--------|---------|-------|
| `E001` | Proveedor no encontrado | ID de proveedor inválido |
| `E002` | Proveedor inactivo | Cuenta deshabilitada |
| `E003` | Límite excedido | Monto > límite contractual |
| `E004` | Factura duplicada | Número de factura ya existe |
| `E005` | Contrato no vigente | Contrato expirado |
| `E006` | Formato inválido | Archivo no es PDF |
| `E007` | Archivo muy grande | > 10MB |
| `E008` | Campos faltantes | Falta información obligatoria |
| `E009` | CUIT inválido | Formato de CUIT incorrecto |
| `E010` | Fecha inválida | Fecha futura o malformada |
| `E011` | Monto inválido | Monto ≤ 0 |
| `E012` | Razón social no coincide | Nombre diferente al registrado |
| `E013` | Factura vencida | > 30 días de antigüedad |
| `E014` | Fraccionamiento detectado | Múltiples facturas similares |
| `E015` | Riesgo elevado | Score de riesgo alto |
| `E099` | Error interno | Problema en el sistema |

---

## 8. Endpoints de API

### Back Office (Puerto 8000)

| Método | Endpoint | Descripción | Respuesta |
|--------|----------|-------------|-----------|
| GET | `/health` | Health check | `{"status": "ok"}` |
| GET | `/health/observability` | Estado completo | Objeto de observabilidad |
| GET | `/logs/recent?lines=500` | Logs detallados | Lista de logs |
| GET | `/dashboard` | Dashboard | HTML del dashboard |
| GET | `/inbox` | Facturas pendientes | JSON con facturas |
| POST | `/inbox/upload` | Subir factura | Resultado de procesamiento |
| GET | `/invoices` | Historial | JSON con facturas |
| GET | `/chat` | Chat IA | Respuesta del agente |

### Supplier Portal (Puerto 8000)

| Método | Endpoint | Descripción | Respuesta |
|--------|----------|-------------|-----------|
| GET | `/supplier/` | Portal proveedor | HTML del portal |
| GET | `/supplier/login` | Login | Autenticación |
| GET | `/supplier/dashboard` | Dashboard | Datos del proveedor |
| GET | `/supplier/invoices` | Facturas | Lista de facturas |
| GET | `/supplier/invoice/{id}` | Detalle | Detalle de factura |

### Microservicios

| Servicio | Puerto | Endpoint | Descripción |
|----------|--------|----------|-------------|
| Supplier Service | 8001 | `/health` | Health check |
| Contract Service | 8002 | `/health` | Health check |
| MCP Toolbox | 5000 | `/health` | Health check |
| External Auditor | 8003 | `/health` | Health check |

---

*Documento generado: 2026-07-18*
*Sistema: InvoiceFlow v3.1.0*
