# SPECS 005 — Sistema de Guardrails

> **Proyecto**: InvoiceFlow  
> **Tipo**: Especificación de Seguridad  
> **Estado**: ✅ Implementado

---

## 1. Resumen del Sistema

El sistema de guardrails implementa **26 reglas** organizadas en 4 categorías para validar cada aspecto de las facturas de proveedores.

### 1.1 Estructura de Reglas

| Categoría | Código | Cantidad | Propósito |
|-----------|-------|----------|-----------|
| **VR** | Validación Estructural | 7 | Formato de archivo y datos |
| **BR** | Reglas de Negocio | 10 | Control de aprobación |
| **SR** | Seguridad | 5 | Protección contra accesos |
| **CR** | Continuidad | 3 | Manejo de fallas |

**Total: 26 reglas**

---

## 2. Reglas de Validación Estructural (VR)

### 2.1 Lista de Reglas

| ID | Condición | Acción | Mensaje |
|----|-----------|--------|---------|
| VR-01 | `archivo.tipo != 'pdf'` | reject | Formato de archivo no soportado, debe ser PDF |
| VR-02 | `archivo.tamanio_mb > 10` | reject | Archivo demasiado grande (máximo 10 MB) |
| VR-03 | `faltan_campos_obligatorios(...)` | reject | Campos obligatorios faltantes |
| VR-04 | `not_validar_cuit(cuit)` | reject | CUIT con formato inválido |
| VR-05 | `fecha_emision mal_formada OR > hoy` | reject | Fecha de emisión inválida |
| VR-06 | `monto <= 0` | reject | Monto de factura inválido |
| VR-07 | `existe_factura_duplicada(...)` | reject | Factura duplicada |

### 2.2 Campos Obligatorios

```python
CAMPOS_OBLIGATORIOS = [
    "cuit",
    "razon_social",
    "monto",
    "fecha",
    "numero_factura"
]
```

---

## 3. Reglas de Negocio (BR)

### 3.1 Lista de Reglas

| ID | Condición | Acción | Mensaje | Recoverable |
|----|-----------|--------|---------|-------------|
| BR-01 | `not existe_proveedor(supplier_id)` | reject | Proveedor no registrado | No |
| BR-02 | `proveedor.status != 'ACTIVE'` | reject | Proveedor inactivo | No |
| BR-03 | `dias_desde_emision > plazo` | reject | Factura vencida | No |
| BR-04 | `razon_social != contrato` | reject | Razón social no coincide | No |
| BR-05 | `monto > limite_contractual` | reject | Monto excede el límite | No |
| BR-06 | `not existe_contrato_vigente` | escalate | Sin contrato vigente | Sí |
| BR-07 | `monto > 500000` | escalate | Supera el monto de aprobación automática | Sí |
| BR-08 | `risk_score == 'alto'` | escalate | Factura clasificada como alto riesgo | Sí |
| BR-09 | `suma_facturas_30_dias + monto > 500000` | escalate | Posible fraccionamiento | Sí |
| BR-10 | `estado_actual IN ['REJECTED', 'PAID']` | block | Factura ya procesada | No |

---

## 4. Reglas de Seguridad (SR)

### 4.1 Lista de Reglas

| ID | Condición | Acción | Mensaje |
|----|-----------|--------|---------|
| SR-01 | `contenido contiene_inyeccion_prompt` | reject | Contenido sospechoso detectado |
| SR-02 | `accion NOT IN ['registrar', 'consultar']` | reject | Acción no autorizada |
| SR-03 | `cuit_solicitado != cuit_autenticado` | reject | No autorizado a consultar datos de otro proveedor |
| SR-04 | `facturas_enviadas > 20/hora` | block | Límite de envíos alcanzado |
| SR-05 | `solicita_info_interna_sistema` | redirect | No puedo compartir esa información |

### 4.2 Anti-Inyección

```python
# Patrones sospechosos
INYECTION_PATTERNS = [
    r"(?i)ignore previous instructions",
    r"(?i)system prompt",
    r"(?i)you are now",
    r"(?i)disregard",
    r"<script",
    r"{{",
]
```

---

## 5. Reglas de Continuidad (CR)

### 5.1 Lista de Reglas

| ID | Condición | Acción | Mensaje | Recoverable |
|----|-----------|--------|---------|-------------|
| CR-01 | `servicio_externo no_responde` | mark_pending_technical | Estamos procesando tu factura | Sí |
| CR-02 | `falla_transitoria` | retry | (automático) | Sí |
| CR-03 | `estado == 'PENDIENTE_TECNICO'` | wait | Estamos procesando tu factura | Sí |

### 5.2 Configuración de Reintentos

```yaml
CR-02:
  max_retries: 3
  backoff_seconds: [1, 2, 4]
```

---

## 6. Pipeline de Evaluación

### 6.1 Orden de Ejecución

```yaml
pipeline:
  orden:
    - paso: 0
      regla: BR-10          # ¿Ya fue procesada?
      
    - paso: 1
      reglas: [VR-01..VR-07]  # Validación estructural
      
    - paso: 2
      reglas: [SR-01]         # Seguridad (inyección)
      
    - paso: 3
      reglas: [BR-01, BR-02]  # Validar proveedor
      
    - paso: 4
      reglas: [BR-03..BR-06]  # Validación contractual
      
    - paso: 5
      reglas: [BR-07..BR-09]  # Validación de montos
      
    - paso: 6
      reglas: [SR-02]         # Seguridad (acciones)
```

### 6.2 Transversales (cualquier momento)

```yaml
transversales:
  - reglas: [SR-03, SR-04, SR-05]
    momento: cualquier
    canal: chat
```

---

## 7. Constantes del Sistema

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `MONTO_MAXIMO_AUTOAPROBACION` | 500,000 | Umbral de escalado |
| `PLAZO_FACTURA_DIAS` | 60 | Días para vencer |
| `VENTANA_FRAGMENTACION_DIAS` | 30 | Ventana anti-fragmentación |
| `LIMITE_FACTURAS_POR_HORA` | 20 | Rate limiting |
| `TAMANIO_MAXIMO_ARCHIVO_MB` | 10 | Tamaño máximo de PDF |

---

## 8. Configuración de Servicios

```yaml
servicios_externos:
  supplier_service:
    url: "http://127.0.0.1:8001"
    timeout_segundos: 5
    reintentos_max: 3

  contract_service:
    url: "http://127.0.0.1:8002"
    timeout_segundos: 5
    reintentos_max: 3
```

---

## 9. Archivo de Configuración

**Ubicación**: `guardrails/rules.yaml`

**Estructura**:
```yaml
guardrails:
  - id: VR-01
    tipo: structural
    aplica_a: invoice_manager_agent
    prioridad: 1
    condicion: "archivo.tipo != 'pdf'"
    accion: reject
    mensaje: "..."
    recoverable: false

pipeline:
  orden:
    - paso: 1
      reglas: [...]
```

---

## 10. Referencias

| Documento | Descripción |
|-----------|-------------|
| `guardrails/rules.yaml` | Archivo de configuración |
| `guardrails/guardrail_engine.py` | Motor de evaluación |
| `SPECS_004_FLUJOS.md` | Cómo se aplican en flujos |

---

**Versión**: 2.0.0  
**Última actualización**: 2026-07-15
