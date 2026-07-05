# InvoiceFlow — Documento de Casos de Uso

## Índice

1. [Actores del Sistema](#1-actores-del-sistema)
2. [Casos de Uso — Proveedor](#2-casos-de-uso--proveedor)
3. [Casos de Uso — Back Office](#3-casos-de-uso--back-office)
4. [Flujos Detallados](#4-flujos-detallados)
5. [Casuísticas y Escenarios](#5-casuísticas-y-escenarios)
6. [Diagrama de Casos de Uso](#6-diagrama-de-casos-de-uso)

---

## 1. Actores del Sistema

| Actor | Descripción | Rol |
|-------|-------------|-----|
| **Proveedor** | Empresa que emite facturas | Subir facturas, consultar estados |
| **Administrador** | Equipo de cuentas a pagar | Gestionar inbox, auditar, aprobar/rechazar escaladas |
| **Sistema** | Procesos automáticos | Validar, aprobar, rechazar, escalar automáticamente |

---

## 2. Casos de Uso — Proveedor

### 2.1 CU-P01: Iniciar Sesión en Portal

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-P01 |
| **Nombre** | Iniciar Sesión en Portal |
| **Actor** | Proveedor |
| **Precondiciones** | El proveedor debe estar registrado en el sistema |
| **Postcondiciones** | El proveedor accede a su dashboard personalizado |

#### Flujo Básico
1. El proveedor abre la URL del portal: `http://localhost:8000/supplier/`
2. El sistema muestra la pantalla de login
3. El proveedor ingresa su identificador (CUIT, nombre o ID)
4. El sistema valida las credenciales contra `supplier-service`
5. El sistema muestra el dashboard con los datos del proveedor

#### Flujos Alternativos

**FA-P01.1: Identificador no encontrado**
- Si el identificador no existe → Mostrar mensaje "Proveedor no encontrado"

**FA-P01.2: Proveedor inactivo**
- Si el proveedor está INACTIVE → Mostrar mensaje "Proveedor inactivo, contacte a soporte"

#### Campos del Formulario
| Campo | Tipo | Obligatorio | Validación |
|-------|------|-------------|------------|
| Identificador | Texto | Sí | Existe en la base de proveedores |

#### Proveedores de Prueba
```
SUP001, SUP002, SUP003, SUP004, SUP005
```

---

### 2.2 CU-P02: Subir Factura (Flujo A)

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-P02 |
| **Nombre** | Subir Factura |
| **Actor** | Proveedor |
| **Precondiciones** | Proveedor autenticado |
| **Postcondiciones** | Factura procesada y decisión registrada |

#### Flujo Básico
1. El proveedor navega a "Subir factura" desde el sidebar
2. El proveedor arrastra el archivo PDF al área de drop o hace clic para seleccionar
3. El sistema valida el archivo (formato PDF, tamaño ≤10MB)
4. El sistema extrae los datos de la factura
5. El sistema ejecuta el pipeline de guardrails:
   - Validación estructural (VR-01 a VR-07)
   - Validación de proveedor (BR-01, BR-02)
   - Validación contractual (BR-03 a BR-06)
   - Verificación de riesgo (BR-07 a BR-09)
6. El sistema muestra el resultado:
   - ✅ **Aprobada**: Factura aprobada automáticamente
   - ⚠️ **Escalada**: Requiere revisión manual
   - ❌ **Rechazada**: No cumple las reglas

#### Validaciones del Archivo
| Validación | Regla | Acción si falla |
|-----------|-------|-----------------|
| Formato | VR-01 | Rechazar |
| Tamaño | VR-02 (≤10MB) | Rechazar |
| Campos obligatorios | VR-03 | Rechazar |
| CUIT válido | VR-04 | Rechazar |
| Fecha válida | VR-05 | Rechazar |
| Monto > 0 | VR-06 | Rechazar |
| No duplicada | VR-07 | Rechazar |

#### Validaciones de Negocio
| Validación | Regla | Acción si falla |
|-----------|-------|-----------------|
| Proveedor existe | BR-01 | Rechazar |
| Proveedor activo | BR-02 | Rechazar |
| Factura no vencida | BR-03 | Rechazar |
| Razón social coincide | BR-04 | Rechazar |
| Dentro del límite | BR-05 | Rechazar |
| Contrato vigente | BR-06 | Escalar |
| Monto ≤ $500.000 | BR-07 | Escalar |
| Riesgo bajo | BR-08 | Escalar |
| Sin fraccionamiento | BR-09 | Escalar |

---

### 2.3 CU-P03: Consultar Estado de Factura (Flujo B)

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-P03 |
| **Nombre** | Consultar Estado de Factura |
| **Actor** | Proveedor |
| **Precondiciones** | Proveedor autenticado |
| **Postcondiciones** | El proveedor visualiza el estado actual de su factura |

#### Flujo Básico
1. El proveedor navega a "Mis facturas" desde el sidebar
2. El sistema muestra la lista de facturas del proveedor
3. El proveedor puede filtrar por:
   - Año (2025, 2026, etc.)
   - Mes (Enero a Diciembre)
   - Estado (Pendiente, Aprobada, Escalada, Rechazada, Pagada)
4. El proveedor hace clic en "Ver" de una factura
5. El sistema muestra el modal de detalle

#### Detalle según Estado

| Estado | Información mostrada |
|--------|---------------------|
| **Pendiente** | Fecha, monto, estado "En revisión" |
| **Aprobada** | Fecha, monto, estado, mensaje de aprobación |
| **Escalada** | Fecha, monto, estado "En revisión manual", resultado del auditor si disponible |
| **Rechazada** | Fecha, monto, estado, **motivo puntual del rechazo** |
| **Pagada** | Fecha, monto, CBU, fecha de pago, N° de comprobante |

#### Consulta por Chat
El proveedor también puede consultar por chat:
- "¿Cuál es el estado de mi factura FC-2026-SUP001-001?"
- "¿Cuándo voy a cobrar?"
- "¿Por qué fue rechazada mi factura?"

---

### 2.4 CU-P04: Usar Chat de Soporte

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-P04 |
| **Nombre** | Usar Chat de Soporte |
| **Actor** | Proveedor |
| **Precondiciones** | Proveedor autenticado |
| **Postcondiciones** | El proveedor recibe respuesta a su consulta |

#### Tipos de Consultas Soportadas

| Consulta | Respuesta del Sistema |
|----------|----------------------|
| Estado de facturas | Resumen de estados + instrucciones |
| Tiempos de pago | Información sobre fechas estimadas |
| Facturas rechazadas | Motivos de rechazo |
| Saludo general | Respuesta amigable + ayuda |
| Problemas técnicos | Instrucciones de soporte básico |

#### Seguridad (SR-05)
Si el proveedor pregunta sobre información interna del sistema (prompts, arquitectura, agentes), el sistema responde:
> "No puedo compartir esa información. ¿Hay algo más en lo que pueda ayudarte?"

---

### 2.5 CU-P05: Cerrar Sesión

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-P05 |
| **Nombre** | Cerrar Sesión |
| **Actor** | Proveedor |
| **Precondiciones** | Proveedor autenticado |
| **Postcondiciones** | Sesión terminada, redirigido a login |

#### Flujo
1. El proveedor hace clic en "Cerrar sesión" en el header
2. El sistema limpia los datos de sesión
3. El sistema redirige a la pantalla de login

---

## 3. Casos de Uso — Back Office

### 3.1 CU-B01: Ver Dashboard

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-B01 |
| **Nombre** | Ver Dashboard |
| **Actor** | Administrador |
| **Precondiciones** | Administrador con acceso al Back Office |
| **Postcondiciones** | El administrador visualiza estadísticas del sistema |

#### Información del Dashboard

**Tarjetas de Estado (5 badges)**
| Tarjeta | Descripción | Color |
|--------|-------------|-------|
| En Inbox | Facturas pendientes de procesar | Neutral |
| Aprobadas | Facturas aprobadas | Verde |
| Escaladas | Facturas en revisión manual | Naranja |
| Rechazadas | Facturas rechazadas | Rojo |
| Total Aprobado | Suma de montos aprobados | Azul |

**Tabla de Últimos Pagos**
| Columna | Descripción |
|---------|-------------|
| Fecha | Fecha de procesamiento |
| Factura | Número de factura |
| Proveedor | Nombre del proveedor |
| Monto | Importe de la factura |
| Decisión | APPROVED / REJECTED / ESCALATED |
| Comprobante | ID de confirmación |

**Filtros Disponibles**
- Año (Todos, 2025, 2026)
- Mes (Todos, Enero-Diciembre)

---

### 3.2 CU-B02: Gestionar Inbox

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-B02 |
| **Nombre** | Gestionar Inbox |
| **Actor** | Administrador |
| **Precondiciones** | Administrador con acceso al Back Office |
| **Postcondiciones** | Facturas procesadas o movidas a carpetas |

#### Sub-funcionalidades

**B-B02.1: Ver Facturas Pendientes**
- Lista de facturas en `platform/data/inbox/`
- Muestra: nombre archivo, factura, proveedor, monto, tamaño

**B-B02.2: Subir Factura Manualmente**
- Drag & drop de archivos JSON o TXT
- Validación de formato antes de procesar

**B-B02.3: Procesar Factura Individual**
- Seleccionar factura → clic en "Procesar"
- Ejecuta el flujo de aprobación automático

**B-B02.4: Procesar Todas las Facturas**
- Botón "Procesar todo el inbox"
- Ejecuta el flujo para todas las facturas pendientes

**B-B02.5: Agrupar Facturas**
- Agrupa facturas por CUIT de proveedor
- Crea carpetas automáticamente

---

### 3.3 CU-B03: Revisar Historial

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-B03 |
| **Nombre** | Revisar Historial |
| **Actor** | Administrador |
| **Precondiciones** | Administrador con acceso al Back Office |
| **Postcondiciones** | El administrador visualiza el historial completo de facturas |

#### Filtros Disponibles
| Filtro | Opciones |
|--------|----------|
| Proveedor | Lista de proveedores / texto libre |
| Año | Todos, 2025, 2026 |
| Estado | Todos, Aprobada, Rechazada, Escalada |

#### Columnas del Historial
| Columna | Descripción |
|---------|-------------|
| Fecha | Fecha de procesamiento |
| Factura | Número de factura |
| Proveedor | ID del proveedor |
| Monto | Importe |
| Decisión | APPROVED / REJECTED / ESCALATED |
| Confirmación | ID de confirmación |
| Estado | Estado de pago |
| Motivo | Razón del rechazo/escalado (si aplica) |

---

### 3.4 CU-B04: Usar Chat Interno

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-B04 |
| **Nombre** | Usar Chat Interno |
| **Actor** | Administrador |
| **Precondiciones** | Administrador con acceso al Back Office |
| **Postcondiciones** | El administrador recibe asistencia de IA |

#### Diferencia con Chat de Proveedor
> ⚠️ **IMPORTANTE**: Este chat es para el **equipo de administración**, diferenciado del chat de soporte que usan los proveedores.

#### Comandos Soportados
| Comando | Acción |
|---------|--------|
| "procesá todo el inbox" | Procesa todas las facturas pendientes |
| "procesá la factura FC-XXX" | Procesa una factura específica |
| "mostrame las rechazadas" | Lista facturas rechazadas |
| "calculá el total aprobado" | Muestra suma de aprobados |

---

### 3.5 CU-B05: Monitorear Estado de Agentes

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-B05 |
| **Nombre** | Monitorear Estado de Agentes (Observabilidad) |
| **Actor** | Administrador |
| **Precondiciones** | Administrador con acceso al Back Office |
| **Postcondiciones** | El administrador visualiza el estado de todos los servicios |

#### Métricas por Agente/Servicio

| Métrica | Descripción |
|---------|-------------|
| Estado | Online 🟢 / Caído 🔴 |
| Última ejecución | Tiempo desde última invocación |
| Invocaciones 24h | Cantidad de veces llamado |
| Tasa de error | Porcentaje de errores |

#### Servicios Monitoreados

| Servicio | Descripción |
|---------|-------------|
| invoice_orchestrator | Orquestador principal |
| validator_agent | Validación de proveedores |
| contract_agent | Control contractual |
| router_agent | Clasificador de chat |
| supplier-service | Microservicio de proveedores |
| contract-service | Microservicio de contratos |
| external-auditor | Agente auditor externo |

---

### 3.6 CU-B06: Ver Evaluación (LLM-as-a-Judge)

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-B06 |
| **Nombre** | Ver Resultados de Evaluación |
| **Actor** | Administrador |
| **Precondiciones** | Evaluaciones ejecutadas previamente |
| **Postcondiciones** | El administrador visualiza métricas de calidad |

#### Métricas Mostradas

| Métrica | Descripción | Umbral |
|---------|-------------|--------|
| Accuracy | % de decisiones correctas | ≥95% |
| Precision | Predicciones positivas correctas | ≥90% |
| Recall | Casos detectados correctamente | ≥90% |
| Casos Totales | Cantidad de golden cases evaluados | 20 |
| Casos Pasados | Golden cases que pasaron | - |
| Casos Fallidos | Golden cases que fallaron | - |

#### Detalle de Casos
Tabla con:
- ID del caso de prueba
- Categoría (structural, business, security, continuity, happy_path)
- Descripción
- Resultado (✅ Pasó / ❌ Falló)
- Score de evaluación

---

### 3.7 CU-B07: Revisar Documentación

| Atributo | Descripción |
|----------|-------------|
| **Código** | CU-B07 |
| **Nombre** | Revisar Documentación |
| **Actor** | Administrador |
| **Precondiciones** | Administrador con acceso al Back Office |
| **Postcondiciones** | El administrador accede a la documentación técnica |

#### Contenido Disponible
- Cómo usar el sistema
- Formas de procesar facturas
- Formatos de archivos aceptados
- Endpoints de la API
- Enlace a documentación Swagger/OpenAPI

---

## 4. Flujos Detallados

### 4.1 Flujo A: Alta de Factura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUJO A: ALTA DE FACTURA                             │
└─────────────────────────────────────────────────────────────────────────────┘

    PROVEEDOR                      SISTEMA                         AGENTES/TOOLS
         │                            │                                  │
         │  1. Sube PDF               │                                  │
         ├──────────────────────────►│                                  │
         │                            │                                  │
         │  2. Validar archivo       │                                  │
         │                            ├──VR-01: ¿Es PDF?──────────────────┤
         │                            ├──VR-02: ¿Tamaño ≤10MB?───────────┤
         │                            ├──VR-03: ¿Campos obligatorios?────┤
         │                            ├──VR-04: ¿CUIT válido?─────────────┤
         │                            ├──VR-05: ¿Fecha válida?────────────┤
         │                            ├──VR-06: ¿Monto > 0?──────────────┤
         │                            └──VR-07: ¿No duplicada?───────────┤
         │                            │                                  │
         │                            │  3. Extraer datos               │
         │                            │                                  │
         │                            │  4. Validar proveedor           │
         │                            ├──► validator_agent ─────────────┤
         │                            │     │                          │
         │                            │     ├──BR-01: ¿Existe?──────────┤
         │                            │     └──BR-02: ¿Activo?───────────┤
         │                            │                                  │
         │                            │  5. Validar contrato            │
         │                            ├──► contract_agent (RAG) ─────────┤
         │                            │     │                          │
         │                            │     ├──BR-03: ¿No vencida?──────┤
         │                            │     ├──BR-04: ¿Razón social OK?──┤
         │                            │     ├──BR-05: ¿Dentro límite?────┤
         │                            │     └──BR-06: ¿Contrato existe?─┤
         │                            │                                  │
         │                            │  6. Evaluar riesgo              │
         │                            │                                  │
         │                            │     ├──BR-07: ¿Monto ≤$500k?─────┤
         │                            │     ├──BR-08: ¿Riesgo bajo?─────┤
         │                            │     └──BR-09: ¿Sin fraccionar?──┤
         │                            │                                  │
         │                            │  7. Registrar decisión          │
         │                            ├──► payment_agent ──────────────┤
         │                            │     └──Escribir en payments.db │
         │                            │                                  │
         │  8. Mostrar resultado     │                                  │
         │◄──────────────────────────┤                                  │
         │                            │                                  │
         │  ¿Resultado?              │                                  │
         │                            │                                  │
    ┌────┴────┐                      │                                  │
    │         │                      │                                  │
    │  ✅     │                      │                                  │
    │APPROVED │                      │                                  │
    │         │                      │                                  │
    └─────────┘                      │                                  │
    ┌─────────┐                      │                                  │
    │         │                      │                                  │
    │  ⚠️     │──────────────────────►│  9. Escalar al auditor (A2A)   │
    │ESCALATED│                      │    Si monto >$500k o alto riesgo │
    │         │                      │                                  │
    └─────────┘                      │                                  │
    ┌─────────┐                      │                                  │
    │         │                      │                                  │
    │  ❌     │                      │                                  │
    │REJECTED │                      │                                  │
    │         │                      │                                  │
    └─────────┘                      │                                  │
```

### 4.2 Flujo B: Consulta de Estado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FLUJO B: CONSULTA DE ESTADO                              │
└─────────────────────────────────────────────────────────────────────────────┘

    PROVEEDOR                      SISTEMA                         DB
         │                            │                          │
         │  1. Consulta por chat      │                          │
         │     "¿Estado de mi         │                          │
         │      factura FC-001?"      │                          │
         ├──────────────────────────►│                          │
         │                            │                          │
         │                            │  2. Clasificar intención  │
         │                            ├──► router_agent ──────────┤
         │                            │     detection: "check_status" │
         │                            │                          │
         │                            │  3. Consultar DB        │
         │                            ├──────────────────────────►│
         │                            │     SELECT * FROM        │
         │                            │     payments WHERE       │
         │                            │     invoice_id = ?      │
         │                            │◄──────────────────────────┤
         │                            │     (resultado)          │
         │                            │                          │
         │  4. Mostrar estado        │                          │
         │     con detalle según      │                          │
         │     el estado actual       │                          │
         │◄──────────────────────────┤                          │
         │                            │                          │
         │  Ejemplo:                 │                          │
         │  ┌─────────────────┐     │                          │
         │  │ Estado: Aprobada │     │                          │
         │  │ Monto: $45.000  │     │                          │
         │  │ Comprobante:     │     │                          │
         │  │ PAY-A1B2C3D4     │     │                          │
         │  │ CBU: 017029...   │     │  ← Solo si PAID       │
         │  └─────────────────┘     │                          │
         │                            │                          │
```

### 4.3 Flujo C: Revisión de Factura Escalada

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                FLUJO C: REVISIÓN DE FACTURA ESCALADA                        │
└─────────────────────────────────────────────────────────────────────────────┘

    ADMIN                  SISTEMA              AUDITOR (A2A)
      │                        │                    │
      │  1. Ve factura        │                    │
      │     en historial       │                    │
      │◄───────────────────────┤                    │
      │                        │                    │
      │  2. Solicita          │                    │
      │     revisión           │                    │
      ├───────────────────────►│                    │
      │                        │                    │
      │                        │  3. Enviar a A2A   │
      │                        │    POST /audit     │
      │                        ├───────────────────►│
      │                        │                    │
      │                        │                    │  4. Evaluar factura
      │                        │                    │     • Monto elevado
      │                        │                    │     • Historial
      │                        │                    │     • Documentación
      │                        │                    │     • Contrato
      │                        │                    │     • Señales de alerta
      │                        │                    │
      │                        │                    │  5. Dictamen
      │                        │                    │     {
      │                        │◄───────────────────┤      "audit_result": "APPROVE",
      │                        │                    │      "confidence": 0.87,
      │                        │                    │      "findings": [...]
      │                        │                    │    }
      │                        │                    │
      │                        │  6. Actualizar    │
      │                        │     decisión en DB │
      │                        ├──────────────────►│
      │                        │                    │
      │  7. Mostrar          │                    │
      │     resultado al      │                    │
      │     proveedor         │                    │
      │◄───────────────────────┤                    │
      │                        │                    │
```

---

## 5. Casuísticas y Escenarios

### 5.1 Escenarios de Rechazo

| Escenario | Causa | Regla | Mensaje al Proveedor |
|-----------|-------|-------|---------------------|
| **E1: Archivo no PDF** | Proveedor sube imagen | VR-01 | "Formato de archivo no soportado, debe ser PDF" |
| **E2: Archivo muy grande** | PDF > 10MB | VR-02 | "Archivo demasiado grande (máximo 10 MB)" |
| **E3: Campos incompletos** | Falta CUIT o monto | VR-03 | "Campos obligatorios faltantes: [detalle]" |
| **E4: CUIT inválido** | Dígito verificador incorrecto | VR-04 | "CUIT con formato inválido" |
| **E5: Fecha futura** | Fecha > hoy | VR-05 | "Fecha de emisión inválida" |
| **E6: Monto negativo** | amount ≤ 0 | VR-06 | "Monto de factura inválido" |
| **E7: Factura duplicada** | Mismo invoice_id existe | VR-07 | "Factura duplicada" |
| **E8: Proveedor inexistente** | CUIT no registrado | BR-01 | "Proveedor no registrado" |
| **E9: Proveedor inactivo** | Status = INACTIVE | BR-02 | "Proveedor inactivo" |
| **E10: Factura vencida** | > 60 días desde emisión | BR-03 | "Factura vencida" |
| **E11: Razón social no coincide** | Nombre en factura ≠ contrato | BR-04 | "Razón social no coincide con el proveedor registrado" |
| **E12: Excede límite contractual** | monto > límite del contrato | BR-05 | "Monto excede el límite contractual" |

### 5.2 Escenarios de Escalado

| Escenario | Causa | Regla | Acción |
|-----------|-------|-------|--------|
| **E13: Sin contrato** | No existe contrato vigente | BR-06 | Escalar a revisión manual |
| **E14: Monto alto** | > $500.000 | BR-07 | Escalar a revisión humana |
| **E15: Alto riesgo ML** | Modelo clasifica como alto riesgo | BR-08 | Escalar a revisión humana |
| **E16: Posible fraccionamiento** | Múltiples facturas que suman >$500k | BR-09 | Escalar para verificar |

### 5.3 Escenarios de Seguridad

| Escenario | Causa | Regla | Acción |
|-----------|-------|-------|--------|
| **E17: Inyección de prompt** | Texto extraído contiene instrucciones | SR-01 | Rechazar con mensaje genérico |
| **E18: Acción no permitida** | Intenta modificar DB | SR-02 | Rechazar |
| **E19: Acceso cruzado** | Consulta datos de otro proveedor | SR-03 | Rechazar con "No autorizado" |
| **E20: Rate limit exceeded** | > 20 facturas/hora | SR-04 | Bloquear 1 hora |
| **E21: Info interna** | Pregunta sobre arquitectura | SR-05 | Redirigir |

### 5.4 Escenarios de Continuidad

| Escenario | Causa | Regla | Acción |
|-----------|-------|-------|--------|
| **E22: Servicio caído** | supplier-service no responde | CR-01 | Marcar PENDIENTE_TECNICO |
| **E23: Falla transitoria** | Timeout temporal | CR-02 | Reintentar 3 veces con backoff |
| **E24: Error técnico visible** | Exception en sistema | CR-03 | Mensaje amigable |

### 5.5 Casos de Prueba (Golden Cases)

| ID | Categoría | Descripción | Esperado |
|----|-----------|-------------|----------|
| TC-001 | happy_path | Factura válida, proveedor activo, dentro del límite | ✅ APPROVE |
| TC-002 | structural | Archivo JPG en vez de PDF | ❌ REJECT (VR-01) |
| TC-003 | structural | Archivo de 15MB | ❌ REJECT (VR-02) |
| TC-004 | structural | Campos obligatorios faltantes | ❌ REJECT (VR-03) |
| TC-005 | structural | CUIT con formato inválido | ❌ REJECT (VR-04) |
| TC-006 | structural | Fecha de emisión futura | ❌ REJECT (VR-05) |
| TC-007 | structural | Monto negativo | ❌ REJECT (VR-06) |
| TC-008 | business | Proveedor no registrado | ❌ REJECT (BR-01) |
| TC-009 | business | Proveedor inactivo | ❌ REJECT (BR-02) |
| TC-010 | business | Factura vencida (>60 días) | ❌ REJECT (BR-03) |
| TC-011 | business | Razón social no coincide | ❌ REJECT (BR-04) |
| TC-012 | business | Monto excede límite contractual | ❌ REJECT (BR-05) |
| TC-013 | business | Sin contrato vigente | ⚠️ ESCALATE (BR-06) |
| TC-014 | business | Monto > $500.000 | ⚠️ ESCALATE (BR-07) |
| TC-015 | business | Alto riesgo según ML | ⚠️ ESCALATE (BR-08) |
| TC-016 | business | Posible fraccionamiento | ⚠️ ESCALATE (BR-09) |
| TC-017 | business | Factura ya procesada | 🚫 BLOCK (BR-10) |
| TC-018 | security | Inyección de prompt | ❌ REJECT (SR-01) |
| TC-019 | security | Acceso a otro proveedor | ❌ REJECT (SR-03) |
| TC-020 | continuity | Servicio externo caído | ⏳ PENDIENTE_TECNICO (CR-01) |

---

## 6. Diagrama de Casos de Uso

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INVOICEFLOW                                         │
│                    Sistema de Aprobación                                     │
│                         de Facturas                                         │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   PROVEEDOR     │
                              └────────┬────────┘
                                       │
          ┌─────────────────────────────┼─────────────────────────────┐
          │                             │                             │
          │    ┌──────────────┐   ┌─────▼──────┐   ┌──────────────┐   │
          │    │  CU-P01      │   │  CU-P02    │   │  CU-P03      │   │
          │    │  Iniciar     │   │  Subir      │   │  Consultar   │   │
          │    │  Sesión      │   │  Factura    │   │  Estado      │   │
          │    └──────┬───────┘   └─────┬──────┘   └──────┬───────┘   │
          │           │                  │                  │           │
          │           │          ┌───────▼──────┐         │           │
          │           │          │  Flujo A      │         │           │
          │           │          │  (Alta)       │         │           │
          │           │          └───────┬───────┘         │           │
          │           │                  │                  │           │
          │           │          ┌───────▼──────┐         │           │
          │           │          │  Guardrails   │         │           │
          │           │          │  (26 reglas)  │         │           │
          │           │          └───────┬───────┘         │           │
          │           │                  │                  │           │
          │           │          ┌───────▼──────┐         │           │
          │           │          │  Aprobación   │         │           │
          │           │          │  Automática   │         │           │
          │           │          └───────┬───────┘         │           │
          │           │                  │                  │           │
          │           │          ┌───────▼──────┐         │           │
          │           │          │  Flujo B     │         │           │
          │           │          │  (Consulta)  │         │           │
          │           │          └──────────────┘         │           │
          │           │                                      │           │
          │    ┌──────▼───────┐                      ┌───────▼──────┐   │
          │    │  CU-P04      │                      │  CU-P05      │   │
          │    │  Chat de     │                      │  Cerrar     │   │
          │    │  Soporte     │                      │  Sesión     │   │
          │    └──────────────┘                      └─────────────┘   │
          │                                                             │
          │                        ┌─────────────────┐                 │
          │                        │  ADMINISTRADOR  │                 │
          │                        └────────┬────────┘                 │
          │                                 │                         │
          │    ┌───────────────────────────┼─────────────────────┐   │
          │    │                           │                         │   │
          │    │   ┌──────────┐    ┌──────▼──────┐    ┌──────────┐ │   │
          │    │   │ CU-B01   │    │  CU-B02     │    │ CU-B03   │ │   │
          │    │   │ Dashboard│    │  Gestionar  │    │ Historial│ │   │
          │    │   └──────────┘    │  Inbox      │    └──────────┘ │   │
          │    │                    └──────┬───────┘                 │   │
          │    │                           │                         │   │
          │    │   ┌──────────┐    ┌──────▼──────┐    ┌──────────┐ │   │
          │    │   │ CU-B05   │    │  CU-B04     │    │ CU-B06   │ │   │
          │    │   │Estado de │    │  Chat       │    │Evalua-   │ │   │
          │    │   │Agentes   │    │  Interno    │    │ción      │ │   │
          │    │   └──────────┘    └─────────────┘    └──────────┘ │   │
          │    │                                                       │   │
          │    │                        ┌──────────┐                  │   │
          │    │                        │ CU-B07    │                  │   │
          │    │                        │ Docs      │                  │   │
          │    │                        └──────────┘                  │   │
          │    │                                                       │   │
          └────┼─────────────────────────────────────────────────────┘   │
               │                                                         │
               │   ┌─────────────────────────────────────┐              │
               │   │           SISTEMA                    │              │
               │   │  (Procesos automáticos)             │              │
               │   └─────────────────────────────────────┘              │
               │                                                         │
          ┌────┼─────────────────────────────────────────────────────┐   │
          │    │                                                         │   │
          │    │   ┌──────────┐    ┌──────────┐    ┌──────────┐       │   │
          │    │   │ Validar  │    │ Control  │    │ Evaluar  │       │   │
          │    │   │Proveedor │    │Contrato  │    │  Riesgo  │       │   │
          │    │   │(VR+BR)   │    │  (RAG)   │    │   (ML)   │       │   │
          │    │   └──────────┘    └──────────┘    └──────────┘       │   │
          │    │                                                         │   │
          │    │   ┌──────────────────────────────────────────┐       │   │
          │    │   │  A2A: External Auditor Agent (Puerto 8003) │       │   │
          │    │   │  Revisión de facturas escaladas              │       │   │
          │    │   └──────────────────────────────────────────┘       │   │
          │    │                                                         │   │
          └────┼─────────────────────────────────────────────────────┘   │
               │                                                         │
               └─────────────────────────────────────────────────────────┘
```

---

## Anexo: Endpoints de API

### Backend (Puerto 8000)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check con estado de servicios |
| GET | `/` | Página principal del Back Office |
| GET | `/supplier/` | Portal del Proveedor |
| GET | `/inbox` | Lista de facturas en inbox |
| POST | `/inbox/upload` | Subir factura al inbox |
| POST | `/inbox/process/{filename}` | Procesar una factura |
| POST | `/inbox/process-all` | Procesar todas |
| POST | `/invoices` | Submitir factura directamente |
| GET | `/invoices` | Listar facturas procesadas |
| GET | `/dashboard` | Estadísticas del dashboard |
| POST | `/chat` | Chat-driven processing |

### Supplier Service (Puerto 8001)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/suppliers` | Listar todos los proveedores |
| GET | `/suppliers/{id}` | Obtener proveedor por ID |
| POST | `/suppliers` | Crear proveedor |
| PUT | `/suppliers/{id}/status` | Actualizar estado |

### Contract Service (Puerto 8002)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/contracts` | Listar contratos |
| POST | `/contracts/upload` | Subir contrato |
| GET | `/contracts/{supplier_id}/check` | Verificar límite contractual |

---

**Documento creado**: 2025
**Versión**: 1.0.0
**Proyecto**: InvoiceFlow — TP Sistemas Multiagentes (UP)
