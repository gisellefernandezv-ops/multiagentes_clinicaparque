# SPECS OBS — Observabilidad y Health Check

> **Proyecto**: InvoiceFlow  
> **Tipo**: Especificación de Observabilidad Completa
> **Estado**: ✅ Implementado y Ampliado
> **Versión**: 3.0.0

---

## 1. Concepto de Observabilidad

La observabilidad en InvoiceFlow es un sistema integral que proporciona visibilidad completa sobre todos los componentes del sistema, permitiendo monitoreo en tiempo real, diagnóstico de problemas y tracking de métricas.

### Pilares de la Observabilidad

| Pilar | Descripción | Componentes |
|-------|-------------|-------------|
| **Disponibilidad** | Estado de todos los servicios | Health checks de servicios |
| **Rendimiento** | Métricas de respuesta y throughput | Response times, timeouts |
| **Integridad** | Estado de datos y sistemas de almacenamiento | DBs, archivos, índices |
| **Integraciones** | Conectividad entre componentes | MCP, RAG, A2A |
| **Logs** | Auditoría y debugging | Tracking de eventos |
| **Agentes** | Estado de los agentes IA | Router, Validator, etc. |

---

## 2. Arquitectura de Observabilidad

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           DASHBOARD / FRONTEND                               │
│                    http://127.0.0.1:8000 (BackOffice)                        │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │ Polling / WebSocket
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     BACKEND (Puerto 8000) - API Principal                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    /health/observability                                 │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │ │
│  │  │ Services │  │Databases │  │   MCP    │  │   RAG    │  │   Logs   │  │ │
│  │  │ Checker  │  │ Checker  │  │ Checker  │  │ Checker  │  │ Tracker  │  │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │ │
│  └───────┼─────────────┼─────────────┼─────────────┼─────────────┼───────┘ │
└──────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────┘
           │             │             │             │             │
           ▼             ▼             ▼             ▼             ▼
