# SPECS 004 — Flujos de Negocio

> **Proyecto**: InvoiceFlow  
> **Tipo**: Especificación de Flujos  
> **Estado**: ✅ Implementado

---

## 1. Índice de Flujos

| Flujo | Descripción | Actor Principal |
|-------|-------------|----------------|
| **Flujo A** | Alta de factura nueva | Proveedor |
| **Flujo B** | Consulta de estado | Proveedor |
| **Flujo C** | Chat con soporte | Proveedor |
| **Flujo D** | Back Office | Administrador |

---

## 2. Flujo A — Alta de Factura Nueva

### 2.1 Diagrama de Secuencia

```
┌─────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│Proveedor│     │Orquestador    │     │  Validator   │     │  Contract    │
└────┬────┘     └───────┬──────┘     └──────┬───────┘     └──────┬───────┘
     │                   │                    │                    │
     │ 1. Identificarse │                    │                    │
     │──────────────────>│                    │                    │
     │                   │                    │                    │
     │                   │ 2. Validar (CUIT)  │                    │
     │                   │───────────────────>│                    │
     │                   │<──────────────────│                    │
     │                   │                    │                    │
     │ 3. Confirmar      │                    │                    │
     │   proveedor       │                    │                    │
     │<──────────────────│                    │                    │
     │                   │                    │                    │
     │ 4. Adjuntar PDF   │                    │                    │
     │──────────────────>│                    │                    │
     │                   │                    │                    │
     │                   │ 5. Extraer datos  │                    │
     │                   │────┐               │                    │
     │                   │    │               │                    │
     │                   │<───┘               │                    │
     │                   │                    │                    │
     │                   │ 6. Guardrail      │                    │
     │                   │────┐               │                    │
     │                   │    │               │                    │
     │                   │<───┘               │                    │
     │                   │                    │                    │
     │                   │                    │ 7. Buscar contrato │
     │                   │                    │───────────────────>│
     │                   │                    │<───────────────────│
     │                   │                    │                    │
     │                   │ 8. Registrar pago  │                    │
     │                   │────┐               │                    │
     │                   │    │               │                    │
     │                   │<───┘               │                    │
     │                   │                    │                    │
     │ 9. Resultado       │                    │                    │
     │<───────────────────│                    │                    │
```

### 2.2 Pasos Detallados

#### PASO 0: Identificación del Proveedor
1. Proveedor ingresa CUIT, nombre o ID
2. Orquestador llama a `validator_agent`
3. `validator_agent` usa `supplier_lookup_tool`
4. Si encontrado y ACTIVE → continuar
5. Si inactivo → mensaje de error
6. Si no encontrado → mensaje de error

#### PASO 1: Recepción del PDF
1. Proveedor adjunta archivo de factura
2. Sistema extrae datos con `extract_invoice_from_pdf`
3. Se extraen: invoice_id, amount, currency, invoice_date
4. Se verifica que el CUIT coincida

#### PASO 2: Guardrail Estructural
1. Orquestador llama a `run_invoice_guardrail_tool`
2. Se aplican 26 reglas de validación
3. Si `action = REJECT` → goto PASO 6
4. Si `action = ESCALATE` → goto PASO 5 (A2A)
5. Si `action = APPROVE` → continuar

#### PASO 3: Control Contractual (RAG)
1. Orquestador llama a `contract_agent`
2. `contract_agent` usa `search_contract_tool`
3. Se consulta ChromaDB por contrato
4. Se extrae límite contractual
5. Se compara con monto de factura
6. Si `within_limit = True` → continuar
7. Si `within_limit = False` → goto PASO 6

#### PASO 4: Registro de Pago
1. Orquestador llama a `payment_agent`
2. `payment_agent` usa `register_payment_tool`
3. Se inserta registro en SQLite
4. Se genera `confirmation_id` único

#### PASO 5: Escalado a Auditor Externo (A2A)
1. Si `decision = ESCALATED`
2. Orquestador invoca External Auditor via A2A
3. Auditor evalúa factura
4. Devuelve dictamen

#### PASO 6: Decisión Final
1. Orquestador compone respuesta final
2. Se muestra al proveedor
3. Sesión se cierra o inicia nueva consulta

### 2.3 Estados de Decisión

| Código | Significado | payment_status |
|--------|-------------|----------------|
| `APPROVED` | Factura aprobada | `PENDING_PAYMENT` |
| `REJECTED` | Factura rechazada | `REJECTED` |
| `ESCALATED` | Requiere revisión humana | `PENDING_HUMAN_REVIEW` |

### 2.4 Razones de Rechazo

| Código | Razón | Fuente |
|--------|-------|--------|
| R001 | Proveedor no encontrado | validator_agent |
| R002 | Proveedor inactivo | validator_agent |
| R003 | Factura duplicada | guardrail |
| R004 | Monto inválido | guardrail |
| R005 | Sin contrato vigente | contract_agent |
| R006 | Excede límite contractual | contract_agent |
| R007 | Fecha inválida | guardrail |
| R008 | Campos obligatorios faltantes | guardrail |

---

## 3. Flujo B — Consulta de Estado

### 3.1 Diagrama de Secuencia

```
┌─────────┐     ┌──────────────┐     ┌──────────────────────┐
│Proveedor│     │ RouterAgent   │     │ invoice_status_tool   │
└────┬────┘     └───────┬──────┘     └──────────┬───────────┘
     │                   │                       │
     │ 1. Consultar      │                       │
     │   estado          │                       │
     │──────────────────>│                       │
     │                   │                       │
     │                   │ 2. classify_intent     │
     │                   │────┐                  │
     │                   │    │                  │
     │                   │<───┘                  │
     │                   │                       │
     │                   │ 3. derive_action      │
     │                   │────┐                  │
     │                   │    │                  │
     │                   │<───┘                  │
     │                   │                       │
     │                   │ 4. check_status      │
     │                   │──────────────────────>│
     │                   │<──────────────────────│
     │                   │                       │
     │ 5. Respuesta      │                       │
     │<───────────────────│                       │
```

