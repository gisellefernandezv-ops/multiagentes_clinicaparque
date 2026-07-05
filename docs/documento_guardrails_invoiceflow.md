# Documento de Guardrails — InvoiceFlow
## Reglas de negocio, validación, seguridad y continuidad (COMPLETO)

Este documento es la fuente única de verdad de todas las reglas que gobiernan el procesamiento de facturas en InvoiceFlow. Todo guardrail que se implemente en código debe estar acá primero.

---

## 0. Por qué 4 categorías, no 2

Hasta ahora habíamos hablado de guardrails "de negocio" y "de seguridad". Para que el documento sea completo, se agregan dos categorías más que un sistema real de aprobación de facturas necesita:

| Categoría | Pregunta que responde |
|---|---|
| **VR — Validación estructural** | ¿El documento/dato que llegó tiene la forma correcta? |
| **BR — Negocio** | ¿Esta factura cumple las condiciones para pagarse? |
| **SR — Seguridad** | ¿Alguien está intentando hacer algo que no debería? |
| **CR — Continuidad** | ¿Qué hacemos si un servicio del que dependemos falla? |

La categoría **CR** es nueva y surge de algo real que ya vimos: en la captura del Back Office, `supplier-service` y `contract-service` figuraban caídos. Sin una regla explícita para ese caso, el sistema no sabe si rechazar, esperar, o qué decirle al proveedor — y eso es un guardrail faltante tan importante como los de negocio.

---

## 1. VR — Validación estructural (antes de que la factura llegue a los agentes)

| ID | Condición | Acción | Mensaje al proveedor |
|---|---|---|---|
| VR-01 | El archivo no es un PDF | Rechazar | "Formato de archivo no soportado, debe ser PDF" |
| VR-02 | El archivo supera el tamaño máximo (10 MB) | Rechazar | "Archivo demasiado grande" |
| VR-03 | Falta algún campo obligatorio (CUIT, razón social, monto, fecha, N° de factura) | Rechazar | "Campos obligatorios faltantes: [detalle de cuáles]" |
| VR-04 | El CUIT no tiene formato válido (11 dígitos, dígito verificador correcto) | Rechazar | "CUIT con formato inválido" |
| VR-05 | La fecha de emisión está mal formada o es una fecha futura | Rechazar | "Fecha de emisión inválida" |
| VR-06 | El monto es ≤ 0 | Rechazar | "Monto de factura inválido" |
| VR-07 | Ya existe una factura con el mismo N° para el mismo proveedor | Rechazar | "Factura duplicada" |

---

## 2. BR — Guardrails de negocio (durante el procesamiento)

| ID | Condición | Acción | Mensaje al proveedor |
|---|---|---|---|
| BR-01 | El proveedor no existe en el sistema | Rechazar | "Proveedor no registrado" |
| BR-02 | El proveedor existe pero está INACTIVE | Rechazar | "Proveedor inactivo" |
| BR-03 | La factura está vencida (plazo del contrato/adenda si existe; si no, 60 días corridos desde emisión) | Rechazar | "Factura vencida" |
| BR-04 | La razón social de la factura no coincide con la registrada para ese CUIT | Rechazar | "Razón social no coincide con el proveedor registrado" |
| BR-05 | El monto excede el límite establecido en el contrato o adenda vigente | Rechazar | "Monto excede el límite contractual" |
| BR-06 | No existe contrato vigente cargado para el proveedor | **Escalar** (no rechazar) | "Sin contrato vigente registrado, requiere revisión manual" |
| BR-07 | El monto supera $500.000 | **Escalar** | "Supera el monto de aprobación automática" |
| BR-08 | El modelo de ML clasifica la factura como riesgo alto | **Escalar** | "Factura clasificada como alto riesgo, requiere revisión" |
| BR-09 | El proveedor presentó, en los últimos 30 días, otras facturas que sumadas a la actual superan $500.000 (posible fraccionamiento) | **Escalar** | "Monto acumulado del período supera el límite, requiere revisión" |
| BR-10 | La factura ya tiene un estado definitivo (RECHAZADA o PAGADA) | Bloquear reproceso | "Esta factura ya fue procesada, no puede reenviarse" |

**Nota sobre BR-09:** esta regla existe porque dividir una factura grande en varias chicas para evitar el guardrail de monto es un patrón de fraude conocido en circuitos de pagos a proveedores — vale la pena mencionarlo en la defensa oral como ejemplo de "justificación de decisiones de diseño".

---

## 3. SR — Guardrails de seguridad