┌─────────────────┐ ┌─────────┐ ┌───────────┐ ┌─────────┐ ┌───────────────┐
│    Services     │ │Databases│ │    MCP    │ │   RAG   │ │     Logs       │
├─────────────────┤ ├─────────┤ ├───────────┤ ├─────────┤ ├───────────────┤
│ • Backend:8000  │ │suppliers│ │  Toolbox  │ │ChromaDB │ │invoiceflow.log │
│ • Supplier:8001 │ │payments │ │ :5000     │ │collections│ │               │
│ • Contract:8002 │ │chat_ses │ │  tools.yaml│ │documents │ │               │
│ • Auditor:8003  │ │inbox    │ │  servers.json│ │         │ │               │
└─────────────────┘ └─────────┘ └───────────┘ └─────────┘ └───────────────┘
```

---

## 3. Endpoints de Observabilidad

### 3.1 Health Check Básico

```bash
GET /health
```

**Respuesta**:
```json
{
  "service": "invoiceflow-backend",
  "status": "ok",
  "version": "1.0.0",
  "watcher_enabled": true,
  "microservices": {
    "supplier-service": {"status": "ok"},
    "contract-service": {"status": "ok"}
  },
  "paths": {
    "inbox": "app/data/inbox",
    "processed": "app/data/processed",
    "rejected": "app/data/rejected"
  }
}
```

### 3.2 Health Check de Agentes (Proxy)

```bash
GET /agents/health
```

**Respuesta**:
```json
{
  "status": "ok",
  "all_services_ok": true,
  "critical_services": {
    "invoiceflow-backend": {"ok": true, "status": "up", "url": "..."},
    "supplier-service": {"ok": true, "status": "up", "url": "..."},
    "contract-service": {"ok": true, "status": "up", "url": "..."}
  },
  "secondary_services": {
    "external-auditor": {"ok": false, "status": "down", "url": "..."}
  }
}
```

### 3.3 Observabilidad Completa (V3.0.0)

```bash
GET /health/observability
```

**Respuesta Completa**:
```json
{
  "status": "healthy|degraded|unhealthy",
  "health_score": 95.5,
  "timestamp": "2026-07-13T22:30:00.123456",
  "version": "3.0.0",
  
  "services": {
    "services": {
      "backend": {
        "url": "http://127.0.0.1:8000/health",
        "type": "critical",
        "status": {
          "ok": true,
          "status": "up",
          "details": {...},
          "response_time_ms": 12.5
        }
      },
      "supplier_service": {
        "url": "http://127.0.0.1:8001/health",
        "type": "critical",
        "status": {"ok": true, "status": "up"}
      },
      "contract_service": {
        "url": "http://127.0.0.1:8002/health",
        "type": "critical",
        "status": {"ok": true, "status": "up"}
      },
      "mcp_toolbox": {
        "url": "http://127.0.0.1:5000/health",
        "type": "secondary",
        "status": {"ok": false, "status": "not_running"}
      },
      "external_auditor_a2a": {
        "url": "http://127.0.0.1:8003/health",
        "type": "secondary",
        "status": {"ok": false, "status": "not_running"}
      }
    },
    "metrics": {
      "total": 5,
      "up": 3,
      "down": 2,
      "all_critical_healthy": true,
      "all_services_healthy": false
    }
  },
  
  "databases": {
    "databases": {
      "suppliers_db": {
        "ok": true,
        "status": "ok",
        "path": "app/data/suppliers.db",
        "tables": ["suppliers", "contracts"],
        "table_count": 2,
        "counts": {"suppliers": 11, "contracts": 5},
        "total_rows": 16,
        "index_count": 3,
        "size_bytes": 36864,
        "size_human": "36.0 KB",
        "integrity": "ok"
      },
      "payments_db": {...},
      "chat_sessions_db": {...},
      "inbox_db": {...}
    },
    "metrics": {
      "total": 4,
      "ok": 4,
      "failed": 0,
      "all_healthy": true
    }
  },
  
  "integrations": {
    "mcp": {
      "mcp_toolbox": {
        "ok": true,
        "status": "not_running",
        "config_exists": true,
        "config_path": "mcp_config/tools.yaml",
        "servers_config_exists": true,
        "servers_config_path": "mcp_config/mcp_servers.json",
        "configured_tools": [
          {"name": "get_supplier_status", "description": "Obtiene el estado..."},
          {"name": "check_supplier_active", "description": "Verifica si..."},
          ...
        ],
        "tools_count": 5,
        "mcp_servers": [
          {"name": "invoiceflow-toolbox", "command": "python", "cwd": "..."}
        ],
        "servers_count": 1,
        "start_command": "python -m app.services.toolbox_server.main"
      },
      "integration_summary": {
        "server_available": false,
        "tools_configured": 5,
        "servers_configured": 1,
        "configuration_valid": true
      }
    },
    "rag": {
      "primary_rag": {
        "ok": true,
        "status": "ready",
        "path": "app/data/chroma_db",
        "collections_count": 2,
        "collections": [
          {"id": "uuid-1", "name": "contracts"},
          {"id": "uuid-2", "name": "invoices"}
        ],
        "total_documents": 150,
        "size_bytes": 560000,
        "initialized": true
      },
      "backup_rag": {...},
      "integration_status": {
        "primary_available": true,
        "backup_available": true,
        "documents_indexed": 150
      }
    },
    "a2a": {
      "external_auditor": {
        "url": "http://127.0.0.1:8003/health",
        "status": {"ok": false, "status": "down"}
      },
      "a2a_directory": {
        "exists": true,
        "path": "a2a",
        "agents_found": ["external_auditor_agent"],
        "agent_count": 1
      },
      "integration_status": {
        "auditor_available": false,
        "protocol_active": true
      }
    }
  },
  
  "files": {
    "paths": {
      "inbox": {
        "ok": true,
        "path": "app/data/inbox",
        "file_count": 3,
        "size_bytes": 150000,
        "size_human": "146.5 KB",
        "by_extension": {
          ".pdf": {"count": 2, "size_bytes": 100000, "avg_size_bytes": 50000},
          ".txt": {"count": 1, "size_bytes": 50000, "avg_size_bytes": 50000}
        },
        "recent_files": [...]
      },
      "processed": {...},
      "rejected": {...},
      "new_invoices": {...},
      "contracts": {...}
    },
    "watcher_enabled": true,
    "watched_directory": "app/data/inbox",
    "metrics": {
      "total_files": 55,
      "total_size_bytes": 2750000,
      "total_size_human": "2.6 MB",
      "paths_monitored": 5
    }
  },
  
  "logs": {
    "recent": {
      "ok": true,
      "path": "data/logs/invoiceflow.log",
      "total_lines": 1250,
      "recent_lines": 100,
      "entries": [
        {"level": "INFO", "message": "[2026-07-13 22:30:00] INFO: System started"},
        {"level": "WARNING", "message": "[2026-07-13 22:31:00] WARNING: Slow query detected"}
      ],
      "level_counts": {"INFO": 80, "WARNING": 15, "ERROR": 5, "DEBUG": 0},
      "log_span": {
        "first_entry": "2026-07-13 22:30:00",
        "last_entry": "2026-07-13 23:00:00",
        "duration_seconds": 1800,
        "duration_human": "30.0 minutes",
        "entries_per_minute": 0.7
      },
      "file_size_bytes": 256000,
      "file_size_human": "250.0 KB"
    },
    "errors": {
      "ok": true,
      "level": "ERROR",
      "count": 5,
      "entries": ["[2026-07-13 22:35:00] ERROR: Connection timeout..."]
    },
    "warnings": {...},
    "metrics": {
      "log_file_exists": true,
      "total_errors": 5,
      "total_warnings": 15,
      "has_critical_issues": true
    }
  },
  
  "agents": {
    "ok": true,
    "agents": {
      "router_agent": {"exists": true, "status": "available"},
      "validator_agent": {"exists": true, "status": "available"},
      "orchestrator": {"exists": true, "status": "available"},
      "contract_agent": {"exists": true, "status": "available"},
      "payment_agent": {"exists": true, "status": "available"},
      "invoice_manager_agent": {"exists": true, "status": "available"}
    },
    "metrics": {
      "total": 6,
      "available": 6,
      "all_loaded": true
    }
  },
  
  "summary": {
    "services_up": 3,
    "services_total": 5,
    "services_critical_healthy": true,
    "databases_ok": 4,
    "databases_total": 4,
    "databases_all_healthy": true,
    "mcp_tools_configured": 5,
    "mcp_server_running": false,
    "rag_documents_indexed": 150,
    "rag_primary_available": true,
    "inbox_count": 3,
    "processed_count": 42,
    "rejected_count": 5,
    "log_entries_available": true,
    "recent_log_lines": 100,
    "total_errors": 5,
    "total_warnings": 15,
    "a2a_agents_count": 1,
    "auditor_available": false
  },
  
  "issues": [
    "MCP Toolbox server not running",
    "External Auditor not available"
  ],
  "issues_count": 2
}
```

### 3.4 Logs Recientes

```bash
GET /logs/recent?lines=100
```

---

## 4. Servicios Monitoreados

### 4.1 Servicios Críticos (Requeridos)

| Servicio | Puerto | Tipo | Descripción | Peso Health |
|----------|--------|------|-------------|-------------|
| Backend | 8000 | critical | API principal + UI | 100% |
| Supplier Service | 8001 | critical | Gestión de proveedores | 100% |
| Contract Service | 8002 | critical | Gestión de contratos + RAG | 100% |

### 4.2 Servicios Secundarios (Opcionales)

| Servicio | Puerto | Tipo | Descripción | Impacto |
|----------|--------|------|-------------|---------|
| MCP Toolbox | 5000 | secondary | Herramientas MCP | 10% |
| External Auditor A2A | 8003 | secondary | Auditoría A2A | 0% |

---

## 5. Bases de Datos Monitoreadas

| Database | Ubicación | Tablas | Propósito | Integridad |
|----------|-----------|--------|-----------|------------|
| suppliers.db | app/data/ | suppliers, contracts | Registro de proveedores y contratos | ✅ Check |
| payments.db | data/ | payments | Historial de pagos | ✅ Check |
| chat_sessions.db | data/ | sessions | Sesiones de chat IA | ✅ Check |
| inbox.db | data/ | inbox | Tracking de facturas | ✅ Check |

### 5.1 Métricas de Base de Datos

```python
{
    "tables": ["suppliers", "contracts"],
    "table_count": 2,
    "counts": {"suppliers": 11, "contracts": 5},
    "total_rows": 16,
    "index_count": 3,
    "size_bytes": 36864,
    "integrity": "ok"
}
```

---

## 6. Integraciones MCP

### 6.1 MCP Toolbox Server

```yaml
# mcp_config/tools.yaml
tools:
  - name: "get_supplier_status"
    query: "SELECT ... FROM suppliers WHERE ..."
  - name: "check_supplier_active"
  - name: "get_supplier_by_cuit"
  - name: "list_active_suppliers"
  - name: "check_supplier_contract"
