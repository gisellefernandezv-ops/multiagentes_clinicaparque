# SPECS 010 — Evaluación y Testing

> **Proyecto**: InvoiceFlow  
> **Tipo**: Especificación de Quality Assurance  
> **Estado**: ✅ Implementado

---

## 1. Sistema de Evaluación

El proyecto incluye un framework de evaluación para medir la calidad del sistema.

### 1.1 Componentes

| Componente | Ubicación | Descripción |
|-----------|-----------|-------------|
| **Golden Cases** | `evaluation/golden_cases.py` | 20 casos de prueba |
| **LLM Judge** | `evaluation/llm_judge.py` | Gemini como evaluador |
| **Métricas** | `evaluation/metrics.py` | Runner y agregación |

---

## 2. Golden Cases

### 2.1 Lista de Casos

| ID | Descripción | Decisión Esperada |
|----|-------------|-------------------|
| GC001 | Factura válida dentro del límite | APPROVED |
| GC002 | Supera límite contractual | REJECTED |
| GC003 | Proveedor inactivo | REJECTED |
| GC004 | Supera guardrail ($500k) | ESCALATED |
| GC005 | Proveedor inexistente | REJECTED |
| GC006 | Datos incompletos | REJECTED |
| GC007 | Factura duplicada | REJECTED |
| GC008 | CUIT inválido | REJECTED |
| GC009 | Monto negativo | REJECTED |
| GC010 | Fecha futura | REJECTED |
| GC011 | Archivo no PDF | REJECTED |
| GC012 | Archivo muy grande | REJECTED |
| GC013 | Razón social no coincide | REJECTED |
| GC014 | Factura vencida | REJECTED |
| GC015 | Fraccionamiento detectado | ESCALATED |
| GC016 | Alto riesgo ML | ESCALATED |
| GC017 | Sin contrato vigente | ESCALATED |
| GC018 | Alta confianza de aprobación | APPROVED |
| GC019 | Varios factores de riesgo | REJECTED |
| GC020 | Caso edge - monto exacto | APPROVED |

### 2.2 Estructura

```python
GOLDEN_CASES = [
    {
        "id": "GC001",
        "description": "Factura válida dentro del límite",
        "input": {
            "invoice_id": "INV-001",
            "supplier_id": "SUP001",
            "amount": 50000,
            "invoice_date": "2025-06-01"
        },
        "expected_decision": "APPROVED",
        "expected_fields": ["confirmation_id", "payment_status"]
    },
    # ... más casos
]
```

---

## 3. LLM Judge

### 3.1 Rol

Gemini actúa como juez semántico para evaluar:
- Coincidencia de decisión (60%)
- Coherencia de justificación (25%)
- Presencia de campos (15%)

### 3.2 Puntuación

```python
score = (
    0.60 * decision_match +      # ¿Decisión correcta?
    0.25 * justification_coherence +  # ¿Justificación tiene sentido?
    0.15 * fields_present         # ¿Campos obligatorios?
)
```

### 3.3 Output del Judge

```python
{
    "case_id": "GC001",
    "decision_match": True,
    "justification_coherence": 0.85,
    "fields_present": True,
    "overall_score": 0.95,
    "reasoning": "La decisión es correcta y la justificación es coherente..."
}
```

---

## 4. Métricas

### 4.1 Pass Rate

```python
def calculate_pass_rate(results):
    passed = sum(1 for r in results if r["decision_match"])
    return passed / len(results)
```

**Objetivo**: > 95%

### 4.2 BertScore F1

Mide similitud semántica entre justificaciones esperadas y reales.

**Modelo**: `xlm-roberta-base` (multilingüe)

**Objetivo**: > 0.85

### 4.3 Latencia

```python
latency = end_time - start_time
```

**Objetivo**: < 30 segundos end-to-end

---

## 5. Ejecución

### 5.1 Comando

```bash
python -m evaluation.metrics
```

### 5.2 Salida Esperada

```
============================================================
EVALUACIÓN — InvoiceFlow Golden Cases
============================================================

GC001 ... PASS (judge=1.00, bert_f1=0.91, latency=2.3s)
GC002 ... PASS (judge=1.00, bert_f1=0.88, latency=2.1s)
GC003 ... PASS (judge=1.00, bert_f1=0.95, latency=1.8s)
GC004 ... PASS (judge=0.95, bert_f1=0.82, latency=2.5s)
GC005 ... PASS (judge=1.00, bert_f1=0.90, latency=1.9s)
...

============================================================
RESULTADOS FINALES
============================================================
Pass Rate: 19/20 (95.0%)
Avg BertScore F1: 0.89
Avg Latency: 2.3s
```

---

## 6. Smoke Tests

### 6.1 Componentes Individuales

```bash
# Test guardrails
python -m guardrails.invoice_guardrail

# Test tools
python -m tools.supplier_mcp_tool
python -m tools.rag_tool
python -m tools.payment_db_tool

# Test agents
python -m agents.validator_agent
python -m agents.contract_agent
python -m agents.payment_agent
python -m agents.orchestrator

# Test services
python -m app.services.supplier_service.main
python -m app.services.contract_service.main
```

### 6.2 Script Automatizado

```bash
smoke_test.bat
```

---

## 7. Dataset de Evaluación

### 7.1 Ubicación

```
tests/eval/
├── datasets/
│   └── invoiceflow-dataset.json
└── eval_config.yaml
```

### 7.2 Configuración

```yaml
eval_config:
  model: gemini-2.0-flash
  metrics:
    - accuracy
    - precision
    - recall
    - latency
    - coverage
  thresholds:
    pass_rate: 0.95
    bertscore_f1: 0.85
    latency_seconds: 30
```

---

## 8. Referencias

| Documento | Descripción |
|-----------|-------------|
| `evaluation/golden_cases.py` | Definición de casos |
| `evaluation/llm_judge.py` | Evaluador LLM |
| `evaluation/metrics.py` | Runner de métricas |

---

**Versión**: 2.0.0  
**Última actualización**: 2026-07-15
