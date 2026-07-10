# SPECS 007 — Frontend

> **Proyecto**: InvoiceFlow  
> **Tipo**: Especificación de Interfaces  
> **Estado**: ✅ Implementado

---

## 1. Interfaces del Sistema

| Interface | Ubicación | Propósito |
|-----------|-----------|----------|
| **Supplier Portal** | `supplier_portal/` | Portal para proveedores |
| **Back Office** | `app/frontend/` | Panel de administración |

---

## 2. Supplier Portal

### 2.1 Estructura de Archivos

```
supplier_portal/
├── index.html      # Página principal
├── style.css       # Estilos
└── app.js          # Lógica JavaScript
```

### 2.2 Páginas

#### Login
- Campo: CUIT / Nombre / ID de Proveedor
- Validación contra backend
- Mensaje de error si no existe o está inactivo

#### Inicio (Dashboard)
- 5 badges de estado con contadores:
  - Pendiente (⏳)
  - Aprobada (✅)
  - Escalada (⚠️)
  - Rechazada (❌)
  - Pagada (💰)
- Botones de acceso rápido

#### Subir Factura
- Drag & drop para PDF
- Preview de datos extraídos
- Confirmación de envío

#### Mis Facturas (Historial)
- Filtros: año, mes, estado
- Tabla con datos de facturas
- Modal de detalle expandible

#### Chat de Soporte
- Conversación con RouterAgent
- Ícono flotante accesible desde cualquier página

### 2.3 Navegación

```
Login ──┬──> Inicio ──┬──> Subir Factura
        │             ├──> Mis Facturas
        │             └──> Chat
        │
        └──> (Error: proveedor no encontrado/inactivo)
```

### 2.4 API Consumida

| Endpoint | Método | Uso |
|----------|--------|-----|
| `/supplier/validate` | POST | Login |
| `/supplier/invoices/{id}` | GET | Historial |
| `/invoices` | POST | Procesar factura |
| `/dashboard` | GET | Estadísticas |

---

## 3. Back Office

### 3.1 Estructura de Archivos

```
app/frontend/
├── index.html      # Página principal
├── style.css       # Estilos
├── app.js          # Lógica JavaScript
└── InvoiceApprovalSystem.jsx  # Componentes React (?)
```

### 3.2 Páginas

#### Dashboard
- Tarjetas de resumen por estado
- Totales de aprobadas y pagadas
- Filtro por año/mes
- Tabla de últimos pagos

#### Inbox
- Facturas pendientes de procesar
- Botón "Procesar todas"
- Preview de contenido

#### Historial
- Todas las facturas procesadas
- Filtros avanzados
- Exportación (futuro)

#### Chat Interno
- Canal de comunicación del equipo
- Integración con agentes IA

#### Estado de Agentes (Observabilidad)
- Estado de cada servicio
- Métricas de uso
- Errores recientes

#### Evaluación
- Resultados de golden cases
- Métricas de calidad
- Historial de ejecuciones

#### Docs
- Documentación técnica
- Enlaces a specs

### 3.3 Navegación

```
Sidebar
├── Dashboard
├── Inbox
├── Historial
├── Chat interno
├── Estado de Agentes
├── Evaluación
└── Docs
```

---

## 4. Diseño Visual

### 4.1 Paleta de Colores

| Propósito | Color | Uso |
|-----------|-------|-----|
| Primario | `#2563eb` | Botones, links |
| Secundario | `#64748b` | Texto secundario |
| Success | `#10b981` | Estados aprobados |
| Warning | `#f59e0b` | Estados pendientes |
| Danger | `#ef4444` | Estados rechazados |
| Background | `#f8fafc` | Fondo general |
| Card | `#ffffff` | Tarjetas |

### 4.2 Tipografía

| Elemento | Fuente | Tamaño |
|----------|--------|--------|
| H1 | System UI | 24px |
| H2 | System UI | 20px |
| Body | System UI | 14px |
| Small | System UI | 12px |

### 4.3 Badges de Estado

| Estado | Color | Icono |
|--------|-------|-------|
| PENDING | `#f59e0b` (warning) | ⏳ |
| APPROVED | `#10b981` (success) | ✅ |
| REJECTED | `#ef4444` (danger) | ❌ |
| ESCALATED | `#f59e0b` (warning) | ⚠️ |
| PAID | `#10b981` (success) | 💰 |

---

## 5. Responsive Design

### 5.1 Breakpoints

| Breakpoint | Ancho | Disposición |
|------------|-------|-------------|
| Mobile | < 768px | Columna única |
| Tablet | 768px - 1024px | Sidebar colapsable |
| Desktop | > 1024px | Sidebar visible |

### 5.2 Sidebar

- **Desktop**: Visible, 250px de ancho
- **Tablet/Mobile**: Oculto, toggler para mostrar

---

## 6. Estructura HTML Común

### 6.1 Header (Global)

```html
<header class="app-header">
    <div class="header-brand">
        <span class="header-logo">🏢</span>
        <h1>InvoiceFlow</h1>
    </div>
    <div class="header-user">
        <span>Usuario</span>
        <button>Cerrar sesión</button>
    </div>
</header>
```

### 6.2 Sidebar

```html
<nav class="sidebar">
    <ul class="sidebar-nav">
        <li class="sidebar-item active">
            <span class="icon">🏠</span>
            <span class="text">Inicio</span>
        </li>
        <!-- más items -->
    </ul>
</nav>
```

### 6.3 Main Content

```html
<main class="main-content">
    <div class="page active" id="page-inicio">
        <h2>Título de página</h2>
        <!-- contenido -->
    </div>
</main>
```

---

## 7. Rutas del Frontend

| URL | Página | Componente |
|-----|--------|------------|
| `/` | Back Office | index.html |
| `/supplier/` | Supplier Portal | index.html |
| `/supplier/portal` | Portal (API) | supplier_portal_router.py |

---

## 8. Referencias

| Documento | Descripción |
|-----------|-------------|
| `supplier_portal/index.html` | Portal del proveedor |
| `app/frontend/index.html` | Back Office |
| `SPECS_006_BACKEND.md` | API que consume el frontend |

---

**Versión**: 2.0.0  
**Última actualización**: 2026-07-15