```

### 6.2 MCP Servers Configuration

```json
# mcp_config/mcp_servers.json
{
  "mcpServers": {
    "invoiceflow-toolbox": {
      "command": "python",
      "args": ["-m", "app.services.toolbox_server.main"],
      "cwd": "invoice_approval_system"
    }
  }
}
```

### 6.3 Estados de MCP Toolbox

| Estado | Significado | Acción |
|--------|-------------|--------|
| `running` | Servidor activo y respondiendo | Listo para usar |
| `not_running` | Servidor no iniciado | `python -m app.services.toolbox_server.main` |

---

## 7. RAG / ChromaDB Integration

### 7.1 Índices Monitoreados

| Índice | Ubicación | Propósito |
|--------|-----------|-----------|
| Primary | app/data/chroma_db/ | Embeddings principales |
| Backup | data/chroma_db/ | Backup de embeddings |

### 7.2 Métricas RAG

```json
{
  "collections_count": 2,
  "collections": [
    {"name": "contracts", "id": "uuid-1"},
    {"name": "invoices", "id": "uuid-2"}
  ],
  "total_documents": 150
}
```

---

## 8. Sistema de Logs

### 8.1 Ubicación

```
invoice_approval_system/
└── data/
    └── logs/
        └── invoiceflow.log
