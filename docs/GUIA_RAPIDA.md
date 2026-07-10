# InvoiceFlow — Guía Rápida

> Referencia rápida para iniciar el sistema en minutos.

---

## 🚀 Inicio Rápido

### 1. Clonar o Descargar

```bash
git clone https://github.com/gisellefernandezv-ops/multiagentes_clinicaparque.git
cd invoice_approval_system
```

### 2. Instalar Dependencias

```bash
# Crear entorno virtual
python -m venv .venv

# Activar
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # Linux/macOS

# Instalar
pip install -r requirements.txt
```

### 3. Configurar

```bash
cp .env.example .env
# Editar .env y agregar: GOOGLE_API_KEY=tu_api_key
```

### 4. Iniciar (3 terminales)

```bash
# Terminal 1 - Supplier Service
python -m platform.services.supplier_service.main

# Terminal 2 - Contract Service  
python -m platform.services.contract_service.main

# Terminal 3 - Backend
cd platform/backend && python main.py
```

---

## 🌐 URLs del Sistema

| Servicio | URL |
|----------|-----|
| **Back Office** | http://localhost:8000/ |
| **Supplier Portal** | http://localhost:8000/supplier/ |
| **API Backend** | http://localhost:8000/docs |
| **API Supplier** | http://localhost:8001/docs |
| **API Contract** | http://localhost:8002/docs |

---

## 🔑 Login de Prueba

Usar estos IDs de proveedor:

| ID | Nombre | Estado |
|----|--------|--------|
| SUP001 | TechCorp SA | ACTIVE |
| SUP002 | Papeleria Norte SRL | ACTIVE |
| SUP003 | Servicios Rapidos SA | INACTIVE |
| SUP004 | Limpieza Total SRL | ACTIVE |
| SUP005 | Consultoria Digital SA | ACTIVE |

---

## 📋 Ejemplo de Factura (JSON)

```json
{
  "invoice_id": "INV-001",
  "supplier_id": "SUP001",
  "supplier_name": "TechCorp SA",
  "amount": 50000,
  "currency": "ARS",
  "invoice_date": "2025-06-01"
}
```

### Decisiones Posibles

| Decisión | Significado |
|----------|-------------|
| `APPROVED` | Factura validada, lista para pago |
| `REJECTED` | Factura rechazada (ver motivo) |
| `ESCALATED` | Requiere revisión humana |

---

## 🔧 Comandos Útiles

### Health Check
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Verificar Componentes
```bash
python -m guardrails.invoice_guardrail
python -m evaluation.metrics
```

### Detener Servicios
```bash
# Windows
taskkill /F /IM python.exe

# Linux/macOS
pkill -f "python.*platform"
```

---

## ❓ Solución Rápida de Problemas

| Error | Solución |
|-------|----------|
| `python not found` | Reinstalar Python marcando "Add to PATH" |
| `Port in use` | `netstat -ano \| findstr :8000` → matar proceso |
| `Module not found` | Activar entorno virtual (`.venv\Scripts\activate`) |
| `Dependencias faltantes` | `pip install -r requirements.txt` |

---

## 📚 Documentación Completa

| Archivo | Descripción |
|---------|-------------|
| [README.md](../README.md) | Descripción general y arquitectura |
| [CHANGELOG.md](../CHANGELOG.md) | Historial de cambios |
| [INSTALL.md](../INSTALL.md) | Guía de instalación detallada |
| [especificacion_sistema_invoiceflow.md](./especificacion_sistema_invoiceflow.md) | Especificación técnica |
| [documento_guardrails_invoiceflow.md](./documento_guardrails_invoiceflow.md) | Sistema de guardrails |

---

## 📞 Guías por Sistema Operativo

- [Windows](INSTALACION_WINDOWS.md) — Instalación paso a paso
- [Linux](INSTALACION_LINUX.md) — Instalación paso a paso
- [macOS](INSTALACION_MACOS.md) — Instalación paso a paso

---

**Versión**: 1.0.0 | **Última actualización**: 2025-06-20