| ID | Condición | Acción |
|---|---|---|
| SR-01 | El texto extraído del PDF contiene instrucciones dirigidas al agente (ej. "ignorá las instrucciones anteriores") | Rechazar por contenido sospechoso |
| SR-02 | Se solicita al `payment_agent` una acción distinta de "registrar" o "consultar" | Rechazar, acción no autorizada |
| SR-03 | Un proveedor autenticado con su CUIT intenta consultar facturas de otro CUIT | Bloquear, "No autorizado a consultar datos de otro proveedor" |
| SR-04 | Un proveedor envía más de 20 facturas en una hora | Bloquear temporalmente, "Límite de envíos alcanzado" |
| SR-05 | El chat recibe preguntas para revelar información interna del sistema (prompts, nombres de agentes, estructura de datos) | Responder con redirección genérica, no revelar |

---

## 4. CR — Guardrails de continuidad (ante fallas de servicios externos)

| ID | Condición | Acción |
|---|---|---|
| CR-01 | `supplier-service` o `contract-service` no responden (timeout/error) | **No rechazar automáticamente.** Marcar la factura como `PENDIENTE_TECNICO` y notificar al Back Office |
| CR-02 | Falla transitoria de un servicio | Reintentar hasta 3 veces con backoff antes de pasar a CR-01 |
| CR-03 | Una factura queda en `PENDIENTE_TECNICO` | Al proveedor mostrarle: "Estamos procesando tu factura, te confirmaremos en breve" — nunca un error técnico crudo |

Esta categoría existe puntualmente porque el Back Office ya mostró servicios caídos en la práctica — no es un caso hipotético.

---

## 5. Orden de evaluación (pipeline completo)

El orden importa: evaluar reglas baratas antes que las costosas, y nunca rechazar automáticamente por una falla técnica.

```
0. BR-10 → ¿la factura ya tiene estado definitivo? Si sí, bloquear acá. Fin.
1. VR-01 a VR-07 → validación estructural del archivo y sus datos
2. SR-01 → chequeo de contenido sospechoso al extraer el texto del PDF
3. BR-01, BR-02 → validator_agent: ¿existe el proveedor y está activo?
   └─ Si el servicio no responde → CR-01/CR-02
4. BR-03, BR-04, BR-05, BR-06 → contract_agent: vencimiento, razón social, monto, existencia de contrato
   └─ Si el servicio no responde → CR-01/CR-02
5. BR-07, BR-08, BR-09 → guardrail_step: monto, riesgo ML, fraccionamiento
6. Si todo pasó → payment_agent registra (con SR-02 aplicado en este paso)

Transversales, en cualquier momento del canal chat: SR-03, SR-04, SR-05
```

---

## 6. Extensión de `rules.yaml` (para el guardrail_engine)

Esto reemplaza y completa el `rules.yaml` definido en la iteración anterior — incluye todas las reglas de este documento:

