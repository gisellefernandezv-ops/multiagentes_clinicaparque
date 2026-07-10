# SPECS 008 — RAG y ChromaDB

> **Proyecto**: InvoiceFlow  
> **Tipo**: Especificación Técnica  
> **Estado**: ✅ Implementado

---

## 1. Resumen

El sistema usa **Retrieval Augmented Generation (RAG)** con **ChromaDB** para buscar contratos de proveedores de forma semántica.

### 1.1 Componentes

| Componente | Descripción |
|-----------|-------------|
| **ChromaDB** | Vector store para embeddings |
| **Gemini Embeddings** | Modelo de embeddings |
| **Contracts** | Documentos fuente (.txt) |
| **Retriever** | Búsqueda semántica |

---

## 2. Arquitectura RAG

```
┌─────────────────────────────────────────────────────────────────────┐
│                          INGESTA                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌───────────────────┐     ┌──────────────┐   │
│  │ Contratos   │────>│ Embedding Model   │────>│   ChromaDB   │   │
│  │ (.txt)      │     │ (Gemini-001)      │     │ (Persistent) │   │
│  └──────────────┘     └───────────────────┘     └──────────────┘   │
│                                                                      │
│  Chunking: 500 chars con overlap de 50                              │
│  Modelo: models/gemini-embedding-001                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CONSULTA                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌───────────────────┐     ┌──────────────┐   │
│  │ Query        │────>│ Embedding Model   │────>│   ChromaDB   │   │
│  │ (supplier_id │     │ (RETRIEVAL_QUERY) │     │   Search     │   │
│  │  + amount)   │     └───────────────────┘     └──────┬───────┘   │
│  └──────────────┘                                      │            │
│                                                         ▼            │
│                                              ┌──────────────┐      │
│                                              │  Fragmento   │      │
│                                              │  + Límite    │      │
│                                              └──────────────┘      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Ingesta de Contratos

### 3.1 Ubicación

```
data/contracts/
├── contrato_proveedor_001.txt  # SUP001
├── contrato_proveedor_002.txt  # SUP002
├── contrato_proveedor_003.txt  # SUP003
├── contrato_proveedor_004.txt  # SUP004
└── contrato_proveedor_005.txt  # SUP005
```

### 3.2 Script de Ingesta

**Archivo**: `rag/ingest.py`

**Funciones**:
1. Lee archivos .txt de contratos
2. Divide en chunks (500 chars, 50 overlap)
3. Genera embeddings con Gemini
4. Guarda en ChromaDB

### 3.3 Chunking

```python
def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Divide texto en chunks con overlap."""
    # Prioriza cortes en párrafos
    # fallback: oraciones
    # fallback final: palabras
```

### 3.4 Metadata

```python
metadata = {
    "supplier_id": "SUP001",
    "source_file": "contrato_proveedor_001.txt",
    "chunk_index": 0,
    "total_chunks": 5
}
```

---

## 4. Búsqueda Semántica

### 4.1 Query

```python
query = f"contrato proveedor {supplier_id} monto máximo autorizado por factura límite"
```

### 4.2 Parámetros

```python
collection.query(
    query_texts=[query],
    n_results=2,  # Top 2 chunks
    where={"supplier_id": supplier_id}  # Filtrar por proveedor
)
```

### 4.3 Extracción de Monto

```python
def _parse_amount(text: str) -> Optional[float]:
    """Extrae monto máximo del texto."""
    # Patrones:
    # - "monto máximo: $150,000"
    # - "límite contractual: $150.000"
    # - "$150,000"
```

---

## 5. Embedding Function

### 5.1 Wrapper Custom

**Archivo**: `rag/embedding_function.py`

**Problema**: ChromaDB 1.5.x no es compatible con `google-generativeai` 0.8.6

**Solución**: Wrapper custom que usa `google.genai.Client`

```python
class GoogleGenAiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name: str, task_type: str):
        self.model = model_name
        self.task_type = task_type  # RETRIEVAL_DOCUMENT | RETRIEVAL_QUERY
    
    def __call__(self, texts: List[str]) -> List[List[float]]:
        # Usa google.genai.Client en vez de google.generativeai
```

### 5.2 Modelos

| Uso | Modelo | Task Type |
|-----|--------|----------|
| Ingesta | `models/gemini-embedding-001` | `RETRIEVAL_DOCUMENT` |
| Query | `models/gemini-embedding-001` | `RETRIEVAL_QUERY` |

---

## 6. Contract Service API

### 6.1 Endpoints

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| GET | `/health` | Health check |
| POST | `/contracts/upload` | Subir contrato |
| GET | `/contracts` | Listar contratos |
| GET | `/contracts/{id}/check?amount=N` | Verificar límite |
| POST | `/contracts/seed` | Cargar demo |

### 6.2 Check Contract

**Request**:
```
GET /contracts/SUP001/check?amount=50000
```

**Response**:
```json
{
    "supplier_id": "SUP001",
    "found": true,
    "contract_limit": 150000.0,
    "within_limit": true,
    "contract_fragment": "...",
    "error": null
}
```

---

## 7. Persistencia

### 7.1 Ubicación

```
app/data/chroma_db/
├── index.bin
├── index.json
└── ...
```

### 7.2 Colecciones

| Nombre | Descripción |
|--------|-------------|
| `contracts` | Contratos de proveedores |

---

## 8. Contratos de Demo

| Proveedor | Límite Contractual |
|-----------|--------------------|
| SUP001 (TechCorp SA) | $150,000 |
| SUP002 (Papelería Norte SRL) | $30,000 |
| SUP004 (Limpieza Total SRL) | $80,000 |
| SUP005 (Consultoría Digital SA) | $200,000 |

---

## 9. Referencias

| Documento | Descripción |
|-----------|-------------|
| `rag/ingest.py` | Script de ingesta |
| `rag/retriever.py` | Búsqueda semántica |
| `rag/embedding_function.py` | Wrapper de embeddings |
| `SPECS_003_HERRAMIENTAS.md` | `search_contract_tool` |

---

**Versión**: 2.0.0  
**Última actualización**: 2026-07-15