```

### 8.2 Formato de Entradas

```
[TIMESTAMP] LEVEL: MESSAGE

Ejemplos:
[2026-07-13 22:30:00] INFO: InvoiceFlow backend started on port 8000
[2026-07-13 22:31:00] WARNING: Invoice rejected - amount exceeds limit
[2026-07-13 22:32:00] ERROR: Failed to connect to supplier service
[2026-07-13 22:33:00] DEBUG: Processing invoice INV-001
```

### 8.3 Niveles de Log

| Nivel | Color | Uso | Frecuencia Esperada |
|-------|-------|-----|---------------------|
| INFO | Verde | Eventos normales | Alta |
| WARNING | Amarillo | Situaciones inesperadas | Baja |
| ERROR | Rojo | Fallos que requieren atención | Muy Baja |
| DEBUG | Gris | Información de debugging | Variable |

### 8.4 Tracking de Logs Mejorado

```json
{
  "level_counts": {
    "INFO": 80,
    "WARNING": 15,
    "ERROR": 5,
    "DEBUG": 0
  },
  "log_span": {
    "first_entry": "2026-07-13 22:30:00",
    "last_entry": "2026-07-13 23:00:00",
    "duration_seconds": 1800,
    "entries_per_minute": 0.7
  }
}
```

---

## 9. Estados de Salud

### 9.1 Cálculo del Health Score

```
Health Score = 100
  - 40% si servicios críticos no están healthy
  - 30% si bases de datos no están healthy
  - 15% si hay errores en logs
  - 10% si MCP Toolbox no está configurado o corriendo
  - 5% si RAG no está disponible
```

### 9.2 Estados

| Estado | Health Score | Significado |
|--------|--------------|-------------|
| **healthy** | ≥ 95 | Todos los componentes críticos operativos |
| **degraded** | ≥ 70 | Algunos componentes no críticos no disponibles |
| **unhealthy** | < 70 | Componentes críticos no disponibles |

---

## 10. Agentes IA

### 10.1 Agentes Monitoreados

| Agente | Archivo | Estado |
|--------|---------|--------|
| Router Agent | router_agent.py | ✅ Disponible |
| Validator Agent | validator_agent.py | ✅ Disponible |
| Orchestrator Agent | orchestrator.py | ✅ Disponible |
| Contract Agent | contract_agent.py | ✅ Disponible |
| Payment Agent | payment_agent.py | ✅ Disponible |
| Invoice Manager Agent | invoice_manager_agent.py | ✅ Disponible |

---

## 11. File System Monitoring

### 11.1 Directorios Monitoreados

| Directorio | Propósito | Extensiones |
|------------|----------|-------------|
| inbox/ | Facturas entrantes | .pdf, .txt, .jpg, .png |
| processed/ | Facturas procesadas | .pdf, .txt, .jpg |
| rejected/ | Facturas rechazadas | .pdf, .txt, .jpg |
| new_invoices/ | Facturas de prueba | .txt |
| contracts/ | Contratos | .pdf, .txt |

### 11.2 Métricas por Archivo

```json
{
  "inbox": {
    "file_count": 3,
    "size_bytes": 150000,
    "size_human": "146.5 KB",
    "by_extension": {
      ".pdf": {"count": 2, "size_bytes": 100000, "avg_size_bytes": 50000},
      ".txt": {"count": 1, "size_bytes": 50000, "avg_size_bytes": 50000}
    },
    "recent_files": [
      {"name": "invoice_001.pdf", "size_bytes": 50000, "modified": "2026-07-13T..."}
    ]
  }
}
```

---

## 12. A2A Integration

### 12.1 Agentes A2A

```
a2a/
└── external_auditor_agent/
    ├── agent.py
    └── server.py
