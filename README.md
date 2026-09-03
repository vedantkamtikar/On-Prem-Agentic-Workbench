# Sovereign On-Prem Agentic AI Workbench

An air-gapped, self-hosted, multi-model agentic AI workbench built for confidential industrial knowledge work. Engineered specifically for on-premise deployment on standard engineering laptop and workstation hardware (**NVIDIA GeForce RTX 4050 6GB VRAM, AMD Ryzen 7 7435HS, 24GB System RAM**).

---

## 1. Problem & Architectural Rationale

Refineries, power plants, manufacturing facilities, and defense institutions generate routine, high-stakes technical work: scanned equipment manuals, P&ID schematics, vibration sensor logs, vendor bids, and executive approval notes.

- **The Confidentiality Bottleneck**: Commercial cloud AI APIs are strictly prohibited due to trade-secret and intellectual property security policies.
- **The Sovereign Solution**: A self-hosted, autonomous agent that runs 100% locally inside an air-gapped operating system boundary.
- **Zero Cloud Footprint**: Outbound WAN requests are blocked at the OS kernel level; all inference, OCR, and vector embeddings execute strictly on-premise with zero external socket activity.

---

## 2. System Architecture

```
                                 [ Web Console / Engineering Cockpit ]
                                                   │
                                                   ▼
                                       [ FastAPI Backend Server ]
                                                   │
                                                   ▼
                                     [ LangGraph ReAct Orchestrator ]
                                                   │
                ┌──────────────────────────────────┼──────────────────────────────────┐
                ▼                                  ▼                                  ▼
    [ Dynamic Model Router ]             [ Sandboxed Tool Suite ]           [ Grounded Local RAG ]
    (config/model_registry.yaml)         (Docker / CPU Engines)             (all-MiniLM-L6-v2 CPU)
                │                                  │                                  │
    ┌───────────┴───────────┐            ┌─────────┴─────────┐              ┌─────────┴─────────┐
    ▼                       ▼            ▼                   ▼              ▼                   ▼
[Pinned Classifier]  [Worker Pool]   [CPU EasyOCR]    [Subprocess Sandbox] [Plant SOP Store] [Vector Index]
 Qwen3.5-0.8B        Qwen2.5-VL-3B   (CPU Thread)     (Air-Gap Guarded)    (data/kb/*.pdf,   (Cosine Sim /
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
| **Model Router** | `Qwen3.5-0.8B` | GPU (CUDA) | **~1.0 GB** | **Pinned Resident** (`keep_alive: 24h`) |
| **Vision & Diagram Specialist** | `Qwen2.5-VL-3B` (`qwen2.5vl:3b`) | GPU (CUDA) | **~3.2 GB** (at `num_ctx: 4096`) | Active Worker / Cached in RAM |
| **General Reasoning & Drafting** | `Qwen3.5-4B` (`qwen3.5:4b`) | GPU (CUDA) | **~3.4 GB** (at `num_ctx: 4096`) | Active Worker / Cached in RAM |
| **Coding Specialist** | `Qwen2.5-Coder-7B` (`qwen2.5-coder:7b`) | GPU (CUDA) | **~4.7 GB** (at `num_ctx: 4096`) | Standby / Swapped on demand |
| **OCR Preprocessing** | `EasyOCR` + `OpenCV` | **CPU Only** | **0.0 GB** | CPU Worker Thread |
| **RAG Embeddings** | `all-MiniLM-L6-v2` | **CPU Only** | **0.0 GB** | CPU Worker Thread |

### Memory Invariants & Stability Rules
- **6GB VRAM Ceiling**: Peak combined memory is bounded at **~4.4 to 5.7 GB (Worker + 0.8B Router)**, maintaining safe operating headroom on a 6GB laptop GPU.
- **Max 2 Models in VRAM**: At any given time, only the resident router (`0.8b`) and exactly **one** active worker model occupy GPU memory. Inactive workers are cached in the 24GB system RAM for fast PCIe hot-swaps (~1.5s).
- **`num_ctx: 4096` Context Envelope**: Tuned for optimal performance, allowing extensive tool schemas, user prompts, and multi-chunk RAG document retrievals without token truncation or VRAM overflow.
- **Strict CPU Offloading**: OCR and semantic embeddings execute strictly on CPU cores, reserving 100% of GPU VRAM for LLM inference.

---

## 4. Key Capabilities & Features

1. **3-Screen Streamlined Cockpit**:
   - **Workspace (Screen 1)**: Operations hub with quick presets, intelligent file dropzone with inline OCR tag inspector, live ReAct trace with step timers, clipboard utilities, and real-time deliverables history.
   - **Knowledge Base & SOPs (Screen 2)**: CPU vector similarity search across documents in `data/kb/` with relevance scoring, chunk metadata, and one-click re-indexing.
   - **System Trust & Audit (Screen 3)**: Live VRAM/RAM gauges, model pool status, and real-time network socket audit verifying **100% loopback sockets (`127.0.0.1`) and 0 WAN egress**.
2. **Dynamic Deliverable Synthesis**:
   - Automatically parses user intent and generates custom-named Microsoft Word (`.docx`), PowerPoint (`.pptx`), and Excel (`.xlsx`) deliverables based on query context (e.g. `Kirloskar_Pump_Specification_Report.docx`, `Turbine_Compliance_Report.docx`).
   - Formats technical findings with structured headings, parameters, bulleted checklists, and markdown tables.
3. **Multimodal Vision & Diagram Analysis**:
   - CPU-only OCR extraction coupled with `Qwen2.5-VL-3B` vision understanding for P&ID schematics, engineering drawings, and scanned test certificates.
4. **Light & Dark Theme Engine**:
   - Instant toggle with system blueprint aesthetics, high-contrast typography (WCAG AA/AAA compliant), and zero-flash local storage persistence.

---

## 5. Quickstart & Setup

### Prerequisites
- Windows 10/11 or Linux
- NVIDIA GPU (6GB+ VRAM recommended, e.g. RTX 4050 / 3060 / 4060)
- Python 3.10+ (Conda environment recommended: `aiml`)
- [Ollama](https://ollama.com/) installed locally

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Pull Required Model Weights
```powershell
ollama pull qwen3.5:0.8b
ollama pull qwen2.5vl:3b
ollama pull qwen3.5:4b
ollama pull qwen2.5-coder:7b
```

### Step 3: Start the Ollama Daemon
```powershell
ollama serve
```

### Step 4: Launch the Workbench Backend & UI
```powershell
cd c:\Users\LOQ\Desktop\workbench
conda activate aiml
python -c "import sys; sys.path.insert(0, 'src'); import uvicorn; uvicorn.run('workbench.main:app', host='127.0.0.1', port=8000, reload=True)"
```

### Step 5: Open Web Console
Navigate to:
```
http://127.0.0.1:8000/
```

---

## 6. Sample Queries

### Sample 1: Knowledge Base Synthesis & .DOCX Report
> **Route**: `qwen3.5:4b` + Local Vector RAG
```text
Review the technical specifications for Kirloskar End Suction Pumps from the local knowledge base. Summarize the permissible operating head range, casing design pressures, discharge nozzle sizes, and maintenance inspection protocols. Synthesize all findings into a structured technical summary with tables for executive approval.
```

### Sample 2: Optical Tag Inspection & Vision Analysis
> **Route**: `qwen2.5vl:3b` + CPU OCR Engine
```text
Perform an optical and engineering inspection on the attached pump schematic. Identify all marked nozzle connections, extract visible equipment tag numbers, verify the impeller dimensional labels, and highlight any anomalies or operating limit warnings shown in the drawing.
```

---

## 7. Verification & Test Suite

Run the automated integration and unit test suite:
```powershell
pytest tests/ -v
```

---

## 8. Directory Structure

```
workbench/
├── .env                  # Environment, offline mode flags, and hardware variables
├── README.md             # Core system documentation and architecture guide
├── requirements.txt      # Python runtime dependencies
├── config/
│   └── model_registry.yaml   # Single source of truth for models, roles, and VRAM budgets
├── data/
│   ├── kb/               # Local knowledge base documents (.pdf, .md, .txt)
│   ├── uploads/          # Local uploaded drawings and files for air-gapped processing
│   └── kb_index.json     # Persisted CPU vector embeddings index
├── output/               # Generated reports and deliverables (.docx, .pptx, .xlsx)
├── src/
│   └── workbench/
│       ├── api/          # FastAPI REST endpoints and Pydantic schemas
│       ├── models/       # Ollama async client and model registry loader
│       ├── orchestrator/ # LangGraph ReAct agent loop and dynamic deliverable engine
│       ├── rag/          # CPU embeddings and local vector similarity index
│       ├── router/       # Dynamic task classifier (LLM + CPU embedding fallback)
│       ├── sandbox/      # Isolated code execution engine with network isolation guard
│       ├── static/       # Console UI (HTML5, Vanilla CSS, SPA JavaScript)
│       ├── tools/        # Native tool implementations (DOCX, PPTX, XLSX, OCR, KB)
│       ├── vision/       # CPU EasyOCR and multimodal vision analyzer
│       └── main.py       # FastAPI application entry point
└── tests/
    ├── test_workbench.py # Unit tests (path sandboxing, tool execution, model isolation)
    └── test_api.py       # Integration tests (health, hardware telemetry, network audit)
```

---

## 9. Air-Gap Security & Network Isolation Proof

The workbench strictly enforces offline operation via environment flags and socket auditing:
- `HF_HUB_OFFLINE=1`
- `TRANSFORMERS_OFFLINE=1`
- `HF_DATASETS_OFFLINE=1`
- Sandboxed Subprocess: Socket creation blocked via internal network guard.
- Live socket monitor continuously verifies **100% loopback (`127.0.0.1`) connections and 0 external WAN calls**.
