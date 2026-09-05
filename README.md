# RAG-RuleSync V2

RAG-RuleSync is an enterprise Design-for-Manufacturability (DFM) rule extraction and formalisation pipeline built for HCL Technologies. It ingests unstructured PDF manufacturing specifications and outputs structured CAD-ready constraints in the **BucketList `format1.json` schema** required by HCL's downstream CAD compliance toolchain.

The system is structured into two core parts:
1. **Part 1: Extraction Engine (`core_v2/`)** — Layout-aware PDF parsing, sliding window generation, local dense vector anchor classification (filtering ~80% of boilerplate on CPU), and verbatim LLM structuring with SQLite `TruthStore` provenance.
2. **Part 2: Formalisation Pipeline — Version 3 (`dfm_rule_pipeline/taxonomy/`)** — 6-tier taxonomy engine converting rule sentences into CAD-ready nested `format1.json` BucketList objects with 17-check deterministic validation and targeted self-repair.

For the authoritative architectural deep-dive, known risks, and future roadmap, see **[Handover_Report_RAG_RuleSync_Final.md](Handover_Report_RAG_RuleSync_Final.md)**.

---

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

After installation, download the required spaCy language model (used for sentence-boundary detection in `core_v2/`):

```bash
python -m spacy download en_core_web_sm
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# Comma-separated Groq API keys for automatic round-robin rotation
GROQ_API_KEYS=gsk_key1,gsk_key2,gsk_key3

# Or a single key
GROQ_API_KEY=gsk_your_key_here

# Model selection (default: openai/gpt-oss-20b)
# LLM_MODEL=openai/gpt-oss-20b
# LLM_MAX_TOKENS=4096
```

### 3. Running the System

#### Option 1: FastAPI Backend (Primary)

Runs the production REST API:

```bash
uvicorn app:app --reload --port 8000
```

- API Base: `http://localhost:8000`
- Interactive Swagger UI: `http://localhost:8000/docs`

Key endpoints:
| Endpoint | Method | Pipeline Stage | Description |
|---|---|---|---|
| `POST /upload-document` | `multipart/form-data` | **Part 1: Extraction** | Ingests PDF → returns Level-1 extracted verbatim rules |
| `POST /process-rules-taxonomy` | `application/json` | **Part 2: V3 Formalisation** | Formalises rules into nested `format1.json` BucketList structures |
| `POST /process-rules` | `application/json` | Legacy Formalisation | Generates flat CAD equations (kept for backward compatibility) |

#### Option 2: React Frontend SPA

A modern React 18 / Vite SPA is located in `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies API calls to `http://localhost:8000`.

---

## Output Formats

### Part 1: Extracted Rules (`POST /upload-document`)
```json
[
  {
    "rule_text": "Distance between bridges should be at least 4.5 times sheet thickness",
    "resolved_rule_text": "Distance between bridges should be at least 4.5 times sheet thickness",
    "source_window_ids": ["win_0042"]
  }
]
```

### Part 2: Version 3 Formalised `format1.json` (`POST /process-rules-taxonomy`)
```json
{
  "rule_text": "Distance between bridges should be at least 4.5 times sheet thickness",
  "status": "Success",
  "decision_code": "formalized",
  "domain": "SheetMetal",
  "bucket": "DistanceRule",
  "taxonomy_rules": [
    {
      "Name": "Bridge Spacing Requirement",
      "RuleCategory": "SheetMetal",
      "Results": "Validation",
      "RuleType": "Feature",
      "Feature1": "Distance",
      "Object1": "Bridge",
      "Object2": "Bridge",
      "Constraints": {
        "FilterParamList": [{"ExpName": "", "Operator": [""], "Value": [""]}],
        "ConditionParamList": [{"ExpName": "", "Operator": [[""]], "Value": [[[""]]]}],
        "ValidationParamList": [
          {
            "ExpName": "Distance.MinValue",
            "Operator": [[">="]],
            "Value": [[["4.5*SheetMetal.Thickness"]]],
            "AllowedParams": ["SheetMetal.Thickness"]
          }
        ],
        "AdditionalParamList": [{"ExpName": ""}],
        "UserParamList": [{"ParamName": "", "DisplayName": "", "Value": [""], "MinValue": "", "MaxValue": ""}]
      }
    }
  ]
}
```

---

## Project Structure

```
RAG-RuleSync/
├── app.py                          # FastAPI REST application
├── requirements.txt                # Python dependencies
├── .env                            # API keys (not committed)
│
├── core_v2/                        # PART 1: Document Extraction Engine
│   ├── parser.py                   # PyMuPDF layout-aware block extraction
│   ├── truth_store.py              # SQLite immutable rule provenance store
│   ├── windower.py                 # spaCy sentence windowing with overlap
│   ├── embeddings.py               # Local CPU sentence-transformers embeddings
│   ├── vector_store.py             # FAISS dense vector similarity index
│   ├── dfm_anchors.py              # Cosine anchor classifier (pre-LLM filter)
│   ├── candidate_assembler.py      # Candidate block grouping & context assembly
│   └── llm_structurer.py           # Verbatim LLM rule extraction
│
├── dfm_rule_pipeline/              # PART 2: Formalisation Pipeline
│   ├── taxonomy/                   # CANONICAL VERSION 3 FORMALISATION ENGINE
│   │   ├── service.py              # TaxonomyFormalizationService orchestrator
│   │   ├── bucket_classifier.py    # 3-tier bucket & domain classifier
│   │   ├── bucket_registry.py      # 9 BucketList definitions & exemplars
│   │   ├── prompt_context.py       # Dynamic context prompt builder
│   │   ├── llm_extractor.py        # Flat intermediate LLM extractor
│   │   ├── assembler.py            # format1 JSON deterministic assembler
│   │   ├── validator.py            # 17-check deterministic schema validator
│   │   ├── repair.py               # Targeted error repair loop
│   │   ├── schema_registry.py      # Schema registry interface
│   │   └── schema_registry.json    # 12-domain feature/attribute database (22 KB)
│   ├── llm/                        # Multi-key round-robin Groq client
│   ├── schema/                     # 12-domain feature definitions
│   └── stages/, ast_engine/        # Legacy auxiliary modules (backward compat)
│
├── frontend/                       # React 18 / Vite Single Page Application
│   ├── src/App.jsx                 # Dashboard interface
│   └── vite.config.js              # Proxy configuration
│
└── tests/                          # Test Suites (11 files)
```

---

## Documentation Index

| Document | Description |
|---|---|
| **[Handover_Report_RAG_RuleSync_Final.md](Handover_Report_RAG_RuleSync_Final.md)** | Definitive Technical & Stakeholder Handover Report |
| **[Project_description.md](Project_description.md)** | High-level architectural overview |
| **[rule-taxonomy_bucketlist_format.md](rule-taxonomy_bucketlist_format.md)** | Specification of the `format1.json` BucketList schema |
| **[Ground-truth.csv](Ground-truth.csv)** | 110-rule annotated ground truth dataset |