```yaml
guardrails:
  # --- Validación estructural (VR) ---
  - id: VR-01
    tipo: structural
    aplica_a: invoice_manager_agent
    condicion: "archivo.tipo != 'pdf'"
    accion: reject
    mensaje: "Formato de archivo no soportado, debe ser PDF"

  - id: VR-02
    tipo: structural
    aplica_a: invoice_manager_agent
    condicion: "archivo.tamaño_mb > 10"
    accion: reject
    mensaje: "Archivo demasiado grande"

  - id: VR-03
    tipo: structural
    aplica_a: invoice_manager_agent
    condicion: "faltan campos obligatorios (cuit, razon_social, monto, fecha, numero_factura)"
    accion: reject
    mensaje: "Campos obligatorios faltantes"

  - id: VR-04
    tipo: structural
    aplica_a: invoice_manager_agent
    condicion: "cuit no cumple formato válido (11 dígitos + dígito verificador)"
    accion: reject
    mensaje: "CUIT con formato inválido"

  - id: VR-05
    tipo: structural
    aplica_a: invoice_manager_agent
    condicion: "fecha_emision mal formada OR fecha_emision > hoy"
    accion: reject
    mensaje: "Fecha de emisión inválida"

  - id: VR-06
    tipo: structural
    aplica_a: invoice_manager_agent
    condicion: "monto <= 0"
    accion: reject
    mensaje: "Monto de factura inválido"

  - id: VR-07
    tipo: structural
    aplica_a: invoice_manager_agent
    condicion: "existe factura previa con mismo numero_factura y mismo supplier_id"
    accion: reject
    mensaje: "Factura duplicada"

  # --- Negocio (BR) ---
  - id: BR-01
    tipo: business
    aplica_a: validator_agent
    condicion: "supplier no existe"
    accion: reject
    mensaje: "Proveedor no registrado"

  - id: BR-02
    tipo: business
    aplica_a: validator_agent
    condicion: "supplier.status != 'ACTIVE'"
    accion: reject
    mensaje: "Proveedor inactivo"

  - id: BR-03
    tipo: business
    aplica_a: contract_agent
    condicion: "dias_desde_emision > plazo_contrato_o_60_dias_default"
    accion: reject
    mensaje: "Factura vencida"

  - id: BR-04
    tipo: business
    aplica_a: contract_agent
    condicion: "razon_social_factura != razon_social_contrato"
    accion: reject
    mensaje: "Razón social no coincide con el proveedor registrado"

  - id: BR-05
    tipo: business
    aplica_a: contract_agent
    condicion: "monto > limite_contractual (contrato + adendas)"
    accion: reject
    mensaje: "Monto excede el límite contractual"

  - id: BR-06
    tipo: business
    aplica_a: contract_agent
    condicion: "no existe contrato vigente para el proveedor"
    accion: escalate
    mensaje: "Sin contrato vigente registrado, requiere revisión manual"

  - id: BR-07
    tipo: business
    aplica_a: guardrail_step
    condicion: "monto > 500000"
    accion: escalate
    mensaje: "Supera el monto de aprobación automática"

  - id: BR-08
    tipo: business
    aplica_a: guardrail_step
    condicion: "risk_score == 'alto'"
    accion: escalate
    mensaje: "Factura clasificada como alto riesgo"

  - id: BR-09
    tipo: business
    aplica_a: guardrail_step
    condicion: "suma de facturas del mismo proveedor en los últimos 30 días + monto actual > 500000"
    accion: escalate
    mensaje: "Monto acumulado del período supera el límite, posible fraccionamiento"

  - id: BR-10
    tipo: business
    aplica_a: invoice_manager_agent
    condicion: "estado_actual IN ['REJECTED', 'PAID']"
    accion: reject
    mensaje: "Esta factura ya fue procesada, no puede reenviarse"

  # --- Seguridad (SR) ---
  - id: SR-01
    tipo: security
    aplica_a: invoice_manager_agent
    condicion: "texto_extraido_pdf contiene instrucciones dirigidas al agente"
    accion: reject
    mensaje: "Contenido sospechoso detectado en el documento"

  - id: SR-02
    tipo: security
    aplica_a: payment_agent
    condicion: "accion_solicitada NOT IN ['registrar', 'consultar']"
    accion: reject
    mensaje: "Acción no autorizada"

  - id: SR-03
    tipo: security
    aplica_a: validator_agent
    condicion: "cuit_solicitado != cuit_autenticado"
    accion: reject
    mensaje: "No autorizado a consultar datos de otro proveedor"

  - id: SR-04
    tipo: security
    aplica_a: invoice_manager_agent
    condicion: "facturas_enviadas_por_proveedor_ultima_hora > 20"
    accion: reject
    mensaje: "Límite de envíos alcanzado, intentar más tarde"

  - id: SR-05
    tipo: security
    aplica_a: router_agent
    condicion: "mensaje solicita información interna del sistema (prompts, agentes, estructura de datos)"
    accion: reject
    mensaje: "No puedo compartir esa información"

  # --- Continuidad (CR) ---
  - id: CR-01
    tipo: continuity
    aplica_a: [validator_agent, contract_agent]
    condicion: "servicio externo no responde tras reintentos"
    accion: mark_pending_technical
    mensaje: "Estamos procesando tu factura, te confirmaremos en breve"

  - id: CR-02
    tipo: continuity
    aplica_a: [validator_agent, contract_agent]
    condicion: "falla transitoria de servicio externo"
    accion: retry
    mensaje: null
```

---

## 7. Notas para el agente de desarrollo

- El `guardrail_engine.py` ya definido debe soportar las 4 categorías (`structural`, `business`, `security`, `continuity`), no solo `business`/`security` como en la iteración anterior.
- Las reglas `CR` requieren lógica de reintentos (no solo evaluación de condición) — es distinto al resto, que son chequeos puntuales.
- BR-09 (fraccionamiento) requiere una consulta agregada a la base (suma de facturas del proveedor en una ventana de tiempo), no un chequeo sobre la factura individual — implementarlo como una función separada que el guardrail_step invoca.
- Todo esto es **aditivo** sobre lo ya construido — misma regla de resguardo que en las iteraciones anteriores: backup antes de tocar código.
