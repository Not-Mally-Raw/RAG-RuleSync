# HCL DFM Rule Extraction — Comprehensive Handover & Technical Report
### RAG-RuleSync V2 with Version 3 Formalisation Engine | Technical & Stakeholder Reference

---

> **Document Purpose:** This report serves as the complete, authoritative handover document for the incoming engineering team, project stakeholders, and HCL Technologies. It documents the full current state of RAG-RuleSync, establishing a clean, unified architecture consisting of **Part 1: Document Extraction Engine (`core_v2/`)** and **Part 2: Version 3 Rule Formalisation Pipeline (`dfm_rule_pipeline/taxonomy/`)**. It catalogues technical choices, known risks and mitigations, production API endpoints, future roadmap items, and a proposed agentic architecture for subsequent phases.
>
> **Predecessors:** This report builds upon and supersedes prior documentation, including the [Phase-3-Final → RAG-RuleSync handover](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/Handover_Report_Phase3_to_RAG_RuleSync.md) and the FaceVault-style [structural reference](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/Handover_report.md).

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Overview & System Scope](#2-project-overview--system-scope)
3. [System Architecture — Two-Part Core Breakdown](#3-system-architecture--two-part-core-breakdown)
   - 3.1 High-Level Architecture
   - 3.2 Part 1: Document Extraction Engine (`core_v2/`)
   - 3.3 Part 2: Version 3 DFM Rule Formalisation Pipeline (`dfm_rule_pipeline/`)
   - 3.4 API Layer (`app.py`) & Endpoints
   - 3.5 Frontend SPA (`frontend/`)
   - 3.6 Repository File Structure
4. [Evolution & System Generations](#4-evolution--system-generations)
   - 4.1 Generation Comparison (Gen 1 → Gen 2 → Current Gen 3)
   - 4.2 Key Architectural Advances in the Current System
5. [In-Depth: The Version 3 Formalisation Pipeline](#5-in-depth-the-version-3-formalisation-pipeline)
   - 5.1 6-Tier Pipeline Workflow
   - 5.2 The 17-Check Deterministic Validator
   - 5.3 Targeted LLM Self-Repair
   - 5.4 Paragraph Segmentation & Anaphora Handling
   - 5.5 Multi-Key Round-Robin Rotation
6. [Known Risks & Critical Limitations](#6-known-risks--critical-limitations)
7. [Technology Stack & Architectural Justifications](#7-technology-stack--architectural-justifications)
8. [Pipeline Results & Output Formats](#8-pipeline-results--output-formats)
9. [Development Milestones Timeline](#9-development-milestones-timeline)
10. [Future TODO Roadmap](#10-future-todo-roadmap)
11. [Proposed Agentic Architecture for Future Scaling](#11-proposed-agentic-architecture-for-future-scaling)
12. [Glossary of Engineering Terms](#12-glossary-of-engineering-terms)

---

## 1. Executive Summary

RAG-RuleSync is an enterprise Design-for-Manufacturability (DFM) rule extraction and formalisation pipeline built for HCL Technologies. The system ingests unstructured manufacturing specification documents (PDFs) and transforms natural language manufacturing guidelines into structured, CAD-ready rule constraints matching HCL's **BucketList (`format1.json`) schema**.

### The Two-Part Architecture

To eliminate historical confusion between overlapping stages, the current repository is organized into two distinct, sequential macro-components:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  PART 1: Extraction Engine (core_v2/)                                        │
│  Layout-Aware Parsing → Sliding Windows → Local Vector Anchor Filtering     │
│  → Verbatim LLM Structuring + Context Resolution (SQLite TruthStore Provenance)│
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ Extracted & Resolved Rule Sentences
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  PART 2: Formalisation Pipeline — Version 3 (dfm_rule_pipeline/taxonomy/)   │
│  Bucket Classification → Dynamic Schema Context → LLM Extraction             │
│  → Deterministic Assembly → 17-Check Validation → Targeted Error Repair      │
│  Output: Strict CAD-Ready Nested BucketList JSON (format1.json)              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### System Generations Overview

| Generation | Codename | Core Approach | Output Format |
|---|---|---|---|
| **Gen 1** | Phase-3-Final | Supervised ML (5 fine-tuned HuggingFace models) + manual human workflow | Unvalidated raw JSON |
| **Gen 2** | RAG-RuleSync V1 | Brute-force Mega-Prompt LLM chunking + 4-stage refinement | Flat equation CSV (`ExpName/Operator/Recom`) |
| **Gen 3** | **RAG-RuleSync Current** | **Part 1 (`core_v2`) + Part 2 Version 3 (`dfm_rule_pipeline/taxonomy`)** | **Deeply-nested CAD BucketList (`format1.json`)** |

> **Key Takeaway for Stakeholders:** The current system delivers end-to-end automation from raw PDF text directly into the exact nested JSON specification required by HCL's CAD compliance tools. It eliminates ~80% of unnecessary LLM token expenditure through local vector pre-filtering and includes deterministic validation and targeted self-repair.

---

## 2. Project Overview & System Scope

### What the System Solves

Manufacturing organizations maintain hundreds of pages of engineering design standards across multiple domains (Sheet Metal, Injection Molding, Milling, Turning, Drilling, Die Casting, Assembly, etc.). Manually interpreting these standards into CAD compliance rules is slow, error-prone, and expensive. RAG-RuleSync automates this translation.

### What the System Covers

- **Layout-Aware PDF Ingestion:** Extracts text blocks while preserving section hierarchy and titles.
- **Local Anchor Pre-Filtering:** Embeds text windows using local CPU embeddings (`all-MiniLM-L6-v2`) and compares against DFM anchors via FAISS, filtering ~80% of non-rule boilerplate without cloud API costs.
- **Verbatim Rule Extraction with Provenance:** SQLite `TruthStore` guarantees exact character provenance; LLM resolves missing subjects from section headers.
- **Version 3 Taxonomy Formalisation:** Translates plain-English rules into 9 structural buckets (`SimpleValidation`, `RangeValidation`, `ConditionalValidation`, `DistanceRule`, `SetMembership`, etc.) matching domain feature schemas.
- **Deterministic 17-Check Validation:** Validates schema roots, attributes, variable references, boolean states, and array dimensions before output generation.
- **Targeted Self-Repair:** Re-prompts the LLM with precise error diagnostics when schema mismatches occur.
- **Production REST API:** FastAPI backend exposing extraction and formalisation endpoints.

### Explicit Non-Goals & Boundaries

- **Table & Drawing Extraction:** Rules embedded exclusively inside graphical engineering drawings or complex PDF tables are not captured.
- **Streaming Execution:** The system operates in batch mode per document.
- **Multi-Tenant Authentication:** The API currently operates without authentication middleware (intended for internal secure network deployment).

---

## 3. System Architecture — Two-Part Core Breakdown

### 3.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                               CLIENT LAYER                                   │
│            React / Vite Single Page Application (frontend/)                  │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ HTTP REST (JSON / Multipart)
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                                API LAYER                                     │
│             FastAPI Backend (app.py) · CORS Enabled · Uvicorn                │
│                                                                              │
│  POST /upload-document              POST /process-rules-taxonomy (Canonical)  │
│  (Triggers Part 1 Extraction)       (Triggers Part 2 Version 3 Formalisation)│
└──────────┬───────────────────────────────────────────┬───────────────────────┘
           │                                           │
           ▼                                           ▼
┌──────────────────────────────────────┐ ┌─────────────────────────────────────┐
│ PART 1: EXTRACTION ENGINE (core_v2/) │ │ PART 2: V3 FORMALISATION PIPELINE   │
│                                      │ │ (dfm_rule_pipeline/taxonomy/)       │
│ • LayoutAwareParser (PyMuPDF)        │ │                                     │
│ • TruthStore (SQLite Provenance)     │ │ • BucketClassifier (Tier 0)         │
│ • SlidingWindowGenerator (spaCy)     │ │ • PromptContextBuilder (Tier 1)     │
│ • EmbeddingManager (MiniLM CPU)      │ │ • LLMExtractor (Tier 2)             │
│ • VectorStore (FAISS Index)          │ │ • TaxonomyAssembler (Tier 3)        │
│ • DFMAnchorClassifier (0.25 Gate)    │ │ • TaxonomyValidator 17-Check(Tier 4)│
│ • CandidateAssembler (Block Grouping)│ │ • TaxonomyRepair Loop (Tier 5)      │
│ • LLMStructurer (Verbatim Extract)   │ │                                     │
└──────────────────────────────────────┘ │ Shared Infrastructure:              │
                                         │ • LLMClient (Round-Robin Groq)      │
                                         │ • schema_registry.json (12 Domains) │
                                         │ • Legacy Fallbacks (stages/, ast/)  │
                                         └─────────────────────────────────────┘
```

---

### 3.2 Part 1: Document Extraction Engine (`core_v2/`)

Part 1 is responsible for taking raw unstructured PDF files and producing clean, verbatim rule sentences with resolved contextual subjects.

| Module | File | Responsibility & Design Rationale |
|---|---|---|
| **Parser** | [`core_v2/parser.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/parser.py) | `LayoutAwareParser` parses PDF blocks using PyMuPDF, extracting paragraphs, lists, and headings, tagging each text block with its hierarchical `section_title`. |
| **Truth Store** | [`core_v2/truth_store.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/truth_store.py) | Temporary SQLite database (`TruthStore`) storing immutable character records of every block and window. Guarantees 100% provenance back to source text. |
| **Windower** | [`core_v2/windower.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/windower.py) | `SlidingWindowGenerator` splits blocks into overlapping windows using spaCy's sentence tokenizer to prevent cutting engineering abbreviations (e.g., `0.5 mm`, `1.2 in.`). |
| **Embeddings** | [`core_v2/embeddings.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/embeddings.py) | `EmbeddingManager` generates 384-dimensional dense vectors locally on CPU using `all-MiniLM-L6-v2` at zero API cost. |
| **Vector Store** | [`core_v2/vector_store.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/vector_store.py) | `VectorStore` builds an in-memory FAISS flat index for sub-millisecond similarity queries. |
| **Anchor Classifier** | [`core_v2/dfm_anchors.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/dfm_anchors.py) | `DFMAnchorClassifier` scores window vectors against known manufacturing rule exemplars. Windows falling below cosine threshold (0.25) are discarded, eliminating ~80% of boilerplate. |
| **Candidate Assembler** | [`core_v2/candidate_assembler.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/candidate_assembler.py) | Groups surviving candidate windows by parent `block_id`, reconstructing full unfragmented paragraphs and attaching section metadata. |
| **LLM Structurer** | [`core_v2/llm_structurer.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/llm_structurer.py) | Sends assembled text blocks to Groq LLM with strict verbatim extraction instructions and context resolution. |

**Output of Part 1:** A list of `ExtractedRule` objects:
```json
{
  "rule_text": "Distance between bridges should be at least 4.5 times sheet thickness",
  "resolved_rule_text": "Distance between bridges should be at least 4.5 times sheet thickness",
  "source_window_ids": ["win_0012", "win_0013"]
}
```

---

### 3.3 Part 2: Version 3 DFM Rule Formalisation Pipeline (`dfm_rule_pipeline/`)

Part 2 takes rule sentences and transforms them into HCL's CAD-compliant `format1.json` BucketList schema. 

The **Version 3 Engine** (`dfm_rule_pipeline/taxonomy/`) is the canonical implementation of this formalisation process.

#### Version 3 Core Components (`dfm_rule_pipeline/taxonomy/`)

```
dfm_rule_pipeline/taxonomy/
├── service.py             # TaxonomyFormalizationService (Primary Orchestrator)
├── bucket_classifier.py   # Tier 0: 3-Tier Classifier (Regex → Embeddings → LLM)
├── bucket_registry.py     # Definitions of 9 structural rule buckets
├── prompt_context.py      # Tier 1: Dynamic Prompt Context Builder
├── llm_extractor.py       # Tier 2: LLM Flat Extraction Engine
├── assembler.py           # Tier 3: Deterministic Schema Assembler
├── validator.py           # Tier 4: 17-Check Schema & Consistency Validator
├── repair.py              # Tier 5: Targeted LLM Error Repair Loop
├── schema_registry.py     # Registry interface for domain features & attributes
├── schema_registry.json   # 22 KB Knowledge Base of 12 Domain Schemas
├── domain_normalizer.py   # Domain alias & keyword normalizer
└── models.py              # Pydantic schema models (TaxonomyRule, Constraints, etc.)
```

#### Shared Supporting Infrastructure & Pipeline Unification

To avoid code duplication and maintain clean boundaries, the formalisation pipeline utilizes shared infrastructure within `dfm_rule_pipeline/`:

1. **LLM Connection Layer (`dfm_rule_pipeline/llm/client.py`):** Multi-key round-robin Groq client supporting automatic rotation and rate-limit mitigation.
2. **Central Configuration (`dfm_rule_pipeline/config.py`):** Loads `.env` variables (`GROQ_API_KEYS`, `LLM_MODEL = "openai/gpt-oss-20b"`, `EMBEDDING_MODEL = "all-MiniLM-L6-v2"`).
3. **Domain Definitions (`dfm_rule_pipeline/schema/`):** Full technical schemas for 12 manufacturing domains (`Sheetmetal`, `SMForm`, `Injection Moulding`, `Die Cast`, `Drill`, `Mill`, `Turn`, `Assembly`, `Additive`, `Tubing`, `Model`, `General`).
4. **V3 Canonical Architecture (`dfm_rule_pipeline/taxonomy/`):** Designated as the single source of truth for all CAD-ready formalisation. Top-level [`dfm_rule_pipeline/__init__.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/__init__.py) directly exposes the V3 public interface.
5. **Legacy Compatibility Modules (`stages/`, `pipeline.py`, `formatter.py`, `ast_engine/`):** Retained as auxiliary utilities for legacy flat equation formatting (`/process-rules`) and batch CLI execution (`main.py`). All 8 stage modules and `pipeline.py` use clean absolute imports (`from dfm_rule_pipeline...`), eliminating previous fragile `sys.path` injection hacks.

---

### 3.4 API Layer (`app.py`) & Endpoints

[`app.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/app.py) provides a FastAPI application running on Uvicorn.

```python
# Startup event initializes global singletons once
@app.on_event("startup")
def startup_event():
    embedder = EmbeddingManager(model_name=EMBEDDING_MODEL)
    classifier = DFMAnchorClassifier(embedder, threshold=0.25)
    llm_client = LLMClient()
    taxonomy_service = TaxonomyFormalizationService(llm_client=llm_client, embedder=embedder)
```

#### API Endpoints Reference

| Route | Method | Pipeline Stage | Input | Primary Output |
|---|---|---|---|---|
| `/` | `GET` | System Health | None | `{"status": "running", "message": "..."}` |
| `/upload-document` | `POST` | **Part 1 (Extraction)** | `multipart/form-data` (PDF file) | Array of Level-1 `{rule_text, resolved_rule_text, source_window_ids}` |
| `/process-rules-taxonomy` | `POST` | **Part 2 (V3 Formalisation)** | `{"rules": [{"rule_text": "...", "rule_type": "..."}]}` | Array of `TaxonomyResponse` objects containing full `TaxonomyRule` format1 JSON |
| `/process-rules` | `POST` | Legacy Formalisation | `{"rules": [{"rule_text": "...", "rule_type": "..."}]}` | Array of legacy flat CAD math equations (backward compatibility) |

Interactive documentation is served at `http://localhost:8000/docs`.

---

### 3.5 Frontend SPA (`frontend/`)

The repository includes a modern React 18 / Vite Single Page Application located in `frontend/`:

- **Main Component:** [`frontend/src/App.jsx`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/frontend/src/App.jsx) (23.5 KB)
- **Styling & Design System:** [`frontend/src/index.css`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/frontend/src/index.css) (24 KB dark/light theme)
- **Proxy Configuration:** [`frontend/vite.config.js`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/frontend/vite.config.js) proxies API requests to `http://localhost:8000`.

---

### 3.6 Repository File Structure

```
RAG-RuleSync/
├── app.py                             # FastAPI REST application
├── requirements.txt                   # Production Python dependencies
├── README.md                          # Setup, installation, and run guide
├── Handover_Report_RAG_RuleSync_Final.md # This authoritative technical report
├── Project_description.md             # V2 architecture overview
├── rule-taxonomy_bucketlist_format.md # Detailed specification of format1.json
├── Ground-truth.csv                   # 110-rule annotated ground truth
├── Ground-truth.xlsx                  # 107-rule Excel benchmark dataset
│
├── core_v2/                           # PART 1: Extraction Engine (11 files)
│   ├── parser.py                      # PyMuPDF structural layout parser
│   ├── truth_store.py                 # SQLite immutable text provenance store
│   ├── windower.py                    # spaCy sliding window generator
│   ├── embeddings.py                  # Local MiniLM dense embeddings
│   ├── vector_store.py                # FAISS vector similarity index
│   ├── dfm_anchors.py                 # Cosine similarity anchor classifier
│   ├── candidate_assembler.py         # Block-level candidate group reconstruction
│   ├── llm_structurer.py              # LLM verbatim extraction & context resolver
│   ├── extractor.py                   # Extraction facade
│   └── validator.py                   # Conflict & overlap validator
│
├── dfm_rule_pipeline/                 # PART 2: Formalisation Pipeline (V3 & Shared)
│   ├── __init__.py                    # Package init exporting V3 Taxonomy Service
│   ├── config.py                      # Unified environment configuration
│   ├── taxonomy/                      # CANONICAL VERSION 3 FORMALISATION ENGINE
│   │   ├── service.py                 # TaxonomyFormalizationService orchestrator
│   │   ├── bucket_classifier.py       # 3-tier bucket & domain classifier
│   │   ├── bucket_registry.py         # 9 bucket definitions & exemplars
│   │   ├── prompt_context.py          # Dynamic prompt builder
│   │   ├── llm_extractor.py           # LLM extraction to flat intermediate model
│   │   ├── assembler.py               # Deterministic format1 JSON constructor
│   │   ├── validator.py               # 17-check deterministic schema validator
│   │   ├── repair.py                  # Targeted LLM self-repair module
│   │   ├── schema_registry.py         # Schema registry manager
│   │   ├── schema_registry.json       # 12-domain feature/attribute database (22 KB)
│   │   ├── domain_normalizer.py       # Domain string normalizer
│   │   └── models.py                  # Pydantic models for format1 schema
│   │
│   ├── llm/                           # Shared LLM connectivity
│   │   ├── client.py                  # Multi-key round-robin Groq client
│   │   └── prompts.py                 # Legacy prompt definitions
│   ├── schema/                        # Shared 12-domain feature definitions
│   │   ├── features.py                # Domain feature dictionary
│   │   ├── feature_schema.py          # Domain mappings
│   │   └── domain_definitions.py      # Semantic descriptions
│   ├── stages/                        # Legacy 4-stage modules (backward compat)
│   ├── ast_engine/                    # Legacy AST parser (backward compat)
│   ├── pipeline.py                    # Legacy pipeline orchestrator
│   └── formatter.py                   # Legacy CAD normalizer
│
├── frontend/                          # React 18 / Vite Frontend SPA
│   ├── src/App.jsx                    # UI application
│   ├── src/index.css                  # UI styling
│   ├── package.json                   # Node dependencies
│   └── vite.config.js                 # Dev server proxy configuration
│
└── tests/                             # Automated Test Suite (11 files)
    ├── test_taxonomy_engine.py        # V3 formalisation engine tests
    ├── test_bucketlist_coverage.py    # format1.json bucket coverage tests
    ├── test_taxonomy_api.py           # FastAPI endpoint tests
    ├── test_candidate_assembler.py    # Core V2 assembler tests
    ├── test_indexing.py               # FAISS vector store tests
    ├── test_ingestion.py              # PDF parser tests
    ├── test_llm_client_fallback.py    # Round-robin key rotation tests
    └── ...                            # Additional unit tests
```

---

## 4. Evolution & System Generations

### 4.1 Generation Comparison

```
Generation 1 (Phase-3-Final)
  [PDF] ──> [Win32COM / PaddleOCR] ──> [5 Fine-Tuned Models] ──> [Manual UI] ──> Raw JSON
                                                                                    │
Generation 2 (RAG-RuleSync V1)                                                     ▼
  [PDF] ──> [Mega-Prompt (Groq)] ──> [4-Stage Refinement] ──> [AST Engine] ──> Flat CSV
                                                                                    │
Generation 3 (Current: RAG-RuleSync + V3 Taxonomy)                                  ▼
  [PDF] ──> [Layout Parser] ──> [FAISS Anchor Filter] ──> [Verbatim Structurer]
                                                                │
                                                                ▼
                                                [V3 Taxonomy Engine]
                                                [Classifier ──> Assembler ──> 17-Validator ──> Repair]
                                                                │
                                                                ▼
                                                [CAD-Ready format1.json]
```

### 4.2 Key Architectural Advances

| Dimension | Generation 1 (Phase-3-Final) | Generation 2 (RAG-RuleSync V1) | Current Generation 3 |
|---|---|---|---|
| **Extraction Paradigm** | Heavyweight OCR + 5 transformer classifiers | Brute-force LLM mega-prompt on all text | Local dense anchor filtering + verbatim LLM structurer |
| **Pre-LLM Filtering** | None (100% processed by local models) | None (100% sent to cloud LLM) | **~80% non-rule text filtered locally on CPU** |
| **Provenance Tracking** | None | None | **SQLite `TruthStore` with exact window indexing** |
| **Formalisation Engine** | None | 4-Stage classic pipeline (equations) | **Version 3 Taxonomy Engine (6 tiers)** |
| **Output Data Model** | Unvalidated flat JSON | Flat CSV (`ExpName/Operator/Recom`) | **Nested `format1.json` BucketList JSON** |
| **Schema Validation** | None | Stage 4 self-reflection | **17-check deterministic schema validator** |
| **Error Recovery** | None | Generic re-prompting | **Error-code specific targeted repair loop** |
| **Paragraph Logic** | Naive sentence splitting | Naive chunking | **Topic-shift & anaphora continuation detection** |
| **API Architecture** | Monolithic Streamlit UI | Streamlit-only script | **FastAPI REST backend (`app.py`)** |
| **Client UI** | 6-page Streamlit | Single-page Streamlit | **React 18 / Vite Single Page Application** |
| **Rate Limit Handling** | Hardcoded `time.sleep(2)` | Groq → Cerebras failover | **Multi-key round-robin Groq rotation** |

---

## 5. In-Depth: The Version 3 Formalisation Pipeline

### 5.1 6-Tier Pipeline Workflow

The Version 3 pipeline operates across six distinct, deterministic tiers:

```
                      Raw Rule Sentence
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 0: Adaptive Bucket & Domain Classification             │
│ Regex Patterns ──> Embedding Cosine ──> LLM Guesser Fallback│
│ Result: Identified Domain (e.g. Milling) & Bucket (e.g. SimpleValidation)
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: Dynamic Prompt Context Generation                   │
│ Injects relevant schema paths & bucket exemplars into prompt│
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 2: LLM Flat Extraction                                 │
│ LLM outputs flat ExtractionResult intermediate structure    │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 3: Deterministic Schema Assembly                       │
│ TaxonomyAssembler constructs nested TaxonomyRule format1    │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 4: Deterministic 17-Check Schema Validation            │
│ Validates syntax, attribute existence, operators, dimensions│
└────────────────────────────┬────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │ Validation Errors?          │
              ▼ Yes                         ▼ No
┌───────────────────────────────┐  ┌─────────────────────────┐
│ TIER 5: Targeted Repair Loop  │  │ SUCCESS                 │
│ LLM re-prompted with specific │  │ Status: Success         │
│ diagnostic templates          │  │ Decision: formalized    │
│ ──> Re-Assemble ──> Re-Validate│  │ Output: format1 JSON    │
└───────────────────────────────┘  └─────────────────────────┘
```

---

### 5.2 The 17-Check Deterministic Validator

The [`TaxonomyValidator`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/validator.py) guarantees output integrity by enforcing 17 discrete rules:

1. **Mandatory Constraint Lists:** `FilterParamList`, `ConditionParamList`, `ValidationParamList`, `AdditionalParamList`, and `UserParamList` must all exist.
2. **Non-Empty Validation Check:** `ValidationParamList` must contain at least one valid check.
3. **Schema Root Verification:** Features and objects referenced in `ExpName` must exist in `schema_registry.json`.
4. **Schema Attribute Verification:** Attributes must exist on the specified root feature in the domain.
5. **Strict Boolean Typing:** Parameters ending in `.Is...` must use exclusively `"Yes"` or `"No"`.
6. **AllowedParams Declaration:** Any variable referenced in a formula (e.g., `4.5 * SheetMetal.Thickness`) must be explicitly declared in `AllowedParams`.
7. **Branch-to-Value Alignment:** In conditional rules, the number of condition branches must match validation value groups.
8. **Unit Stripping:** Pure numeric constraints must not contain literal unit words (`mm`, `deg`, `inches`).
9. **Distance Object Completeness:** `DistanceRule` buckets must define both `Object1` and `Object2`.
10. **Module Rule Feature Segregation:** `Module` level rules must leave `Feature1/2` and `Object1/2` empty.
11. **Operator Whitelisting:** Operators must belong to `{>=, <=, >, <, =, ANY}`.
12. **Value Dimension Structure:** Nested value array depths must match schema standards (`[[["val"]]]`).
13. **Operator Dimension Structure:** Operator array depths must match schema standards (`[["op"]]`).
14. **Filter Parameter Structure:** Filter parameter values must be flat arrays (`["val"]`).
15. **Additional Parameter Schema Compliance:** `AdditionalParamList` references must be valid schema paths.
16. **User Parameter Bounds:** `UserParamList` min/max bounds must be mathematically consistent.
17. **Dynamic Attribute Discovery:** Automatically flags and registers newly encountered valid engineering attributes.

---

### 5.3 Targeted LLM Self-Repair

When validation errors occur, [`TaxonomyRepair`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/repair.py) avoids generic retry loops. It maps each error code to a targeted correction prompt:

```python
ERROR_REPAIR_TEMPLATES = {
    "schema_attribute_failed": (
        "In the ExpName variable path '{value}', the attribute '{attr}' does not exist for object '{root}' in domain '{domain}'. "
        "Valid attributes for '{root}' are: {options}. Choose the correct attribute."
    ),
    "allowed_params_missing": (
        "The validation value formula '{value}' references variable '{ref}', but '{ref}' was not listed in 'allowed_params'. "
        "Ensure '{ref}' is added to the 'allowed_params' array."
    ),
    "boolean_value_invalid": (
        "Boolean parameters (ending with .Is...) must use ONLY 'Yes' or 'No' as values. You outputted '{value}'."
    )
}
```

---

### 5.4 Multi-Point Segmentation, List Sanitization & Individual Rule Formalisation

A key challenge when connecting Part 1 (PDF Ingestion) to Part 2 (Rule Formalisation) is that raw engineering documents frequently group multiple constraints into bulleted lists, numbered points, or compound text blocks:

- `1. Minimum bend radius should be 1.5 times sheet thickness. 2. Bend relief depth must be at least 2.0 mm.`
- `- Distance between bridges should be at least 4.5t\n- Distance from hole to edge must be at least 2t`
- `• Feature clearance check • Minimum hole spacing`

If treated as a single composite rule, the LLM attempts to squeeze multiple unrelated features into a single rule bucket, triggering validation errors (`distance_object_missing`, duplicate expressions) and failing to formalise.

To address this, the pipeline implements multi-point segmentation and sanitization:

1. **Automatic List & Bullet Splitting (`_split_into_rule_sentences()`):**
   - Automatically detects newline breaks, inline bullet markers (`•`, `-`, `*`, `–`), and numbered prefixes (`1.`, `2.`, `1)`, `2)`).
   - Segments multi-point inputs into individual, atomic rule sentences while stripping distracting list prefixes.
2. **Anaphoric Continuation Preservation:**
   - Heuristically identifies dependent continuation sentences (`"otherwise"`, `"if the material is aluminum, the ratio limit reduces to..."`, `"in that case"`, `"this tolerance applies"`).
   - Preserves conditional branches and tolerance modifications alongside their parent rule rather than splitting them into invalid fragments.
3. **Individual Pipeline Formalisation (`app.py`):**
   - Both `/process-rules-taxonomy` and `/process-rules` pre-segment composite payloads so each constituent rule sentence is routed independently through the 6-tier Taxonomy V3 engine.
   - Each rule receives its own classified domain, structural bucket, validation passes, and individual result card in the frontend UI.
4. **Seamless Frontend Integration (`frontend/src/App.jsx`):**
   - In `sendToBuilder`, moving extracted rules from Document Ingestion into the Compiler automatically splits multi-line rules onto clean individual lines.
   - In `buildPayload`, leading numbering and bullet characters are automatically stripped before dispatching to the API.

---

### 5.5 Multi-Key Round-Robin Rotation

[`LLMClient`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/llm/client.py) rotates across a comma-separated list of Groq keys from `GROQ_API_KEYS`. If a key encounters rate limits (HTTP 429), it automatically cycles to the next key in the pool, multiplying throughput without pipeline stalls.

---

## 6. Known Risks & Critical Limitations

| Risk Level | Issue | Root Cause | Impact | Mitigation Strategy |
|---|---|---|---|---|
| 🔴 **CRITICAL** | **Single-Prompt Extraction Bottleneck** | Tier 2 LLM prompt attempts to extract domain, bucket, objects, and math in one call | Ambiguous or compound rules fail Tier 4 validation and enter repair | Adopt the **Specialist Agent Architecture** detailed in Section 11 |
| 🔴 **CRITICAL** | **No Secondary LLM Provider** | V2 removed Cerebras failover; relies solely on Groq key pool | Exhausting the entire Groq key pool halts extraction | Re-integrate Cerebras / OpenAI-compatible secondary provider in `LLMClient` |
| 🟡 **HIGH** | **Anchor Threshold Brittleness** | Fixed cosine similarity threshold (`0.25`) tuned primarily for Sheet Metal | May over-filter or under-filter on novel manufacturing domains | Implement adaptive per-domain thresholding and report coverage ratios |
| 🟡 **HIGH** | **spaCy Model Installation Dependency** | `en_core_web_sm` is a separate download step not covered by `pip install` | Uninitialized runtime crash if model is not downloaded | Add startup health validation in `app.py` surfacing clear installation commands |
| 🟡 **HIGH** | **Frontend Production Build Missing** | React frontend is configured for Vite dev server (`npm run dev`) | Cannot deploy static frontend assets to staging/production web servers | Add `npm run build` step and configure FastAPI to serve `frontend/dist` |
| 🟡 **HIGH** | **No Automated CI Benchmark Gate** | Ground truth dataset is verified manually rather than in automated CI | Risk of silent formalisation quality regressions on code changes | Implement `test_ground_truth_coverage.py` gating CI on accuracy thresholds |
| 🟢 **MEDIUM** | **Table & Diagram Rule Omission** | Document parser extracts textual blocks only; ignores complex tables | Misses lookup tables and visual callouts | Integrate structured table parsing (`pdfplumber` / `camelot`) in next phase |
| 🟢 **MEDIUM** | **Unrestricted CORS & Open Auth** | `allow_origins=["*"]` configured for dev ease; no API auth header | Security vulnerability if exposed outside private network | Configure restricted origins and add API key authorization header |

---

## 7. Technology Stack & Architectural Justifications

### Active Technologies

| Technology | Role | Justification |
|---|---|---|
| **FastAPI + Uvicorn** | Web Framework | Native async support, high performance, automatic OpenAPI documentation (`/docs`), Pydantic request validation. |
| **PyMuPDF (`fitz`)** | PDF Parsing | Cross-platform, high-speed document layout parsing preserving structural block headers and coordinates. |
| **spaCy (`en_core_web_sm`)** | NLP Tokenization | Reliable sentence boundary detection that respects engineering units (`0.5 mm`, `1.2 in.`). |
| **Sentence-Transformers (`all-MiniLM-L6-v2`)** | Local Dense Embeddings | Runs locally on CPU with zero API costs; generates 384-dimensional embeddings for anchor classification. |
| **FAISS (`faiss-cpu`)** | Vector Similarity Index | Ultra-fast in-memory vector search for local anchor similarity matching. |
| **Groq Cloud API** | Fast LLM Inference | High tokens-per-second inference speed using OpenAI-compatible SDK. |
| **Pydantic v2** | Data Modeling & Validation | Enforces strict typing and data invariants across API models and the nested `TaxonomyRule` schema. |
| **SQLite (Python `sqlite3`)** | Provenance Truth Store | Zero-infrastructure, thread-isolated SQLite database tracking exact character spans of extracted rules. |
| **React 18 + Vite** | Frontend Dashboard | Fast, responsive modern SPA for document upload and rule formalisation inspection. |
| **pytest + pytest-asyncio** | Automated Testing | Comprehensive unit and integration testing of async endpoints, taxonomy rules, and schema validators. |

### Eliminated Legacy Technologies

- **Win32COM / PaddleOCR / DETR:** Eliminated due to Windows platform locking, heavy GPU footprint, and memory leaks.
- **5 Local Fine-Tuned Transformer Models:** Eliminated multi-GB startup downloads in favor of local sentence embeddings + cloud LLM.
- **Qdrant / TF-IDF Extraction Clustering:** Replaced with simpler, faster in-memory FAISS indexing and block-level candidate grouping.

---

## 8. Pipeline Results & Output Formats

### Part 1: Extracted Rule Output (`POST /upload-document`)

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
      "Feature2": "",
      "Object1": "Bridge",
      "Object2": "Bridge",
      "Constraints": {
        "FilterParamList": [
          {
            "ExpName": "",
            "Operator": [""],
            "Value": [""]
          }
        ],
        "ConditionParamList": [
          {
            "ExpName": "",
            "Operator": [[""]],
            "Value": [[[""]]]
          }
        ],
        "ValidationParamList": [
          {
            "ExpName": "Distance.MinValue",
            "Operator": [[">="]],
            "Value": [[["4.5*SheetMetal.Thickness"]]],
            "AllowedParams": ["SheetMetal.Thickness"]
          }
        ],
        "AdditionalParamList": [
          {
            "ExpName": ""
          }
        ],
        "UserParamList": [
          {
            "ParamName": "",
            "DisplayName": "",
            "Value": [""],
            "MinValue": "",
            "MaxValue": ""
          }
        ]
      }
    }
  ],
  "validation_errors": []
}
```

---

## 9. Development Milestones Timeline

```
July 2025: Phase-3-Final Prototype (HuggingFace Classifiers, Win32COM, Manual UI)
   │
Oct 2025: RAG-RuleSync V1 Inception (Prompt-driven extraction, 15-package lean stack)
   │
Jan 2026: Consolidation of Mega-Prompt & 4-Stage Classic Formalisation Pipeline
   │
Apr 2026: Part 1 Core V2 Ingestion (PyMuPDF Layout Parser, TruthStore, FAISS Anchors)
   │
Jun 2026: Part 2 Version 3 Taxonomy Engine Built (9 Buckets, format1.json, 17-Check Validator)
   │
Aug 2026: FastAPI REST backend (app.py), React 18 frontend, Multi-Key Rotation
   │
Sep 2026: Final stabilization, Ground-Truth Validation, Canonical Handover Documentation
```

---

## 10. Future TODO Roadmap

### Phase 1: Immediate Production Readiness (Next Sprint)

1. **Restore Multi-Provider Fallback:** Re-introduce Cerebras / OpenAI-compatible secondary client in `dfm_rule_pipeline/llm/client.py`.
2. **Automated CI Ground Truth Benchmark:** Implement a pytest suite that runs `Ground-truth.csv` through the V3 formalisation endpoint and enforces a minimum 85% success threshold in GitHub Actions.
3. **spaCy Startup Diagnostic:** Add explicit startup verification in `app.py` that raises a human-readable error with installation instructions if `en_core_web_sm` is missing.
4. **CORS & Auth Hardening:** Configure environment-driven allowed origins and API key header authentication.

### Phase 2: Feature & Coverage Expansion

5. **Table Extraction Pipeline:** Integrate `pdfplumber` to detect structured tables and convert matrix rules into atomic `TaxonomyRule` instances.
6. **Dynamic Schema Gap Reporter:** Build an automated reporter logging unresolved attributes during production runs to systematically expand `schema_registry.json`.
7. **Production Frontend Build:** Create multi-stage `Dockerfile` and `docker-compose.yml` serving the React build via Nginx.
8. **Rule Conflict Detection:** Detect contradictions between rules extracted from differing document revisions (e.g., standard 2020 vs 2024).

---

## 11. Proposed Agentic Architecture for Future Scaling

### 11.1 The Rationale for an Agentic Formalisation Engine

While the current Version 3 formalisation pipeline is significantly more accurate than its predecessors, its reliance on a **single generalist LLM prompt at Tier 2** remains its primary vulnerability. 

A single prompt must simultaneously deduce:
1. The manufacturing domain (among 12 options)
2. The structural bucket (among 9 options)
3. The specific physical features and objects
4. The exact CAD-namespaced mathematical formula
5. Any filtering conditions or conditional branch logic
6. The list of formula variables (`AllowedParams`)

When extracting rules with complex multi-feature relationships or nested conditional branches, a single prompt can easily misassign one field, triggering validator failures.

### 11.2 Specialized Multi-Agent Architecture

The proposed next generation decomposes the formalisation stage into specialized, cooperative agents orchestrated by a coordinator:

```
                            Extracted Rule Sentence
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. DOMAIN & BUCKET AGENT                                                    │
│ Determines Domain & selects the exact format1 structural bucket template   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
┌──────────────────────────────────────┐┌─────────────────────────────────────┐
│ 2. ENTITY RESOLUTION AGENT           ││ 3. FILTER & CONDITION AGENT         │
│ Identifies Feature1/2, Object1/2     ││ Extracts applicability filters and  │
│ strictly from domain schema registry ││ branch conditions independently     │
└──────────────────┬───────────────────┘└──────────────────┬──────────────────┘
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. MATHEMATICAL FORMALISATION AGENT                                         │
│ Derives ExpName, Operator, Value formula, and compiles AllowedParams        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. COORDINATOR & VALIDATION AGENT                                           │
│ Deterministically constructs format1 JSON, runs 17-Check Validator, and     │
│ routes specific error codes back to the responsible agent for targeted fix   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.3 Generation Comparison Across Generations

| Capability | Gen 1 (Phase-3) | Gen 2 (V1) | Gen 3 (Current V3) | Proposed Agentic V4 |
|---|---|---|---|---|
| **Rule Extraction Accuracy** | Low | Medium | **High** | **Very High** |
| **Complex Condition Handling** | None | Low | **Medium-High** | **Very High** |
| **Error Isolation** | None | None | **Diagnostic-Level** | **Agent-Level (Isolated)** |
| **Schema Compliance** | None | Partial | **Enforced (17 Checks)**| **Enforced & Auto-Repaired** |
| **Deployment Readiness** | Prototype | Experimental | **Production Ready (Deploy Now)** | Future Architecture |

**Strategic Guidance:** The current Version 3 pipeline in `dfm_rule_pipeline/taxonomy/` is the correct, stable system for immediate production deployment. The agentic model should be developed as a non-breaking evolution for future enterprise scaling.

---

## 12. Glossary of Engineering Terms

| Term | Definition |
|---|---|
| **DFM** | Design for Manufacturability — rules and guidelines ensuring engineered parts can be manufactured reliably and cost-effectively. |
| **`format1.json` / BucketList** | HCL's official JSON rule specification consisting of top-level identifiers and nested `Constraints` parameter lists. |
| **`TaxonomyRule`** | Pydantic data model representing a fully formalized DFM rule ready for CAD software ingestion. |
| **`ExpName`** | Expression Name — a CAD-namespaced dotted path (`Feature.Attribute`, e.g., `SheetMetal.Thickness`, `Hole.Depth`). |
| **`AllowedParams`** | An array of `ExpName` variable strings that must be explicitly declared whenever a rule value uses a formula. |
| **`TruthStore`** | SQLite database tracking exact character spans and window coordinates of source text, ensuring 100% extraction provenance. |
| **Anchor Classifier** | Local vector-similarity filter scoring text against canonical DFM exemplars, eliminating boilerplate before cloud LLM calls. |
| **17-Check Validator** | Deterministic validation engine verifying syntactic, mathematical, and schema integrity of formalized rules. |
| **Targeted Repair** | Dynamic error-recovery loop injecting specific validation diagnostics directly into LLM correction prompts. |

---

*Handover Report finalized for RAG-RuleSync V2 with Version 3 Formalisation Engine.*  
*Contributors: Rahul Dewani, Daksh Agarwal, Spandan Kewte, Raj Patle*  
*Document Date: September 2026*
