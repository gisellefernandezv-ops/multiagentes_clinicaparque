# Especificación de Sistema — InvoiceFlow

Documento técnico completo: tecnología, estructura, arquitectura y pantallas de las dos interfaces del sistema (Portal del Proveedor y Back Office).

---

## 1. Tecnología

| Capa | Tecnología |
|---|---|
| Framework de agentes | Google ADK (Agent Development Kit) |
| Modelo de lenguaje | Gemini 2.5 Flash |
| Backend / API | FastAPI (Python 3.12) |
| Base de datos relacional | SQLite (`payments.db`) |
| Base vectorial (RAG) | ChromaDB |
| Motor de guardrails | Reglas declaradas en YAML + motor propio en Python |
| Evaluación | Google ADK Eval (`agents-cli eval generate` / `agents-cli eval grade`) |
| Modelo de riesgo (ML) | scikit-learn (regresión logística o árbol de decisión) |
| Protocolo A2A | Comunicación entre proyectos ADK independientes vía A2A |
| Frontend | HTML + CSS + JavaScript (sin framework), servido por FastAPI |
| Entorno de desarrollo | Open Code (IDE) + MiniMax como asistente de código |

---

## 2. Estructura de carpetas

```
invoice_approval_system/
├── agent.py
├── agents/
│   ├── orchestrator.py
│   ├── router_agent.py                 # nuevo: clasifica intención (canal chat)
│   ├── validator_agent.py
│   ├── contract_agent.py               # ampliado: 3 validaciones
│   ├── payment_agent.py
│   └── invoice_manager_agent.py
├── tools/
│   ├── supplier_mcp_tool.py
│   ├── payment_db_tool.py
│   ├── rag_tool.py
│   ├── folder_manager_tool.py
│   ├── pdf_extractor_tool.py
│   ├── invoice_status_tool.py          # nuevo: Flujo B (consulta de estado)
│   └── ml_risk_tool.py                 # nuevo: inferencia de riesgo
├── guardrails/
│   ├── rules.yaml                      # nuevo: templates de guardrail
│   └── guardrail_engine.py             # nuevo: motor que lee rules.yaml
├── ml/
│   └── risk_model.pkl                  # nuevo: modelo entrenado
├── a2a/
│   └── external_auditor_agent/         # nuevo: proyecto ADK independiente (simula otra organización)
├── tests/
│   └── eval/
│       ├── datasets/invoiceflow-dataset.json   # nuevo: golden cases
│       └── eval_config.yaml                     # nuevo: métricas a usar
├── data/
│   ├── payments.db
│   ├── chroma_db/
│   ├── contracts/
│   └── new invoices/
├── platform/
│   ├── backend/
│   │   ├── main.py
│   │   ├── supplier_portal_router.py
│   │   ├── new_invoices_router.py
│   │   └── inbox_router.py
│   └── frontend/                       # Back Office
│       ├── index.html
│       ├── app.js
│       └── style.css
└── supplier_portal/                    # Portal del Proveedor
    ├── index.html
    ├── app.js
    └── style.css
```

---

## 3. Arquitectura (resumen)

**Agentes:**

| Agente | Rol |
|---|---|
| `invoice_orchestrator` | Coordina todo, rutea según intent |
| `router_agent` | Clasifica intención solo en el canal chat |
| `validator_agent` | Identifica y valida proveedor |
| `contract_agent` | Valida vencimiento, razón social y monto contra contrato/adenda (RAG) |
| `payment_agent` | Registra resultado, responde sobre pagos |
| `invoice_manager_agent` | Extrae datos de factura, gestiona archivos |
| `external_auditor_agent` (A2A) | Agente externo simulado que audita facturas escaladas |

**Flujo de datos:** viaja por `state` entre agentes (ver `prompt_implementacion_invoiceflow_iteracion1.md` sección 7 para el detalle de claves).

**Flujos de negocio:** Flujo A (alta de factura) y Flujo B (consulta de estado) — detalle completo en `diseno_funcional_invoiceflow.md`.

---

## 4. Pantallas — Portal del Proveedor

### Header (global, en todas las pantallas autenticadas)
- Logo + "InvoiceFlow — Portal Proveedor"
- Razón social del proveedor logueado
- Botón "Cerrar sesión"

### Sidebar (navegación lateral)
- Inicio
- Subir factura
- Mis facturas
- Chat de soporte

### Footer (global)
- Datos de contacto de administración/cuentas a pagar
- Versión del sistema

### Pantallas

