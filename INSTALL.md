# Guía de instalación — Sistema Multiagente de Aprobación de Facturas

> Documento complementario al [`README.md`](README.md). Esta guía explica
> cada paso de la instalación **y por qué se hace**, para que un nuevo
> desarrollador pueda levantar el sistema desde cero sin sorpresas.

---

## Tabla de contenidos

1. [Requisitos previos](#1-requisitos-previos)
2. [Paso 1 — Obtener el código](#paso-1--obtener-el-código)
3. [Paso 2 — Verificar Python](#paso-2--verificar-python)
4. [Paso 3 — Crear el entorno virtual](#paso-3--crear-el-entorno-virtual)
5. [Paso 4 — Activar el venv](#paso-4--activar-el-venv)
6. [Paso 5 — Instalar dependencias](#paso-5--instalar-dependencias)
7. [Paso 6 — Configurar la API key de Google](#paso-6--configurar-la-api-key-de-google)
8. [Paso 7 — Verificar la instalación](#paso-7--verificar-la-instalación)
9. [Paso 8 — Indexar contratos (RAG)](#paso-8--indexar-contratos-rag)
10. [Paso 9 — Levantar la UI de ADK](#paso-9--levantar-la-ui-de-adk)
11. [Paso 10 — Probar el sistema](#paso-10--probar-el-sistema)
12. [Automatización con scripts](#automatización-con-scripts)
13. [Troubleshooting de instalación](#troubleshooting-de-instalación)

---

## 1. Requisitos previos

Antes de empezar, asegurate de tener:

| Requisito | Versión mínima | Cómo verificarlo | Por qué |
|---|---|---|---|
| **Python** | 3.11+ (probado en 3.12) | `python --version` | ADK 2.x requiere 3.11+. Algunas features (type hints nuevos) no andan en 3.10. |
| **pip** | 23+ | `pip --version` | Para resolver dependencias modernas (overrides, markers). |
| **Conexión a internet** | — | `ping google.com` | Para descargar deps de PyPI y para llamar a la API de Gemini en runtime. |
| **API key de Google AI Studio** | — | [aistudio.google.com](https://aistudio.google.com) → API keys | La necesitan todos los agentes (LLM) y la ingesta RAG (embeddings). |
| **~500 MB libres en disco** | — | Explorador de archivos | ChromaDB persiste local (~10 MB) + `bert-score` baja `xlm-roberta-base` (~800 MB) si se corre evaluación. |
| **Windows / macOS / Linux** | — | — | El sistema es multiplataforma. Probado en Windows 10/11. |

**Por qué Python 3.11+ específicamente**: `google-adk 2.x` declara
`requires-python = ">=3.11"` en su `pyproject.toml`. Además, usamos
`from __future__ import annotations` para soportar tipado en cadenas
(string annotations) que funciona mejor en 3.11+.

**Por qué `google-generativeai` + `google-genai`**: la consigna nos obliga
a usar Gemini. Necesitamos ambos paquetes porque:
- `google-genai` (nuevo SDK, no deprecado) → lo usamos para embeddings.
- `google-generativeai` (viejo SDK, deprecado) → lo usa internamente
  el LLM judge de la evaluación. Si no vas a correr evaluación, podés
  desinstalarlo, pero `requirements.txt` lo deja por simplicidad.

---

## Paso 1 — Obtener el código

```bash
# Si tenés git
git clone <repo-url>
cd <repo-cloned>/invoice_approval_system

# Si no, descargá el ZIP y descomprimilo
cd invoice_approval_system
```

**Por qué un directorio por proyecto**: el `requirements.txt` está
optimizado para este proyecto. Mezclarlo con otro venv puede causar
conflictos de versiones (ej: chromadb vs langchain).

---

## Paso 2 — Verificar Python

```bash
python --version
```

Salida esperada: `Python 3.11.x` o superior.

**Por qué**: si tenés Python <3.11, `pip install` fallará con
`ERROR: Could not find a version that satisfies the requirement google-adk`.

**Si no tenés Python**:
- Windows: descargalo de [python.org](https://www.python.org/downloads/).
  **IMPORTANTE**: tildar "Add Python to PATH" en el instalador.
- macOS: `brew install python@3.12`.
- Linux (Debian/Ubuntu): `sudo apt install python3.12 python3.12-venv`.

---

## Paso 3 — Crear el entorno virtual

```bash
# Windows
python -m venv .venv

# Linux / macOS
python3 -m venv .venv
```

Esto crea una carpeta `.venv/` con un Python y pip aislados del sistema.

**Por qué un venv y no instalar global**:

1. **Aislamiento**: las versiones de `chromadb`, `google-adk`, etc. pueden
   romper otros proyectos si se instalan globalmente.
2. **Reproducibilidad**: otro desarrollador puede clonar el repo, hacer
   `pip install -r requirements.txt` y obtener exactamente las mismas
   versiones.
3. **Sin permisos de admin**: no requiere `sudo` ni permisos elevados.
4. **Limpieza**: para "desinstalar todo" basta con borrar `.venv/`.

**Por qué `.venv/` como nombre**: es el nombre que `python -m venv` usa
por defecto y el que `gitignore`/`pipenv`/`poetry` esperan. También está
excluido por nuestro `.gitignore`.

---

## Paso 4 — Activar el venv

```bash
# Windows (cmd)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

**Cómo saber si está activado**: el prompt cambia a `(.venv) ...`.

**Por qué hay que activarlo**:
- Activa el `PATH` del venv → `python` y `pip` apuntan a `.venv/`.
- Activa variables de entorno (`VIRTUAL_ENV`).
- Es reversible con `deactivate`.

**Troubleshooting Windows PowerShell**: si te aparece *"running scripts is
disabled on this system"*, ejecutá una vez como admin:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Paso 5 — Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Por qué actualizar pip primero**: pip moderno (>=23) resuelve mejor
los markers de plataforma y maneja `overrides` correctamente.

**Qué se instala** (con justificación):

| Paquete | Para qué | Por qué esta versión |
|---|---|---|
| `google-adk>=1.0.0` | Framework de agentes | Pedido por la consigna. 2.x es la línea estable actual. |
| `google-generativeai>=0.8.0` | SDK viejo (para el judge de evaluación) | Lo usa `evaluation/llm_judge.py`. Si no corrés evaluación, podés obviarlo. |
| `chromadb>=0.5.0` | Vector store para RAG | Pedido por la consigna. 0.5+ tiene la API de `PersistentClient` que usamos. |
| `python-dotenv>=1.0.0` | Cargar `.env` | Estándar de facto. |
| `mcp>=1.0.0` | Soporte MCP (futuro) | Pedido por la consigna. No exponemos server MCP en el TP, pero dejamos la lib instalada. |
| `bert-score>=0.3.13` | Métrica de similitud semántica | Pedido por la consigna. Trae `torch` (~250 MB) y `transformers` (~600 MB de modelo) como deps transitivas. |

**Por qué `bert-score` y no BLEU/ROUGE**: las justificaciones del
orquestador son texto libre, no n-gramas. BLEU mide overlap léxico y
penaliza reformulaciones válidas. BertScore mide similitud semántica
con embeddings contextuales.

**Troubleshooting**: si `bert-score` falla por memoria (instala modelos
grandes), podés comentar la línea de `requirements.txt` y usar solo el
LLM judge. Pero perderás la métrica cuantitativa de justificaciones.

**Tiempo estimado**: 3-8 minutos dependiendo de la conexión (descarga
~500 MB entre `torch`, `transformers` y el modelo `xlm-roberta-base`).

---

## Paso 6 — Configurar la API key de Google

1. Copiá el archivo de plantilla:
   ```bash
   # Windows (cmd)
   copy .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```

2. Editá `.env` y reemplazá el valor de `GOOGLE_API_KEY`:
   ```env
   GOOGLE_API_KEY=AIzaSy...tu_key_real
   ```

**Cómo obtener la API key**:
1. Ir a [aistudio.google.com](https://aistudio.google.com).
2. Click en "Get API key" → "Create API key".
3. Copiar el valor (empieza con `AIzaSy...`).

**Por qué `.env` y no hardcodear**: nunca se debe commitear una API key
a git. El `.gitignore` excluye `.env`, pero es importante entender que
es un patrón estándar de 12-factor app.

**Por qué `python-dotenv` carga el `.env`**: `agent.py` llama a
`load_dotenv(PROJECT_ROOT / ".env")` en su primera línea, antes de
cualquier import que pueda leer `os.getenv("GOOGLE_API_KEY")`. Esto
asegura que cuando ChromaDB instancia el `GoogleGenAiEmbeddingFunction`
la variable ya está en el entorno.

**⚠️ No commitear `.env`**: ya está cubierto por `.gitignore`, pero si
clonás el repo en otra máquina, volvé a copiar `.env.example` → `.env`.

---

## Paso 7 — Verificar la instalación

Ejecutá los smoke tests individuales para confirmar que cada componente
anda:

```bash
# Windows
python -m guardrails.invoice_guardrail
python -m tools.supplier_mcp_tool
python -m tools.payment_db_tool
python -m tools.rag_tool
python -m agents.validator_agent
python -m agents.contract_agent
python -m agents.payment_agent
python -m agents.orchestrator
python -m sessions.session_manager
```

**O automatizado** (Windows): `smoke_test.bat`.

**Salida esperada de cada uno**:

| Comando | Salida esperada |
|---|---|
| `guardrails` | `✓ válida → APPROVE`, etc. (6 tests del guardrail) |
| `supplier_mcp_tool` | 3 líneas: `SUP001 → {found: True, ...}`, `SUP003 → {INACTIVE}`, `SUP999 → {found: False}` |
| `payment_db_tool` | 2 registros insertados con `confirmation_id` tipo `PAY-XXXXXXXX` |
| `rag_tool` | (Requiere haber hecho la ingesta — ver Paso 8) `SUP001 / $50.000: found=True, limit=$150000, within=True` |
| `agents.*` | Cada uno imprime `✓ <nombre> creado con N tool(s)` |
| `sessions.session_manager` | `Sesión creada: sess-XXXXXXXXXXXX`, state inicial, updates, state final |

**Por qué verificar antes de levantar la UI**: si algún componente
falla, queremos saber **cuál** antes de que ADK nos muestre un error
genérico en el navegador. Es más rápido debuggear desde CLI.

---

## Paso 8 — Indexar contratos (RAG)

Este paso es **obligatorio la primera vez** (y cada vez que agregues/modifiques
contratos en `data/contracts/`).

```bash
python rag/ingest.py
```

**Qué hace** (ver [`rag/ingest.py`](rag/ingest.py)):

1. Lee todos los `.txt` de `data/contracts/`.
2. Para cada contrato:
   - Extrae el `supplier_id` del nombre de archivo (ej.
     `contrato_proveedor_001.txt` → `SUP001`).
   - Divide el texto en chunks de ~500 chars con 50 chars de overlap
     (mejor calidad que cortar a la fuerza — respeta saltos de párrafo).
   - Genera embeddings con `GoogleGenAiEmbeddingFunction` (task
     `RETRIEVAL_DOCUMENT`).
3. Persiste los chunks + embeddings + metadata en `data/chroma_db/`.

**Salida esperada**:
```
[ingest] Encontrados 4 contratos en <path>
[ingest] Colección 'contracts' existente eliminada.
[ingest] contrato_proveedor_001.txt → supplier=SUP001, 5 chunks
[ingest] contrato_proveedor_002.txt → supplier=SUP002, 5 chunks
[ingest] contrato_proveedor_004.txt → supplier=SUP004, 5 chunks
[ingest] contrato_proveedor_005.txt → supplier=SUP005, 6 chunks
[ingest] ✓ Ingesta completa: 4 archivos, 21 chunks
[ingest] ✓ Colección 'contracts' persistida en <path>
```

**Por qué este paso es separado**:

- **Embeddings son costosos**: generan una llamada a la API de Google por
  cada chunk. Hacerlo on-the-fly en cada query multiplicaría la latencia
  y el costo por 100x.
- **Idempotencia**: la ingesta elimina y recrea la colección, así que se
  puede correr múltiples veces sin duplicar datos.
- **Offline**: una vez indexado, el retrieval no llama a la API de
  embeddings (solo el LLM del agente).

**Por qué chunking por caracteres (no por tokens)**: simplicidad. Para
4 contratos de 1-2 KB cada uno, no necesitamos optimizaciones
semánticas de tokenización. Si el corpus creciera, consideraríamos
`RecursiveCharacterTextSplitter` de LangChain o `SemanticChunker`.

**Por qué 500 chars + 50 overlap**: suficiente para capturar cláusulas
contractuales completas (típicamente <400 chars) sin perder contexto en
los bordes.

**⚠️ Si falla con `404 NOT_FOUND models/embedding-001`**: estás en la
versión vieja del código. Actualizá a v1.1.0 (ver
[`CHANGELOG.md`](CHANGELOG.md)) o cambiá el modelo a
`models/gemini-embedding-001` en `rag/embedding_function.py`.

---

## Paso 9 — Levantar la UI de ADK

Desde el directorio **padre** del proyecto:

```bash
cd ..
adk web invoice_approval_system
```

O desde dentro del proyecto:

```bash
cd invoice_approval_system
adk web .
```

**Qué hace ADK**:

1. Detecta `agent.py` como entry point (busca la variable `root_agent`).
2. Levanta un server FastAPI en `http://localhost:8000`.
3. Sirve una UI React para chatear con el agente.
4. Mantiene sesiones en `InMemorySessionService`.

**Por qué `adk web` y no Flask/FastAPI custom**: ADK ya provee la UI con
gestión de sesiones, event inspector y soporte de tools. Reescribirlo
desde cero nos llevaría 10x más tiempo sin beneficio.

**⚠️ Si dice `ModuleNotFoundError: No module named 'agents'`**: estás
ejecutando `adk web` desde el directorio equivocado o te falta un
`__init__.py`. Verificar que `agents/__init__.py` exista.

**Salida esperada**:
```
INFO:     Uvicorn running on http://localhost:8000
INFO:     Application startup complete.
```

---

## Paso 10 — Probar el sistema

1. Abrir el navegador en `http://localhost:8000`.
2. En el selector de agente, elegir `invoice_orchestrator`.
3. En el chat, pegar uno de los JSON de ejemplo del
   [`README.md`](README.md#8-ejemplos-de-uso) sección 8.
4. Observar la respuesta.

**Para detener el server**: `Ctrl+C` en la terminal donde corre `adk web`.

**Por qué los JSON están hardcodeados en el README**: sirven como
smoke tests manuales rápidos. Cada uno cubre una rama distinta del
sistema (APPROVED, REJECTED por límite, REJECTED por inactivo,
ESCALATED, REJECTED por inexistente, REJECTED por incompletos).

---

## Automatización con scripts

El proyecto incluye 3 scripts `.bat` (Windows) que automatizan los pasos
anteriores:

### `setup.bat` — Setup completo desde cero
```bash
setup.bat
```
Hace: crea venv, instala deps, copia `.env`, corre ingesta.

**Por qué existe**: para que un evaluador o nuevo dev pueda levantar
todo con un doble click sin tener que recordar la secuencia exacta.

### `start.bat` — Levanta la UI
```bash
start.bat
```
Hace: activa venv y corre `adk web`.

**Por qué existe**: atajo a la operación más frecuente (levantar la
demo para probar).

### `smoke_test.bat` — Verificación rápida
```bash
smoke_test.bat
```
Hace: corre los 9 smoke tests en secuencia.

**Por qué existe**: para CI o para verificar después de un cambio que
no rompimos nada.

**Equivalentes Linux/macOS**: los `.bat` solo funcionan en Windows. Para
Linux/macOS usar los comandos equivalentes del README o crear un
`Makefile`.

---

## Troubleshooting de instalación

### Error: `python no se reconoce como comando`
**Causa**: Python no está en el `PATH` del sistema.
**Fix**: reinstalar Python tildando "Add Python to PATH" o agregar
`C:\Users\<tu_usuario>\AppData\Local\Programs\Python\Python312\` al PATH
manualmente.

### Error: `pip install` falla con `Microsoft Visual C++ 14.0 required`
**Causa**: alguna dep (típicamente `chromadb` o `onnxruntime`) necesita
compilar extensiones C++.
**Fix**: instalar [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022) con "Desktop development with C++".

### Error: `Could not find a version that satisfies the requirement google-adk`
**Causa**: Python <3.11.
**Fix**: actualizar Python.

### Error: `GOOGLE_API_KEY no está configurada`
**Causa**: no creaste `.env` o está mal escrito.
**Fix**: verificar que `.env` exista en la raíz del proyecto y contenga
`GOOGLE_API_KEY=AIzaSy...`. **No** comillas alrededor del valor.

### Error: `404 NOT_FOUND models/embedding-001`
**Causa**: estás corriendo una versión vieja del código que usa el modelo
deprecado.
**Fix**: actualizar a v1.1.0 (ver `CHANGELOG.md`).

### Error: `ModuleNotFoundError: No module named 'agents'`
**Causa**: `adk web` se está ejecutando desde un directorio que no ve el
paquete.
**Fix**: ejecutar desde el directorio padre con `adk web invoice_approval_system`
o asegurarse de que `agents/__init__.py` exista.

### Error: `UnicodeEncodeError: 'charmap' codec`
**Causa**: consola Windows (cp1252) no soporta caracteres unicode (✓, ✗).
**Fix**: usar `set PYTHONIOENCODING=utf-8` antes del comando, o correr
desde PowerShell/Windows Terminal que sí soporta UTF-8.

### La UI levanta pero las respuestas son lentas (>10s)
**Causa**: normal. `gemini-2.0-flash` + 3 sub-agentes + RAG ≈ 3-7s por
factura en promedio.
**Mitigación**: si es problema, cambiar `model="gemini-2.0-flash-latest"`
a `model="gemini-2.5-flash"` (cuando esté GA) o `gemini-1.5-flash` (más
viejo pero más rápido).

### `bert-score` tarda mucho en la primera evaluación
**Causa**: la primera invocación descarga `xlm-roberta-base` (~500 MB).
**Fix**: dejar que termine una vez; las siguientes son instantáneas.