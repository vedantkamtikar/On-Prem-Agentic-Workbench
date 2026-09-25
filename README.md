# Sovereign On-Prem Agentic AI Workbench

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Ollama: Supported](https://img.shields.io/badge/Ollama-Local%20Inference-orange.svg)](https://ollama.com)
[![Air-Gap: Verified](https://img.shields.io/badge/Air--Gap-100%25%20Offline%20Loopback-success.svg)](#9-air-gap-security--network-isolation-proof)
[![GitHub Repository](https://img.shields.io/badge/GitHub-On--Prem--Agentic--Workbench-blue?logo=github)](https://github.com/vedantkamtikar/On-Prem-Agentic-Workbench)

An air-gapped, self-hosted, multi-model agentic AI workbench built for confidential industrial knowledge work. Engineered specifically for on-premise deployment on standard engineering laptop and workstation hardware (**NVIDIA GeForce RTX 4050 6GB VRAM, AMD Ryzen 7 7435HS, 24GB System RAM**).

---

## 1. Problem & Architectural Rationale

Refineries, power plants, manufacturing facilities, aerospace, and defense institutions generate routine, high-stakes technical work: scanned equipment manuals, P&ID schematics, vibration sensor logs, vendor bids, and executive approval notes.

- **The Confidentiality Bottleneck**: Commercial cloud AI APIs are strictly prohibited due to trade-secret, intellectual property, and defense compliance security policies.
- **The Sovereign Solution**: A self-hosted, autonomous agentic workbench that runs 100% locally inside an air-gapped operating system boundary.
- **Zero Cloud Footprint**: Outbound WAN requests are blocked at the OS kernel level; all inference, OCR, and vector embeddings execute strictly on-premise with zero external socket activity.
- **Consumer Hardware Feasibility**: Solves the VRAM constraint through a resident 0.8B classifier router coupled with dynamic PCIe worker model hot-swapping and strict CPU offloading for non-LLM tasks.

---

## 2. System Architecture

```
                                 [ Web Console / Engineering Cockpit ]
                                (3-Screen SPA: Workspace | KB | Audit)
                                                   │
                                                   ▼
                                        [ FastAPI Backend Server ]
                                                   │
                                                   ▼
                                      [ LangGraph ReAct Orchestrator ]
                           (4096 Context Window · 50s Timeout Guard · Fallback Extractor)
                                                   │
                ┌──────────────────────────────────┼──────────────────────────────────┐
                ▼                                  ▼                                  ▼
    [ Dynamic Model Router ]             [ Sandboxed Tool Suite ]           [ Grounded Local RAG ]
   (15ms CPU Semantic Classifier)       (File, Doc, Vision, Code)          (all-MiniLM-L6-v2 CPU)
                │                                  │                                  │
    ┌───────────┴───────────┐            ┌─────────┴─────────┐              ┌─────────┴─────────┐
    ▼                       ▼            ▼                   ▼              ▼                   ▼
[Resident Router]    [Worker Pool]   [CPU EasyOCR]     [Isolated Code]     [Plant SOP Store] [Vector Index]
 Qwen3.5-0.8B        Qwen2.5-VL-3B   (CPU Thread)      (Network Blocked)   (data/kb/*.pdf,   (Cosine Sim /
 (~1.0 GB VRAM)      Qwen3.5-4B                                             .md, .txt)        CPU Embeddings)
                     Qwen2.5-Coder-7B
                            │                    │
                            └──────────┬─────────┘
                                       ▼
                         [ Dynamic Deliverable Engine ]
                       (.docx, .xlsx, .pptx, Code Scripts)
```

---

## 3. Target Hardware & VRAM Memory Budget

| Component | Target Model / Engine | Compute Engine | VRAM Footprint | Lifecycle State |
|---|---|---|---|---|
| **Resident Model Router** | `Qwen3.5-0.8B` (`qwen3.5:0.8b`) | GPU (CUDA) | **~1.0 GB** | **Pinned Resident** (`keep_alive: 24h`) |
| **Vision & Diagram Specialist** | `Qwen2.5-VL-3B` (`qwen2.5vl:3b`) | GPU (CUDA) | **~3.2 GB** (at `num_ctx: 4096`) | Active Worker / Cached in RAM |
| **General Reasoning & Drafting** | `Qwen3.5-4B` (`qwen3.5:4b`) | GPU (CUDA) | **~3.4 GB** (at `num_ctx: 4096`) | Active Worker / Cached in RAM |
| **Coding Specialist** | `Qwen2.5-Coder-7B` (`qwen2.5-coder:7b`) | GPU (CUDA) | **~4.7 GB** (at `num_ctx: 4096`) | Standby / Swapped on demand |
| **OCR Preprocessing** | `EasyOCR` + `OpenCV` | **CPU Only** | **0.0 GB** | CPU Worker Thread |
| **RAG Embeddings** | `all-MiniLM-L6-v2` | **CPU Only** | **0.0 GB** | CPU Worker Thread |

### Memory Invariants & Stability Rules
- **6GB VRAM Ceiling**: Peak combined memory is bounded at **~4.4 to 5.7 GB (Worker + 0.8B Router)**, maintaining safe operating headroom on a 6GB laptop GPU without risk of CUDA Out-Of-Memory (OOM) errors.
- **Max 2 Models in VRAM**: At any given time, only the resident router (`0.8b`) and exactly **one** active worker model occupy GPU memory. Inactive workers are cached in the 24GB system RAM for sub-second PCIe hot-swaps.
- **`num_ctx: 4096` Context Envelope**: Tuned for optimal performance, allowing extensive tool schemas, user prompts, and multi-chunk RAG document retrievals without token truncation or VRAM thrashing.
- **Strict CPU Offloading**: OCR extraction and semantic embeddings execute strictly on CPU cores, reserving 100% of GPU VRAM for LLM inference.
- **Sub-15ms Routing**: Semantic prompt classification leverages local CPU sentence embeddings before invoking the 0.8B router, avoiding unnecessary inference cycles.

---

## 4. Key Capabilities & Features

### 1. Three-Screen Streamlined Cockpit
- **1. Workspace**:
  - **Task Specification & Presets**: Fast dispatch presets for SOP compliance, optical tag inspection, and sandboxed vibration calculation.
  - **Inline OCR Inspector**: Attach technical drawings or schematics and trigger instant CPU OCR extraction before submitting directives.
  - **Live ReAct Execution Trace**: Collapsible, step-by-step reasoning logs displaying tool calls, arguments, and execution latency.
  - **Executive Findings & Copy Utility**: Clean, markdown-rendered answer preview with one-click clipboard copying.
  - **Active Deliverable Card**: Displays primary output file, size, format badge, and direct download button.
  - **Real-Time Deliverables Archive**: Live file inventory of the `output/` directory with instant download links.
- **2. Knowledge Base & SOPs**:
  - Live document catalog indexing all technical manuals, data sheets, and procedures in `data/kb/`.
  - CPU vector similarity search with cosine distance relevance scoring and excerpt previews.
  - One-click re-indexing endpoint (`/tools/kb/reindex`) that rebuilds `data/kb_index.json`.
- **3. System Trust & Audit**:
  - Real-time VRAM allocation and system RAM telemetry gauges.
  - Active model pool status showing currently resident and loaded models.
  - Live network socket monitor verifying **100% loopback sockets (`127.0.0.1`) and 0 external WAN calls** with an `AIR_GAP_STRICT_PASS` compliance badge.

### 2. Autonomous Dynamic Deliverable Engine
The orchestrator automatically detects deliverable intents and formats outputs into production-grade files:
- **Microsoft Word (`.docx`)**: Auto-renders multi-section technical reports with corporate styling, bold headings, bulleted action items, and grid tables via `render_docx` or automatic markdown compilation.
- **Microsoft Excel (`.xlsx`)**: Generates structured workbooks with styled navy header rows, alternating white/light-blue data rows, thin borders, and auto-fitted column widths via `openpyxl`.
- **PowerPoint (`.pptx`)**: Produces formatted multi-slide briefing decks with titles, subtitles, and structured bullet points via `render_pptx`.
- **Dynamic Filename & Title Generation**: Automatically generates contextual filenames (e.g., `Kirloskar_Pump_Specification_Report.docx`, `Boiler_Feed_Pump_Metrics.xlsx`) based on the query subject.

### 3. Native Air-Gapped Tool Suite
| Tool Name | Engine / Library | Description |
|---|---|---|
| `render_docx` | `python-docx` | Generates formatted Word reports with headings, bullets, and tables |
| `edit_spreadsheet` | `openpyxl` | Creates and updates Excel workbooks (`.xlsx`) with structured tabular data |
| `render_pptx` | `python-pptx` | Generates formatted PowerPoint presentations (`.pptx`) |
| `search_kb` | `all-MiniLM-L6-v2` | Performs CPU cosine similarity search against local indexed documents |
| `run_code` | `subprocess` / `Docker` | Executes Python code inside an isolated sandbox with network access blocked |
| `ocr_image` | `EasyOCR` + `OpenCV` | Runs CPU-only OCR on technical drawings, schematics, and scanned PDFs |
| `analyze_visual_document` | `Qwen2.5-VL-3B` | Multimodal visual inspection for engineering drawings and P&ID diagrams |
| `read_file` / `write_file` | Filesystem | Path-sandboxed file I/O confined strictly to the workspace root |
| `list_directory` | Filesystem | Path-sandboxed directory listing |

### 4. Resilient ReAct Execution Loop
- **50-Second Reasoning Timeout Guard**: Wraps model inference calls with `asyncio.wait_for` to prevent hanging on oversized queries.
- **Fallback Tool-Call Extraction**: Handles models that return tool calls in markdown JSON code blocks or raw JSON strings when native tool calling format is bypassed.
- **Self-Healing Re-Planning**: Automatically feeds tool errors back into the agent context, allowing it to adjust parameters or alternative file paths autonomously.

### 5. Blueprint Theme Engine
- High-contrast **Dark** and **Light** modes tailored for industrial operations.
- Zero-flash theme initialization using `localStorage` persistence.
- Meets WCAG AA/AAA contrast guidelines for low-light control rooms and bright field environments.

---

## 5. Quickstart & Setup

### Prerequisites
- **OS**: Windows 10/11 or Linux
- **GPU**: NVIDIA GPU with 6GB+ VRAM (e.g., RTX 4050, RTX 3060, RTX 4060, or workstation equivalents)
- **Python**: 3.10 or 3.11 (Conda environment recommended)
- **Ollama**: Installed and running locally ([Download Ollama](https://ollama.com/))

### Step 1: Clone the Repository
```powershell
git clone https://github.com/vedantkamtikar/On-Prem-Agentic-Workbench.git
cd On-Prem-Agentic-Workbench
```

### Step 2: Set Up Python Environment
```powershell
# Create and activate conda environment
conda create -n aiml python=3.11 -y
conda activate aiml

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Key variables configured in `.env`:
```env
OLLAMA_HOST=127.0.0.1:11434
OLLAMA_KEEP_ALIVE=24h
OLLAMA_MAX_LOADED_MODELS=2
WORKBENCH_PORT=8000
WORKBENCH_HOST=127.0.0.1
MODEL_REGISTRY_PATH=config/model_registry.yaml

# Air-gap offline flags
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_DATASETS_OFFLINE=1
```

### Step 4: Pull Model Weights via Ollama
Ensure the Ollama daemon is running (`ollama serve`), then pull the four specialized models:
```powershell
# 1. Pinned Resident Classifier Router (~1.0 GB)
ollama pull qwen3.5:0.8b

# 2. General Reasoning & Document Synthesis Worker (~3.4 GB)
ollama pull qwen3.5:4b

# 3. Multimodal Vision & Diagram Specialist (~3.2 GB)
ollama pull qwen2.5vl:3b

# 4. Sandboxed Code Generation Specialist (~4.7 GB)
ollama pull qwen2.5-coder:7b
```

### Step 5: Launch the Workbench
```powershell
# Run with Python module syntax (ensures src/ is in PYTHONPATH)
python -c "import sys; sys.path.insert(0, 'src'); import uvicorn; uvicorn.run('workbench.main:app', host='127.0.0.1', port=8000, reload=True)"
```
Or directly with Uvicorn:
```powershell
$env:PYTHONPATH="src"
uvicorn workbench.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 6: Access the Web Console
Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

---

## 6. Sample Queries & Operational Directives

### Sample 1: Knowledge Base Synthesis & Word Report (`.docx`)
> **Route**: `qwen3.5:4b` + Local Vector RAG + `render_docx`
```text
Review the technical specifications for Kirloskar End Suction Pumps from the local knowledge base. Summarize the permissible operating head range, casing design pressures, discharge nozzle sizes, and maintenance inspection protocols. Synthesize all findings into a structured technical summary with tables for executive approval.
```

### Sample 2: Excel Tabular Extraction (`.xlsx`)
> **Route**: `qwen3.5:4b` + Local Vector RAG + `edit_spreadsheet`
```text
Extract all pump operating parameters, flow capacities, and head ratings from the equipment manuals into an Excel spreadsheet with clean tabular columns for the engineering department.
```

### Sample 3: Optical Tag Inspection & Multimodal Vision
> **Route**: `qwen2.5vl:3b` + CPU EasyOCR + Visual Document Analyzer
```text
Perform an optical and engineering inspection on the attached pump schematic. Identify all marked nozzle connections, extract visible equipment tag numbers, verify the impeller dimensional labels, and highlight any anomalies or operating limit warnings shown in the drawing.
```

### Sample 4: Sandboxed Code Calculation & Vibration Analysis
> **Route**: `qwen2.5-coder:7b` + Subprocess Sandbox (`run_code`)
```text
Write and execute a Python script to compute the Fast Fourier Transform (FFT) on the pump bearing vibration dataset, detect the peak defect frequencies, and verify compliance with ISO 10816-3 vibration severity limits.
```

---

## 7. Verification & Automated Test Suite

The test suite validates path sandboxing, tool execution, model isolation, CPU OCR guarantees, and API endpoints:
```powershell
# Run all tests with pytest
python -m pytest tests/ -v
```

Expected output:
```text
tests/test_api.py::test_health_endpoint PASSED                           [  7%]
tests/test_api.py::test_models_registry_endpoint PASSED                  [ 15%]
tests/test_api.py::test_hardware_telemetry_endpoint PASSED               [ 23%]
tests/test_api.py::test_network_audit_endpoint PASSED                    [ 30%]
tests/test_api.py::test_kb_list_endpoint PASSED                          [ 38%]
tests/test_api.py::test_deliverables_list_endpoint PASSED                [ 46%]
tests/test_workbench.py::test_safe_path_resolution PASSED                [ 53%]
tests/test_workbench.py::test_async_tool_execution PASSED                [ 61%]
tests/test_workbench.py::test_model_tag_isolation PASSED                 [ 69%]
tests/test_workbench.py::test_registry_bidirectional_task_matching PASSED [ 76%]
tests/test_workbench.py::test_shared_embedding_singleton PASSED          [ 84%]
tests/test_workbench.py::test_ocr_engine_cpu_guarantee PASSED            [ 92%]
tests/test_workbench.py::test_kb_query PASSED                            [100%]

============================= 13 passed in ~45s ==============================
```

---

## 8. Directory Structure

```
workbench/
├── .env.example              # Template environment configuration
├── .gitignore                # Production ignore rules (temporary files, indices, weights)
├── README.md                 # Core system documentation and architecture guide
├── requirements.txt          # Python runtime dependencies
├── config/
│   └── model_registry.yaml   # Single source of truth for models, roles, and context budgets
├── data/
│   ├── kb/                   # Local knowledge base documents (.pdf, .md, .txt)
│   ├── uploads/              # Local uploaded drawings and files for air-gapped processing
│   └── kb_index.json         # Persisted CPU vector embeddings index
├── output/                   # Generated reports and deliverables (.docx, .pptx, .xlsx)
├── src/
│   └── workbench/
│       ├── api/              # FastAPI REST endpoints and Pydantic schemas
│       │   └── routes.py     # Health, models, routing, telemetry, KB, deliverables
│       ├── models/           # Model client and registry loaders
│       │   ├── ollama_client.py # Async Ollama API wrapper with VRAM memory tracking
│       │   └── registry.py   # Registry loader with task matching and default fallback
│       ├── orchestrator/     # Autonomous ReAct agent and deliverable engine
│       │   └── agent.py      # ReAct loop, 50s timeout guard, fallback extractor, deliverable compiler
│       ├── rag/              # CPU embeddings and local vector similarity index
│       │   ├── embeddings.py # CPU-only SentenceTransformers singleton
│       │   └── knowledge_base.py # In-memory cosine search and incremental indexer
│       ├── router/           # Dynamic task classification engine
│       │   ├── classifier.py # 15ms CPU Semantic Classifier & 0.8B LLM classifier
│       │   └── router.py     # Multimodal override, task hints, and model resolution
│       ├── sandbox/          # Isolated code execution engine
│       │   └── executor.py   # Subprocess / Docker sandbox with network isolation guard
│       ├── static/           # Front-end console cockpit
│       │   ├── index.html    # 3-screen SPA layout (Workspace, KB & SOPs, Trust & Audit)
│       │   ├── app.js        # Dynamic UI controllers, polling, live ReAct trace, audit table
│       │   └── style.css     # High-contrast Blueprint Dark and Light design system
│       ├── tools/            # Native tool implementations
│       │   ├── base.py       # Path confinement and tool definition schemas
│       │   ├── code_tools.py # run_code tool binding
│       │   ├── doc_tools.py  # render_docx, render_pptx, edit_spreadsheet, render_markdown_to_xlsx
│       │   ├── file_tools.py # read_file, write_file, list_directory
│       │   ├── kb_tools.py   # search_kb tool binding
│       │   └── vision_tools.py # ocr_image, analyze_visual_document
│       ├── vision/           # Optical character recognition and layout analysis
│       │   └── ocr_engine.py # EasyOCR + OpenCV pipeline with 0-CUDA guarantee
│       └── main.py           # FastAPI application entry point with static file mounting
└── tests/
    ├── test_workbench.py     # Unit tests (path sandboxing, tool execution, model isolation)
    └── test_api.py           # Integration tests (health, hardware telemetry, network audit)
```

---

## 9. Air-Gap Security & Network Isolation Proof

The workbench strictly enforces offline operation across all architectural tiers:

1. **Environment Air-Gap Enforcement**:
   - `HF_HUB_OFFLINE=1`: Disables HuggingFace Hub network checks.
   - `TRANSFORMERS_OFFLINE=1`: Enforces local-only transformer weights.
   - `HF_DATASETS_OFFLINE=1`: Blocks dataset remote fetching.
2. **Subprocess Network Isolation**:
   - Sandboxed code execution sets environment flags that prohibit outbound sockets.
   - Docker sandbox mode enforces `--network none`.
3. **Live Kernel Socket Auditor**:
   - The `/system/network-audit` endpoint performs a process-tree socket inspection on every cycle.
   - Verifies that all open sockets are bound strictly to `127.0.0.1` (loopback) or `0.0.0.0`.
   - Any external outbound socket connection immediately triggers an audit violation warning.
4. **Confined Path Sandboxing**:
   - All filesystem operations are verified against `WORKSPACE_ROOT` via `resolve_safe_path()`.
   - Directory traversal attempts (e.g. `../../etc/passwd`) are blocked with a `PermissionError`.

---

## 10. Repository & Contribution

- **GitHub Repository**: [https://github.com/vedantkamtikar/On-Prem-Agentic-Workbench](https://github.com/vedantkamtikar/On-Prem-Agentic-Workbench)
- **Author**: Vedant Kamtikar
- **License**: MIT