### 3.2 Estados Posibles

| Estado | Label | Icono | Color |
|--------|-------|-------|-------|
| `PENDING` | Pendiente | ⏳ | warning |
| `PENDING_PAYMENT` | Aprobada - En espera | ✅ | success |
| `PENDING_HUMAN_REVIEW` | En revisión manual | ⚠️ | warning |
| `REJECTED` | Rechazada | ❌ | danger |
| `PAID` | Pagada | 💰 | success |

---

## 4. Flujo C — Chat con Soporte

### 4.1 Clasificación de Intenciones

```
Usuario → RouterAgent → Clasificar intención
                           │
                           ├── new_invoice    → Orquestador (Flujo A)
                           ├── check_status  → invoice_status_tool (Flujo B)
                           ├── chitchat       → Respuesta directa
                           └── technical      → Instrucciones de soporte
```

### 4.2 Palabras Clave por Intención

| Intención | Keywords |
|-----------|----------|
| new_invoice | factura, subir, adjuntar, cargar, emitir |
| check_status | estado, consultar, progreso, cuándo, pago |
| chitchat | hola, gracias, adiós, cómo estás |
| technical_support | error, problema, no funciona, falló |

---

## 5. Flujo D — Back Office

### 5.1 Funcionalidades

| Sección | Funcionalidad |
|---------|---------------|
| **Dashboard** | Estadísticas, totales, gráfico de decisiones |
| **Inbox** | Facturas pendientes de procesar |
| **Historial** | Todas las facturas procesadas |
| **Chat interno** | Comunicación del equipo |
| **Estado Agentes** | Monitoreo de servicios |
| **Evaluación** | Resultados de golden cases |

---

## 6. Pipelines de Validación

### 6.1 Pipeline de Guardrails

```
┌────────────────────────────────────────────────────────────────┐
│                       PIPELINE DE VALIDACIÓN                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────────┐ │
│  │BR-10 │───>│  VR  │───>│ SR-01│───>│BR-01 │───>│  BR-03   │ │
│  │Chec- │    │Valid.│    │Seguri│    │Vali- │    │Contract: │ │
│  │k dup │    │ Est. │    │dad   │    │dator │    │Vencimien-│ │
│  └──────┘    └──────┘    └──────┘    └──────┘    │to        │ │
│                                                     └──────────┘ │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────────┐ │
│  │  BR-04   │───>│  BR-05   │───>│  BR-07, BR-08, BR-09     │ │
│  │Contract: │    │Contract: │    │  Guardrails de Montos    │ │
│  │Razón Soc│    │ Límite   │    │                          │ │
│  └──────────┘    └──────────┘    └──────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Orden de Prioridades

| Prioridad | Reglas | Descripción |
|-----------|--------|-------------|
| 1 | BR-10 | Verificar si ya fue procesada |
| 2 | VR-01..07 | Validación estructural |
| 3 | SR-01 | Seguridad (inyección) |
| 4 | BR-01..02 | Validación de proveedor |
| 5 | BR-03..06 | Validación contractual |
| 6 | BR-07..09 | Validación de montos |
| 7 | SR-02..05 | Validaciones de seguridad |
| 100+ | CR-01..03 | Continuidad operativa |

---

## 7. Referencias

| Documento | Descripción |
|-----------|-------------|
| `SPECS_002_AGENTES.md` | Detalle de agentes |
| `SPECS_003_HERRAMIENTAS.md` | Detalle de tools |
| `SPECS_005_GUARDRAILS.md` | Sistema de validación |

---

## 8. Formatos de Factura Soportados

### 8.1 Formato 1: Estándar AFIP

```
[EMISOR] Razon Social / CUIT / Condicion IVA / Ing. Brutos / Inicio Act.
[IDENTIFICACION] Codigo tipo / Punto de Venta / Numero / Fecha
...
TOTAL: $ XXX,XXX.XX
```

Campos extraídos:
- `invoice_id`: `FC-{punto_venta}-{numero}`
- `invoice_date`: `YYYY-MM-DD`
- `amount`: float

### 8.2 Formato 2: Factura Nueva (FC-2026-SUP001-NUEVA-X)

```
FACTURA A
Numero: FC-2026-SUP001-NUEVA-3
Fecha: 28/06/2026
...
TOTAL: ARS $ 25,000.00
```

Campos extraídos:
- `invoice_id`: `FC-2026-SUP001-NUEVA-3`
- `invoice_date`: `2026-06-28`
- `amount`: `25000.0`

### 8.3 Formato 3: Key:Value

```
invoice_id: FC-001-00000001
supplier_id: SUP001
amount: 50000
invoice_date: 2025-06-01
currency: ARS
```

### 8.4 Formato 4: JSON

```json
{
  "invoice_id": "FC-001-00000001",
  "supplier_id": "SUP001",
  "amount": 50000,
  "invoice_date": "2025-06-01",
  "currency": "ARS"
}
```

### 8.5 Notas sobre el Parser

El parser en `app/backend/watcher.py` detecta automáticamente el formato:
1. Si es `.json` → usa `json.loads()`
2. Si es `.txt` → detecta formato FACTURA o Key:Value
3. Extrae `supplier_id` del filename o del CUIT del emisor

> Ver `bugs/bugs_021.md` para detalles del parser.

---

**Versión**: 2.0.1  
**Última actualización**: 2026-07-15