**4.1 Login**
- Sin sidebar (previo a autenticación).
- Campo único: CUIT, nombre o ID de proveedor.
- Funcionalidad: valida contra `validator_agent` → si existe y está activo, entra a Inicio; si no, mensaje de error.

**4.2 Inicio (Dashboard proveedor)**
- Resumen de facturas propias por estado: 5 badges de color (Pendiente / Aprobada / Escalada / Rechazada / Pagada) con cantidad de cada una.
- Accesos rápidos: botón "Subir factura", botón "Consultar estado".

**4.3 Subir factura**
- Formulario con carga de archivo PDF (drag & drop o selector).
- Al enviar, dispara el **Flujo A** completo.
- Muestra el resultado inmediato: aprobada / escalada / rechazada (con motivo puntual).

**4.4 Mis facturas (Historial)**
- Listado de todas las facturas propias.
- Filtro por año, mes y estado.
- Click en una fila expande el detalle:
  - Si Rechazada → motivo puntual.
  - Si Pagada → CBU, fecha de pago, N° de comprobante.
  - Si Escalada → "en revisión" (y, si ya corrió A2A, el resultado del dictamen del auditor externo).

**4.5 Chat de soporte**
- Conversación libre con `router_agent` → deriva a `new_invoice`, `check_status` o responde `chitchat` directo.
- Accesible desde el sidebar o como ícono flotante en cualquier pantalla.

### Navegación
```
Login → Inicio → Subir factura ─┐
              → Mis facturas ───┤→ vuelven a Inicio vía sidebar
              → Chat de soporte ┘
```

---

## 5. Pantallas — Back Office

### Header (global)
- Logo "InvoiceFlow" + versión del producto
- Indicador resumido de estado de agentes (ej. "🔴 2 servicios caídos") con link directo a la pantalla de Observabilidad
- Usuario del operador + "Cerrar sesión"

### Sidebar (reemplaza las tabs actuales — se justifica porque ahora hay más secciones que antes)
- Dashboard
- Inbox
- Historial
- Chat interno
- Estado de Agentes (Observabilidad)
- Evaluación (resultados de LLM-as-a-Judge / Golden Cases)
- Docs

### Footer (global)
- Versión, ambiente (dev/prod), link a documentación técnica del proyecto

### Pantallas

**5.1 Dashboard**
- Tarjetas de los 5 estados + Total aprobado + Total pagado (detalle completo en `especificacion_backoffice_invoiceflow.md` sección 2).
- Filtro por año/mes.
- Tabla "Últimos pagos procesados" con columna Comprobante.

**5.2 Inbox**
- Facturas nuevas sin procesar (`data/new invoices/`).
- Botón "Agrupar facturas" (ejecuta `invoice_manager_agent`).
- Botón "Ver facturas" (abre el detalle de lo pendiente).

**5.3 Historial**
- Listado completo, filtrable por proveedor / año / mes / estado.
- Detalle expandible (mismo criterio que 4.4 del portal proveedor, pero con visión interna completa).

**5.4 Chat interno**
- Canal para que el equipo de administración procese facturas conversacionalmente con ayuda de IA.
- Distinto del chat de soporte del proveedor — aclarar con etiqueta visible.

**5.5 Estado de Agentes (Observabilidad)**
- Panel por agente/servicio: estado, última ejecución, invocaciones 24h, tasa de error (detalle completo en `especificacion_backoffice_invoiceflow.md` sección 3).

**5.6 Evaluación**
- Muestra los resultados de la última corrida de `agents-cli eval grade`: qué casos pasaron, qué métricas dieron, para tener la evidencia a mano en la defensa oral sin tener que ir a la terminal.

**5.7 Docs**
- Documentación técnica existente del proyecto (README, este documento, los demás `.md` generados).

### Navegación
```
Dashboard ←→ Inbox ←→ Historial ←→ Chat interno ←→ Estado de Agentes ←→ Evaluación ←→ Docs
   (todas accesibles desde el sidebar, sin jerarquía — navegación plana típica de panel administrativo)
```

---

## 6. Notas de implementación

- Todo lo de este documento es una **formalización** de lo ya existente + las mejoras acordadas — no implica reescribir el portal o el back office desde cero. Misma regla de resguardo que en las iteraciones anteriores: backup antes de tocar código, cambios aditivos.
- El paso de tabs a sidebar en el Back Office es un cambio de layout, no de lógica — puede hacerse sin tocar ninguno de los endpoints existentes.
- Las pantallas nuevas (Evaluación, Estado de Agentes) dependen de que existan los datos que muestran — no tiene sentido construirlas antes de tener la evaluación LLM-as-a-Judge y el motor de guardrails funcionando.