```

### 12.2 Estados

```json
{
  "external_auditor": {
    "url": "http://127.0.0.1:8003/health",
    "status": {"ok": false, "status": "down"}
  },
  "a2a_directory": {
    "exists": true,
    "agents_found": ["external_auditor_agent"],
    "agent_count": 1
  }
}
```

---

## 13. Uso desde el Frontend

### 13.1 Polling Interval Recomendado

```javascript
// Consultar observabilidad cada 30 segundos
setInterval(async () => {
  const response = await fetch('/health/observability');
  const data = await response.json();
  
  // Mostrar health score
  document.getElementById('health-score').textContent = `${data.health_score}%`;
  
  // Mostrar estado
  const statusEl = document.getElementById('status');
  statusEl.textContent = data.status.toUpperCase();
  statusEl.className = `status-${data.status}`;
  
  // Mostrar servicios
  const servicesList = document.getElementById('services');
  servicesList.innerHTML = '';
  Object.entries(data.services.services).forEach(([name, svc]) => {
    const li = document.createElement('li');
    li.textContent = `${name}: ${svc.status.status} (${svc.type})`;
    li.className = svc.status.ok ? 'ok' : 'error';
    servicesList.appendChild(li);
  });
  
  // Mostrar métricas
  document.getElementById('databases-ok').textContent = 
    `${data.summary.databases_ok}/${data.summary.databases_total}`;
  document.getElementById('mcp-tools').textContent = 
    data.summary.mcp_tools_configured;
  document.getElementById('rag-docs').textContent = 
    data.summary.rag_documents_indexed;
  document.getElementById('errors').textContent = 
    data.summary.total_errors;
  
}, 30000);
```

### 13.2 Dashboard Components

```javascript
// Indicador de salud
<div id="health-score">95%</div>
<div id="status" class="status-healthy">HEALTHY</div>

// Lista de servicios
<ul id="services">
  <li class="ok">backend: up (critical)</li>
  <li class="ok">supplier_service: up (critical)</li>
  <li class="ok">contract_service: up (critical)</li>
  <li class="error">mcp_toolbox: down (secondary)</li>
</ul>

// Métricas
<div>
  <span>Databases: <span id="databases-ok">4/4</span></span>
  <span>MCP Tools: <span id="mcp-tools">5</span></span>
  <span>RAG Docs: <span id="rag-docs">150</span></span>
  <span>Errors: <span id="errors">5</span></span>
</div>
```

---

## 14. API Reference

### 14.1 Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check básico |
| GET | `/health/observability` | Observabilidad completa V3.0.0 |
| GET | `/agents/health` | Health de agentes |
| GET | `/logs/recent` | Logs recientes |

### 14.2 Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `connection_error` | Servicio no disponible | Verificar que el servicio esté corriendo |
| `timeout` | Servicio lento | Aumentar timeout o verificar rendimiento |
| `not_found` | Recurso no existe | Verificar configuración de paths |

---

## 15. Referencias

| Documento | Descripción |
|-----------|-------------|
| `app/backend/main.py` | Endpoints de observabilidad |
| `app/backend/health_extended.py` | Módulo de salud completo V3.0.0 |
| `mcp_config/tools.yaml` | Configuración MCP Toolbox |
| `mcp_config/mcp_servers.json` | Configuración MCP Servers |
| `docs/MCP_TOOLBOX.md` | Documentación MCP Toolbox |
| `docs/SPECS_008_RAG.md` | Especificación RAG |
| `docs/SPECS_009_A2A.md` | Especificación A2A |

---

## 16. Changelog

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 3.0.0 | 2026-07-13 | Ampliación completa: MCP, A2A, Agents, File tracking detallado, Log levels |
| 2.0.0 | 2026-07-13 | Agregado /health/observability |
| 1.0.0 | 2026-07-12 | Versión inicial con health básico |

---

**Versión**: 3.0.0  
**Última actualización**: 2026-07-13
