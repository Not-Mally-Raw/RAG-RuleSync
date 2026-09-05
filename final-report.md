# HCL DFM Rule Extraction — Comprehensive Handover & Technical Report
### RAG-RuleSync V2 (Current Final State) | Technical & Stakeholder Reference

---

> **Document Purpose:** This report is the complete handover document for the incoming development team, project stakeholders, and HCL Technologies. It documents the full final state of RAG-RuleSync V2, details the evolution from the previous RAG-RuleSync V1, explains architectural decisions, catalogues known risks and limitations with mitigation strategies, provides an honest performance and quality assessment, and outlines the future roadmap — including a proposed agentic pipeline architecture as the recommended next step.
>
> **Predecessors:** This report builds on two prior documents: the [Phase-3-Final → RAG-RuleSync handover](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/Handover_Report_Phase3_to_RAG_RuleSync.md) and the FaceVault-style [structural template](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/Handover_report.md).

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Overview & Scope](#2-project-overview--scope)
3. [System Architecture — Full Stack Breakdown](#3-system-architecture--full-stack-breakdown)
4. [Evolution: RAG-RuleSync V1 → V2](#4-evolution-rag-rulesync-v1--v2)
5. [Key Improvements in V2](#5-key-improvements-in-v2)
6. [Known Risks & Current Limitations](#6-known-risks--current-limitations)
7. [Technology Stack & Justification](#7-technology-stack--justification)
8. [Pipeline Results & Output Formats](#8-pipeline-results--output-formats)
9. [Development Timeline](#9-development-timeline)
10. [Future TODO Roadmap](#10-future-todo-roadmap)
11. [Proposed Agentic Architecture for Next Phase](#11-proposed-agentic-architecture-for-next-phase)
12. [Glossary](#12-glossary)

---

## 1. Executive Summary

RAG-RuleSync V2 is the current production state of an enterprise-grade **Design-for-Manufacturability (DFM) rule extraction pipeline** built for HCL Technologies. The system ingests unstructured manufacturing documents (PDFs) and transforms them into structured, CAD-ready rule constraints in the **Taxonomy/BucketList JSON format** — the specific schema format required by HCL's downstream CAD compliance engine.

This version represents the **third major iteration** of the system:

| Generation | System | Core Approach |
|---|---|---|
| Generation 1 | Phase-3-Final (Previous Team) | Supervised ML classifiers + manual workflow |
| Generation 2 | RAG-RuleSync V1 | Mega-prompt LLM extraction + 4-stage refinement pipeline |
| Generation 3 | **RAG-RuleSync V2 (Current)** | Layout-aware ingestion + local anchor classification + Taxonomy V3 formalization |

**V2's primary advances over V1:**

1. **Replaced brute-force LLM extraction** with a local-first, embedding-based anchor classification system (`core_v2/`) that filters out ~80% of irrelevant document text *before* any LLM call — dramatically reducing API costs and hallucination rates.
2. **Introduced the Taxonomy V3 formalization engine** — a 6-tier pipeline (Classify → Prompt → Extract → Assemble → Validate → Repair) that produces the deeply-nested `format1.json` BucketList schema, directly consumable by HCL's CAD toolchain.
3. **Introduced a production FastAPI backend** — a REST API (`app.py`) with 3 independent pipeline endpoints, replacing the Streamlit-only V1 interface entirely.
4. **Introduced a React/Vite frontend** (`frontend/`) as a proper SPA web application — the project now has a dedicated frontend codebase instead of Streamlit pages.
5. **Round-robin multi-key Groq rotation** — eliminates free-tier rate limit bottlenecks by distributing requests across a configurable pool of API keys.

> **For Stakeholders:** The system now delivers rules in the exact `format1.json` structure that HCL's CAD validation software expects, with automatic repair loops, schema validation, and domain-classification — significantly reducing manual engineering intervention.

---

## 2. Project Overview & Scope

### What RAG-RuleSync V2 Is

A fully-automated, end-to-end pipeline that:

- **Ingests** PDF manufacturing specification documents using a layout-aware parser that preserves structural hierarchy (section titles, paragraphs, lists).
- **Classifies** text windows locally via sentence-transformer embeddings and FAISS vector search against a curated set of DFM anchor rules — eliminating non-rule text without LLM costs.
- **Extracts** verbatim manufacturing rule sentences from candidate blocks using an LLM (Groq), with section-title injection to resolve pronoun blindness and context gaps.
- **Formalizes** extracted rules into deeply-nested JSON (`TaxonomyRule`) matching HCL's `format1.json` schema — covering `ValidationParamList`, `FilterParamList`, `ConditionParamList`, `AdditionalParamList`, and `UserParamList`.
- **Validates** every formalized rule against a deterministic 17-check schema validator and triggers targeted LLM repair loops when validation fails.
- **Exports** CAD-ready output via a REST API (`/process-rules-taxonomy`) and CSV download.

### What RAG-RuleSync V2 Is NOT

- **Not a real-time system:** Processing is batch-oriented per document, not streaming.
- **Not multi-format complete:** Only PDF ingestion is fully supported in the V2 core pipeline. DOCX/Excel support exists in `requirements.txt` but is not wired into `core_v2/`.
- **Not image/table-aware:** Rules embedded inside figures, diagrams, or complex PDF tables are not extracted.
- **Not cloud-deployed:** The system runs locally or in a CI/CD container. No production Kubernetes/cloud deployment exists.
- **Not formally benchmarked in CI:** Accuracy is assessed against the 110-rule ground truth CSV (`Ground-truth.csv`), but no automated precision/recall computation runs in CI.

---

## 3. System Architecture — Full Stack Breakdown

### 3.1 High-Level Architecture (V2)

```
┌──────────────────────────────────────────────────────────────────────┐
│                  CLIENT LAYER                                        │
│   React/Vite Frontend (frontend/)                                    │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTP (Fetch API / uvicorn)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  API LAYER                                           │
│   app.py — FastAPI (uvicorn, CORS-enabled)                          │
│   POST /upload-document       → Pipeline 1 (core_v2)               │
│   POST /process-rules         → Pipeline 2 (dfm stages)            │
│   POST /process-rules-taxonomy → Pipeline V3 (Taxonomy)            │
└──────────┬───────────────────────────┬───────────────────────────────┘
           │                           │
           ▼                           ▼
┌───────────────────┐    ┌────────────────────────────────────────────┐
│   CORE V2 ENGINE  │    │       DFM RULE PIPELINE                   │
│   (core_v2/)      │    │   dfm_rule_pipeline/                      │
│                   │    │                                            │
│   Parser          │    │   Classic Stages (pipeline.py)            │
│   → TruthStore    │    │   Stages 1-4: Intent → Resolution         │
│   → Windower      │    │   → Formalization → Validation            │
│   → Embeddings    │    │                                            │
│   → FAISS Store   │    │   ─────────────────────────────           │
│   → Anchor Cls.   │    │   Taxonomy V3 (taxonomy/)                 │
│   → Assembler     │    │   BucketClassifier → PromptBuilder        │
│   → LLMStructurer │    │   → LLMExtractor → Assembler              │
│   → Deduplication │    │   → Validator → RepairLoop                │
└───────────────────┘    └────────────────────────────────────────────┘
```

### 3.2 Core V2 Extraction Engine (`core_v2/`)

The Core V2 engine is a **local-first, 3-phase document processing pipeline** designed to maximize signal quality before any cloud LLM call.

| File | Purpose | Key Design Decision |
|---|---|---|
| [`parser.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/parser.py) | `LayoutAwareParser` — PyMuPDF hierarchical block extraction | Preserves section titles; injected into LLM prompts to resolve pronoun blindness |
| [`truth_store.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/truth_store.py) | `TruthStore` — SQLite-backed immutable record of all blocks/windows | Every extracted rule can be traced to an exact character index in the source PDF |
| [`windower.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/windower.py) | `SlidingWindowGenerator` — spaCy-based sentence windowing with overlap | spaCy prevents mid-unit truncation (e.g., "0.3 in." boundary) |
| [`embeddings.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/embeddings.py) | `EmbeddingManager` — `all-MiniLM-L6-v2` on CPU | Local-only; no API cost; 384-dim vectors |
| [`vector_store.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/vector_store.py) | `VectorStore` — FAISS flat index | Sub-millisecond cosine similarity search |
| [`dfm_anchors.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/dfm_anchors.py) | `DFMAnchorClassifier` — Threshold-based gate (default: 0.25) | Eliminates ~80% of boilerplate before LLM |
| [`candidate_assembler.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/candidate_assembler.py) | `CandidateAssembler` — Groups windows by `block_id` | Prevents sentence fragmentation from sliding window overlap |
| [`llm_structurer.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/llm_structurer.py) | `LLMStructurer` — Verbatim extraction with context injection | `rule_text` must be exact substring; `resolved_rule_text` resolves pronouns |
| [`validator.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/validator.py) | Multi-hop conflict resolver | Uses `section_title` metadata to distinguish new rules from refinements |

**Phase 1 Output:** `ExtractedRule` objects — `{rule_text, resolved_rule_text, source_window_ids}`.

### 3.3 DFM Rule Refinement Pipeline (`dfm_rule_pipeline/`)

The classic formalization pipeline inherited from V1. Converts Level-1 verbatim rules into equations (old flat CSV format) via 4 sequential stages.

> **Note:** This pipeline is active via `/process-rules` but superseded for new work by Taxonomy V3 (`/process-rules-taxonomy`). Retained for backward compatibility.

| Stage | File | Purpose |
|---|---|---|
| **Stage 1** | [`stage1_intent_extraction.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/stages/stage1_intent_extraction.py) | Determines: quantifiable? geometry/tolerance/attribute? |
| **Stage 2** | [`stage2_rule_resolution.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/stages/stage2_rule_resolution.py) | Categorizes into Attribute / Geometry / Tolerance; maps domain |
| **Stage 2a** | [`stage2a_schema_consistency.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/stages/stage2a_schema_consistency.py) | Validates objects against domain feature schema |
| **Stage 2b** | [`stage2b_geometry_resolution.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/stages/stage2b_geometry_resolution.py) | For distance/spatial rules: extracts entity pairs |
| **Stage 2c** | [`stage2c_tolerance_spec.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/stages/stage2c_tolerance_spec.py) | For tolerance rules: `Tolerance()`, `Limits()`, `GDT()` |
| **Stage 3** | [`stage3_formalization.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/stages/stage3_formalization.py) + attribute variant | Creates raw mathematical formula using schema variable names |
| **Stage 4** | [`stage4_self_validation.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/stages/stage4_self_validation.py) | LLM self-corrects: schema membership, operator validity |

**AST Engine** ([`ast_engine/`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/ast_engine/)): Handles compound conditional logic (e.g., `bend_radius >= MAX(0.5 × thickness, 0.80)`) via `ast_nodes.py`, `ast_builder.py`, `ast_evaluator.py`.

**Formatter** ([`formatter.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/formatter.py)): `DOMAIN_CONFIG` maps generic terms to CAD namespaced variables; `normalize_algebra()` canonicalizes ratio expressions.

### 3.4 Taxonomy V3 Formalization (`dfm_rule_pipeline/taxonomy/`)

The most significant new component of V2. Replaces the old flat CSV with the deeply-nested `format1.json` BucketList structure.

**The 6-Tier Pipeline:**

```
Rule Text Input
      │
      ▼ Tier 0 — BucketClassifier
┌──────────────────────────────────────┐
│  3-tier: Regex → Embedding → LLM     │
│  Outputs: bucket + domain            │
└──────────────────┬───────────────────┘
                   ▼ Tier 1 — PromptContextBuilder
┌──────────────────────────────────────┐
│  Injects domain schema + bucket      │
│  exemplars into LLM prompt           │
└──────────────────┬───────────────────┘
                   ▼ Tier 2 — LLMExtractor
┌──────────────────────────────────────┐
│  Returns flat ExtractionResult:      │
│  feature1/2, object1/2, validations, │
│  conditions, filters, additional     │
└──────────────────┬───────────────────┘
                   ▼ Tier 3 — TaxonomyAssembler
┌──────────────────────────────────────┐
│  Deterministically constructs nested │
│  TaxonomyRule JSON from flat result  │
└──────────────────┬───────────────────┘
                   ▼ Tier 4 — TaxonomyValidator (17 checks)
┌──────────────────────────────────────┐
│  Schema membership, operators, array │
│  dimensions, boolean values, units,  │
│  branch alignment checks             │
└──────────────────┬───────────────────┘
      ┌────────────┴──────────────┐
      │ Errors?                   │ Clean
      ▼ Yes                       ▼
┌──────────────┐     ┌─────────────────────────┐
│ TaxonomyRepair│    │ Success: TaxonomyResponse│
│ Targeted LLM │     │ decision_code: formalized│
│ re-prompt    │     └─────────────────────────┘
│ → Re-assemble│
│ → Re-validate│
└──────────────┘
```

| File | Size | Purpose |
|---|---|---|
| [`bucket_registry.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/bucket_registry.py) | 9.4 KB | 9 structural bucket types: SimpleValidation, RangeValidation, ConditionalValidation, DistanceRule, SetMembership, AdditionalInfoValidation, FeatureInteraction, AssemblyRule, ProcessParameter |
| [`bucket_classifier.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/bucket_classifier.py) | 26 KB | 3-tier classification: Regex → Embedding cosine similarity → LLM fallback |
| [`schema_registry.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/schema_registry.py) | 14 KB | Loads `schema_registry.json` — all valid `Feature.Attribute` paths per domain |
| [`schema_registry.json`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/schema_registry.json) | 22 KB | Source of truth for all CAD schema paths. All `ExpName` values must trace here |
| [`validator.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/validator.py) | 24 KB | 17 deterministic checks: schema root, attribute validity, boolean values, AllowedParams, branch alignment, unit detection, distance objects |
| [`repair.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/repair.py) | 7.6 KB | Targeted repair with per-error-code instruction templates |
| [`assembler.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/assembler.py) | 18 KB | Deterministic assembly of nested `TaxonomyRule` from flat `ExtractionResult` |
| [`prompt_context.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/prompt_context.py) | 8.7 KB | Dynamic prompt: domain schemas + bucket exemplars + few-shot examples |
| [`service.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/service.py) | 12.8 KB | `TaxonomyFormalizationService` — orchestrator with multi-sentence paragraph splitting |
| [`models.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/models.py) | 5.9 KB | All Pydantic models: `TaxonomyRule`, `ExtractionResult`, `Constraints`, `TaxonomyResponse`, etc. |

### 3.5 Frontend (`frontend/`)

React 18 / Vite SPA for production UI interactions.

| File | Size | Purpose |
|---|---|---|
| [`src/App.jsx`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/frontend/src/App.jsx) | 23.5 KB | Main React application — UI logic, state, API calls |
| [`src/index.css`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/frontend/src/index.css) | 24 KB | Full design system, dark theme, component styles |
| [`vite.config.js`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/frontend/vite.config.js) | — | Proxies API calls to `localhost:8000` |

> **⚠️ Important:** The React frontend is in **development state only** — no production build or Docker setup exists. The API itself (`/docs` Swagger UI) is the primary interface for testing individual endpoints.

### 3.6 API Layer (`app.py`)

[`app.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/app.py) is a **FastAPI** application exposing three distinct pipeline endpoints:

| Endpoint | Pipeline | Description |
|---|---|---|
| `GET /` | Health | Returns API status |
| `POST /upload-document` | Pipeline 1 — Core V2 | PDF → Level-1 `{rule_text, resolved_rule_text}` pairs |
| `POST /process-rules` | Pipeline 2 — Classic | Rule sentences → formalized equations (old flat format) |
| `POST /process-rules-taxonomy` | Pipeline V3 — Taxonomy | Rule sentences → full `format1.json` BucketList structures |

**Interactive docs:** `http://localhost:8000/docs` (Swagger UI, auto-generated by FastAPI).

### 3.7 File Structure

```
RAG-RuleSync/  (Final State, September 2026)
├── app.py                           # FastAPI backend — 3 pipeline endpoints
├── requirements.txt                 # ~22 dependencies
├── README.md                        # Setup & run instructions
├── Project_description.md           # V2 architecture description
├── rule-taxonomy_bucketlist_format.md # BucketList format specification
├── Ground-truth.csv                 # 110-rule annotated ground truth
├── Ground-truth.xlsx                # 107-rule ground truth (Excel)
├── phase3_partial_output.json       # Partial extraction backup on rate-limit
├── phase3_final_rules.csv           # Classic pipeline CSV output
│
├── core_v2/                         # Phase 1: Layout-aware extraction (11 files)
│   ├── parser.py                    # LayoutAwareParser (PyMuPDF)
│   ├── truth_store.py               # SQLite source-of-truth
│   ├── windower.py                  # spaCy sliding windows
│   ├── embeddings.py                # sentence-transformers
│   ├── vector_store.py              # FAISS vector index
│   ├── dfm_anchors.py               # Anchor classification
│   ├── candidate_assembler.py       # Block grouping + context assembly
│   ├── llm_structurer.py            # LLM verbatim extraction
│   ├── extractor.py                 # Extraction coordinator
│   └── validator.py                 # Multi-hop conflict resolver
│
├── dfm_rule_pipeline/               # Phase 2 + 3: Formalization (40+ files)
│   ├── config.py                    # Central config (LLM_MODEL, keys, embedding)
│   ├── pipeline.py                  # Classic 4-stage orchestrator
│   ├── formatter.py                 # DOMAIN_CONFIG + CAD normalization
│   ├── main.py                      # CLI entrypoint for classic pipeline
│   ├── stages/ (9 files)            # Classic stages 1-4
│   ├── ast_engine/ (4 files)        # AST for compound logic
│   ├── schema/ (5 files)            # 12-domain feature schema
│   ├── llm/ (2 files)               # Round-robin LLM client
│   ├── taxonomy/ (13 files)         # Taxonomy V3 pipeline
│   └── tests/                       # Test fixtures
│
├── frontend/                        # React/Vite SPA
│   ├── src/App.jsx                  # Main application (23.5 KB)
│   ├── src/index.css                # Design system (24 KB)
│   ├── package.json
│   └── vite.config.js
│
└── tests/                           # Test suites (11 files)
    ├── test_bucketlist_coverage.py  # Taxonomy coverage tests (17 KB)
    ├── test_taxonomy_engine.py      # Full taxonomy pipeline tests (8 KB)
    ├── test_candidate_assembler.py
    ├── test_extraction.py
    ├── test_indexing.py
    ├── test_ingestion.py
    ├── test_llm_client_fallback.py  # Round-robin rotation tests
    ├── test_taxonomy_api.py
    ├── test_groq.py
    └── test_conn.py
```

**Total V2 codebase: ~55+ files, ~15,000+ lines of code.**

---

## 4. Evolution: RAG-RuleSync V1 → V2

### 4.1 What Changed in V2

The transition from V1 to V2 was a **fundamental rearchitecture of Stage 1 (extraction)** and a **complete addition of the Taxonomy V3 output format**. The core DFM pipeline stages from V1 were retained as a backward-compatible pathway.

**V1 Stage 1 (discarded):**
- Sent entire PDF text chunks directly to LLM via the mega-prompt in `core/prompts.py`
- LangChain + `JsonOutputParser` for structured output
- 800-token windows with 400-token overlap, no local filtering
- High rate-limit exposure; hallucination risk on boilerplate text
- Output: flat JSON `{rule_text, dimensional_constraints, relational_constraints, applicability_constraints}`

**V2 Stage 1 (current):**
- Local embedding-based anchor classification filters ~80% of non-rule text before LLM
- spaCy-based windowing prevents engineering-unit truncation
- SQLite `TruthStore` guarantees verbatim source provenance
- LLM called only on pre-filtered candidate blocks with section-title context injection
- Output: `{rule_text, resolved_rule_text, source_window_ids}` tuples

**V1 Stage 2 output (old flat format):**
```csv
RuleText, Status, DecisionCode, RuleCategory, dfm_json
"Distance >= 4.5 * SheetMetal.Thickness", Success, formalized, Sheet Metal, {...}
```

**V2 Stage 2 output (Taxonomy V3 — new):**
```json
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
    "ValidationParamList": [{
      "ExpName": "Distance.MinValue",
      "Operator": [[">="]],
      "Value": [[["4.5*SheetMetal.Thickness"]]],
      "AllowedParams": ["SheetMetal.Thickness"]
    }],
    "AdditionalParamList": [{"ExpName": ""}],
    "UserParamList": [{"ParamName": "", "DisplayName": "", "Value": [""], "MinValue": "", "MaxValue": ""}]
  }
}
```

### 4.2 V1 vs V2 Comparison Table

| Dimension | RAG-RuleSync V1 | RAG-RuleSync V2 (Current) |
|---|---|---|
| **Stage 1 extraction** | Mega-prompt + LangChain direct LLM chunking | Local embedding anchor classification → LLM on filtered candidates |
| **Pre-filtering** | None | ~80% non-rule text filtered locally |
| **Context resolution** | None | Section-title injection + `resolved_rule_text` |
| **Hallucination prevention** | Zero-mutation JSON guarantee | TruthStore + verbatim extraction constraint |
| **Deduplication** | TF-IDF post-processing (disabled by default) | Block-ID grouping before LLM |
| **Rate limiting** | Intelligent retry + Groq→Cerebras failover | Round-robin multi-key rotation |
| **LLM providers** | Groq (primary) + Cerebras (secondary) | Groq only (multi-key pool) |
| **Output format** | Flat CSV: `ExpName/Operator/Recom` | Nested JSON: `format1.json` BucketList |
| **Schema validation** | Stage 4 LLM self-validation | 17-check deterministic validator + targeted repair |
| **API** | Streamlit UI only | FastAPI (3 endpoints) + React SPA |
| **Taxonomy formalization** | None | Full Taxonomy V3 (9 buckets, 13 files, 6-tier pipeline) |
| **Tests** | 6 test files | 11 test files |
| **Code volume** | ~10,000 LOC (40+ files) | ~15,000+ LOC (55+ files) |

---

## 5. Key Improvements in V2

### 5.1 Local-First Pre-Filtering (Anchor Classification)

**The single most impactful architectural improvement.** By embedding all text windows locally using `all-MiniLM-L6-v2` (CPU-only, no GPU needed) and comparing against DFM anchor exemplars via FAISS cosine similarity, V2 eliminates roughly 80% of document text before sending anything to Groq.

**Practical impact:**
- Dramatically lower API token consumption per document
- Fewer hallucinated "rules" from boilerplate content
- Faster wall-clock processing (fewer LLM round-trips)

### 5.2 Verbatim Extraction + TruthStore Provenance

The `TruthStore` records every text block and window as an immutable source of truth. The `LLMStructurer` is explicitly instructed: `rule_text` must be an **exact, continuous substring** of the input — not a paraphrase.

**Practical impact:**
- Every formalized rule traces back to exact character indices in the source PDF
- LLM cannot fabricate rule text that doesn't exist
- Built-in audit trail for compliance purposes

### 5.3 Taxonomy V3 — BucketList Format Output

The `format1.json` BucketList schema is what HCL's CAD compliance engine directly consumes. V1 produced a flat CSV requiring manual translation. V2 produces the full nested structure — including `FilterParamList` (applicability restrictions), `ConditionParamList` (if-then-else branches), `ValidationParamList` (pass/fail checks), `AdditionalParamList`, and `UserParamList`.

This eliminates an entire manual translation step that previously required senior engineering effort.

### 5.4 Deterministic 17-Check Validator

The [`TaxonomyValidator`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/validator.py) applies 17 deterministic checks to every formalized rule. Key checks include:

1. All 5 constraint lists present
2. `ValidationParamList` non-empty
3. Schema root validation (Feature/Object exists in domain)
4. Schema attribute validation (Attribute exists on Feature)
5. Boolean value validation (`.Is*` fields must use "Yes"/"No")
6. `AllowedParams` completeness (all formula variables declared)
7. Branch alignment (ConditionParam branches match ValidationParam value groups)
8. Unit-in-value detection (numeric values must not contain "mm", "deg", etc.)
9. Distance object presence (DistanceRule bucket requires Object1 + Object2)
10. Module-Feature conflict check
11. Unsupported operator detection
12–17. Value/operator dimension validation, filter type checking, UserParam bounds, new attribute auto-registration

### 5.5 Targeted LLM Repair Loop

When validation fails, [`TaxonomyRepair`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/repair.py) composes **error-code-specific repair instructions** rather than generic re-prompts:

> *"In the ExpName variable path 'Pocket.SideAngle', the attribute 'SideAngle' does not exist for object 'Pocket' in domain 'Milling'. Valid attributes for 'Pocket' are: ['SideFaceAngle', 'Depth', 'Width', 'Length', 'BottomFaceAngle']. Choose the correct attribute."*

This precision produces significantly higher repair success rates.

### 5.6 Multi-Sentence Paragraph Handling

[`service.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/service.py) includes `_split_into_rule_sentences()` — a regex-based segmentation function that:

- Detects **topic-shift markers** (`"Additionally"`, `"Furthermore"`) to split compound paragraphs into independent rules
- Detects **anaphoric continuations** (`"the ratio"`, `"it reduces"`) to merge continuation sentences with their parent rule

This prevents over-splitting compound rules and under-splitting independent rules in the same paragraph.

### 5.7 Round-Robin API Key Rotation

The new [`LLMClient`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/llm/client.py) reads a comma-separated list of Groq keys from `.env` via `config.py`:
```
GROQ_API_KEYS=gsk_key1,gsk_key2,gsk_key3
```
(The config also accepts the singular `GROQ_API_KEY` as a fallback for single-key setups.) Every API call rotates to the next key, effectively multiplying the TPM limit by the number of keys. On full pool exhaustion, processed rules are flushed to `phase3_partial_output.json` for zero data loss.

### 5.8 FastAPI Production Backend

The previous V1 codebase used Streamlit as its only user-facing interface. V2 completely replaces this with a proper client-server split: [`app.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/app.py) is a FastAPI backend and `frontend/` is a React SPA.

The FastAPI backend provides:
- Swagger UI at `/docs` — the primary interface for testing and API exploration
- CORS middleware for React frontend integration
- 3 independent pipeline endpoints (extraction / classic formalization / Taxonomy V3)
- Proper startup event initialization (global models loaded once on server start)
- Structured JSON error responses with HTTP status codes

---

## 6. Known Risks & Current Limitations

### 🔴 CRITICAL — Taxonomy Formalization Brittleness

**Location:** [`dfm_rule_pipeline/taxonomy/`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/taxonomy/)  
**Impact:** Rules with novel attribute vocabulary or complex compound conditions frequently land in `"Review Needed"` status requiring manual engineering intervention.

**Root Cause:** The pipeline uses a **single monolithic LLM call** (Tier 2) to simultaneously determine all fields: domain, bucket, feature/object names, validation expressions, filter conditions, and branch logic. When any single field is wrong, the entire assembly fails. There is no graceful degradation for partial success.

**The fundamental issue:** The valid output formats for a single rule vary significantly — a simple constraint uses `SimpleValidation`, a conditional one uses `ConditionalValidation` with linked branches, a distance rule uses `DistanceRule` with two objects, etc. A generalist single prompt cannot reliably determine which structural template to apply for all edge cases.

**Mitigation (short-term):** Expand `schema_registry.json` as new document types are processed. Enable the auto-registration mechanism (when `has_new_attr = True`).

**Recommended Long-term Fix:** See Section 11 — decompose into specialist agents.

---

### 🔴 CRITICAL — No Secondary LLM Provider (Cerebras Failover Dropped)

**Location:** [`dfm_rule_pipeline/llm/client.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/llm/client.py)  
**Impact:** If all Groq keys in the pool are exhausted simultaneously, the pipeline crashes. No automatic fallback exists (unlike V1, which fell back to Cerebras).

**Mitigation:** Add Cerebras or another OpenAI-compatible provider as a secondary fallback in `LLMClient.call()`. The same SDK is already used — this is a low-effort addition.

---

### 🟡 HIGH — Anchor Classification Threshold is Brittle

**Location:** [`app.py` startup event](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/app.py#L80), [`core_v2/dfm_anchors.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/dfm_anchors.py)  
**Impact:** The fixed `threshold=0.25` was tuned on HCL's Sheet Metal and Injection Molding documents. For domain-shifted documents (Additive Manufacturing, Die Casting), this may over-filter (missing valid rules) or under-filter (passing boilerplate to the LLM) — with no error indication.

**Mitigation:**
- Add configurable per-domain thresholds
- Report window reduction statistics in the `/upload-document` response
- Allow threshold override as a query parameter

---

### 🟡 HIGH — spaCy Model Not Installed by Default

**Location:** [`core_v2/windower.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/core_v2/windower.py)  
**Impact:** `windower.py` requires `en_core_web_sm` which is **not installed by `pip install -r requirements.txt` alone**. A separate `python -m spacy download en_core_web_sm` is required. Missing this causes a cryptic runtime failure on first document upload.

**Mitigation:**
- Add `python -m spacy download en_core_web_sm` as an explicit setup step in README
- Add startup validation in `app.py` that checks for the model and surfaces a clear error if missing

---

### 🟡 HIGH — Frontend is Development-State Only

**Location:** [`frontend/`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/frontend/)  
**Impact:** No production build exists. The React app can only be run via `npm run dev`. It cannot be deployed to any staging or production environment.

**Mitigation:**
- Add `npm run build` step to CI/CD pipeline
- Configure FastAPI to serve the `frontend/dist/` directory as static files
- Create `docker-compose.yml` with separate `api` and `frontend` services

---

### 🟡 HIGH — No Formal Accuracy Benchmarks in CI

**Location:** [`Ground-truth.csv`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/Ground-truth.csv)  
**Impact:** The 110-rule ground truth file exists but no automated test compares pipeline output against it. Silent quality regressions will not be detected.

**Mitigation:** Build `test_ground_truth_coverage.py` that loads `Ground-truth.csv`, passes each rule through `/process-rules-taxonomy`, and computes Success-rate metrics. Gate CI on a minimum threshold (e.g., >80% `Success` status).

---

### 🟡 HIGH — Global State in API Startup — Limited Concurrency Safety

**Location:** [`app.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/app.py#L70-L82)  
**Impact:** `embedder`, `classifier`, `llm_client`, and `taxonomy_service` are global variables. The `current_client_idx` in `LLMClient` is a non-thread-safe integer increment. Under concurrent load, key rotation distribution can drift (though Python's GIL prevents crashes).

**Mitigation:** Protect `current_client_idx` increment with `threading.Lock()`.

---

### 🟢 MEDIUM — README References Non-Existent `streamlit_v2.py`

**Location:** [`README.md`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/README.md)
**Impact:** `README.md` references `python -m streamlit run streamlit_v2.py` as the primary startup command — but no Streamlit files exist anywhere in the repository. Any developer following the README gets an immediate file-not-found error before they can even run the system.

**Root Cause:** The README was carried over from an earlier development phase when Streamlit was still the primary UI. Streamlit was subsequently removed and replaced with FastAPI + React, but the README was not updated to reflect this.

**Mitigation:** Update `README.md` with the correct startup commands for both the FastAPI backend (`uvicorn app:app --reload --port 8000`) and the React frontend (`npm run dev` in `frontend/`).

---

### 🟢 MEDIUM — `pipeline.py` Uses Non-Portable Relative Imports

**Location:** [`dfm_rule_pipeline/pipeline.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/dfm_rule_pipeline/pipeline.py)  
**Impact:** Imports like `from stages.stage1_intent_extraction import extract_intent` work only when running from within `dfm_rule_pipeline/`. Running from project root fails.

**Mitigation:** Convert all imports to absolute package paths: `from dfm_rule_pipeline.stages.stage1_intent_extraction import extract_intent`.

---

### 🟢 MEDIUM — CORS Fully Open + No API Authentication

**Location:** [`app.py`](file:///d:/Downloads/HCL_COMBINED/Final-RuleSync-Version/RuleSync/app.py#L61-L67)  
**Impact:** `allow_origins=["*"]` is a security vulnerability in any production deployment. No authentication means anyone with network access can process documents and consume Groq API quota.

**Mitigation:** Restrict `allow_origins` to specific frontend origin. Add API key header check or JWT middleware before any non-localhost deployment.

---

### 🟢 MEDIUM — Table and Figure Rule Extraction Not Supported

**Impact:** Rules embedded inside PDF tables (tolerance charts, material lookup tables) and figures (annotated engineering drawings) are not extracted. This may represent significant coverage gaps for documents heavy in tabular specifications.

**Mitigation:** Planned enhancement — see Section 10.

---

## 7. Technology Stack & Justification

### ✅ Technologies in Active Use

| Technology | Category | Justification |
|---|---|---|
| **FastAPI + Uvicorn** | API Framework | Replaces Streamlit (V1's only interface). Native async, automatic Swagger docs, Pydantic validation. Enables proper client-server separation with the React frontend |
| **PyMuPDF (fitz)** | PDF Processing | Layout-aware block extraction with section hierarchy — beyond simple text strip |
| **spaCy `en_core_web_sm`** | NLP / Windowing | Sentence-boundary detection respecting engineering units. Regex splitting broke on abbreviations like "0.3 in." |
| **sentence-transformers** | Local Embeddings | `all-MiniLM-L6-v2` on CPU; no API cost; powers anchor classification |
| **FAISS (faiss-cpu)** | Vector Search | In-memory, zero-infrastructure cosine similarity for anchor classification |
| **Groq API** | LLM Provider | Fast inference, OpenAI-compatible, generous free-tier. Multi-key rotation addresses TPM limits |
| **LangChain + LangChain-Groq** | LLM Orchestration | Used in Core V2 `LLMStructurer`. Provides `ChatPromptTemplate` and chain composition |
| **Pydantic v2** | Data Validation | API models, all Taxonomy data models (`TaxonomyRule`, `ExtractionResult`, `Constraints`), configuration |
| **SQLite (Python `sqlite3`)** | TruthStore | Per-request temp database. Zero external dependency, guarantees rule provenance |
| **React 18 + Vite** | Frontend | Modern SPA; Vite proxies API calls to FastAPI backend |
| **pytest + pytest-asyncio** | Testing | Standard Python testing with async support |
| **structlog** | Logging | Structured JSON logging for production monitoring |
| **python-dotenv** | Configuration | Secure API key management; `.env` excluded from version control |
| **openai SDK** | LLM Client | Used for Groq (OpenAI-compatible endpoint) in round-robin client |

### ❌ Technologies Abandoned / Disabled

| Technology | Status | Reason |
|---|---|---|
| **Cerebras API** | Dropped in V2 | Round-robin rotation replaced the failover need — but should be re-added as an emergency fallback |
| **LangChain JsonOutputParser** | Replaced in V2 Core | V2's `LLMStructurer` uses direct JSON parsing instead |
| **Qdrant vector store** | Stub exists in V1 (`use_qdrant=False`), not ported to V2 | Mega-prompt outperformed RAG retrieval for this use case |
| **scikit-learn TF-IDF dedup** | Disabled in V1, not ported to V2 | Block-ID grouping handles deduplication more effectively |
| **PyTorch / TensorFlow** | Eliminated (Phase-3-Final legacy) | LLM-first approach eliminated local DL framework dependency |
| **PaddleOCR + DETR + Win32COM** | Eliminated (Phase-3-Final legacy) | Windows-only, compute-heavy, replaced by text-based extraction |
| **HuggingFace Hub model downloads** | Eliminated (Phase-3-Final legacy) | Multi-GB startup downloads replaced by zero-shot LLM prompting |
| **spaCy in CI only** (V1) | Promoted to runtime dependency in V2 | V2 Windower actively uses spaCy for sentence boundary detection |

---

## 8. Pipeline Results & Output Formats

### Level-1 Extraction Sample (from `/upload-document`)

```json
[
  {
    "rule_text": "Distance between bridges should be at least 4.5 times sheet thickness",
    "resolved_rule_text": "Distance between bridges should be at least 4.5 times sheet thickness",
    "source_window_ids": ["win_0042", "win_0043"]
  },
  {
    "rule_text": "It must be at least 1.5 times material thickness",
    "resolved_rule_text": "Bend radius must be at least 1.5 times material thickness",
    "source_window_ids": ["win_0089"]
  }
]
```

### Taxonomy V3 Output (from `/process-rules-taxonomy`)

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
        "FilterParamList": [{"ExpName": "", "Operator": [""], "Value": [""]}],
        "ConditionParamList": [{"ExpName": "", "Operator": [[""]], "Value": [[[""]]]}],
        "ValidationParamList": [{
          "ExpName": "Distance.MinValue",
          "Operator": [[">="]],
          "Value": [[["4.5*SheetMetal.Thickness"]]],
          "AllowedParams": ["SheetMetal.Thickness"]
        }],
        "AdditionalParamList": [{"ExpName": ""}],
        "UserParamList": [{"ParamName": "", "DisplayName": "", "Value": [""], "MinValue": "", "MaxValue": ""}]
      }
    }
  ],
  "validation_errors": []
}
```

### Test Coverage Summary

| Test Category | Status |
|---|---|
| Simple validation rules (SheetMetal, Milling) | ✅ Covered |
| Range validation rules (between X and Y) | ✅ Covered |
| Conditional validation rules (if blind hole...) | ✅ Covered |
| Distance rules (distance between A and B) | ✅ Covered |
| Set membership rules (from the following list...) | ✅ Covered |
| Multi-sentence paragraph splitting | ✅ Covered |
| Repair loop for schema mismatch errors | ✅ Covered |
| Advisory/non-quantifiable rules | 🟡 Marked "Review Needed" — not formalized |
| Table-embedded rules | ❌ Not supported |
| Figure/diagram rules | ❌ Not supported |
| Ground truth precision/recall in CI | ❌ Not automated |

---

## 9. Development Timeline

### Phase-3-Final (Previous Team — July 2025)

| Period | Event |
|---|---|
| July 2025 | Initial prototype. 12 files, ~2,015 LOC. 1 developer. 6 commits. Development stopped. |

### RAG-RuleSync V1 (October 2025 — April 2026)

| Period | Milestone |
|---|---|
| October 2025 | Project inception. First working LLM extraction from PDFs without classification models. |
| November 2025 | SOLID principles refactoring — Protocol interfaces, Adapter pattern, Dependency Injection. |
| January 2026 | **Major milestone.** Mega-prompt as single source of truth. Pydantic coercion removed. DFM pipeline added. 64-rule extraction target achieved. |
| February 2026 | Rule formatting architecture finalized. `DOMAIN_CONFIG` variable substitution working. |
| March–April 2026 | Final testing, cleanup. Semantic domain keyword mapping. Pipeline stable. V1 delivered. |

### RAG-RuleSync V2 (April–September 2026)

| Period | Milestone |
|---|---|
| April–May 2026 | V2 architecture design. `core_v2/` built: LayoutAwareParser, TruthStore, SlidingWindowGenerator, DFMAnchorClassifier, FAISS. |
| May–June 2026 | Taxonomy V3 pipeline: BucketClassifier, SchemaRegistry, TaxonomyValidator, TaxonomyRepair, TaxonomyAssembler, `schema_registry.json`. |
| June–July 2026 | FastAPI backend with 3-pipeline architecture. React/Vite frontend scaffolded. |
| July–August 2026 | Round-robin LLM key rotation. `_split_into_rule_sentences()`. Test suite expanded to 11 files. |
| August–September 2026 | Stabilization, ground truth testing, documentation. **Current final state.** |

---

## 10. Future TODO Roadmap

### 🔴 Must-Fix Before Production Handoff

1. **Restore Cerebras failover** — Re-add Cerebras (or another OpenAI-compatible provider) as a secondary LLM in `LLMClient.call()`. Same SDK, low effort, prevents complete pipeline halts on Groq pool exhaustion.

2. **Update README.md with correct startup commands** — The README currently references a `streamlit_v2.py` that does not exist. Replace with the actual startup commands: `uvicorn app:app --reload --port 8000` for the API and `npm install && npm run dev` in `frontend/` for the React UI. This is the first thing a new developer reads.

3. **Document spaCy model install + add startup validation** — Add `python -m spacy download en_core_web_sm` to README setup steps. Add a startup check in `app.py` that surfaces a clear error with installation instructions if the model is missing.

4. **Fix `pipeline.py` relative imports** — Convert to absolute package paths for consistency with the rest of the codebase and portability.

5. **Restrict CORS and add API authentication** — Any non-localhost deployment requires this. At minimum, add an API key header check.

### 🟡 High Priority (Before Scaling)

6. **Automated ground truth benchmarking in CI** — Load `Ground-truth.csv`, run through `/process-rules-taxonomy`, compute Success-rate. Gate CI on a minimum threshold. This is the most critical quality gate missing from the current system.

7. **Production-build the React frontend** — `npm run build`, serve `frontend/dist/` from FastAPI, update `docker-compose.yml`.

8. **Thread-safe LLM key rotation** — Protect `current_client_idx` with `threading.Lock()` for concurrent request safety.

9. **Per-domain anchor classification thresholds** — Replace single `0.25` threshold with domain-aware configuration. Include window reduction statistics in `/upload-document` response.

10. **Full-stack Docker Compose** — `docker-compose.yml` with `api` (FastAPI + uvicorn) and `frontend` (Nginx + Vite build) services, with environment variables for all secrets.

### 🟢 Medium Priority (Feature Enhancements)

11. **Table rule extraction** — Integrate `pdfplumber` or `camelot` for structured table detection. Develop table-to-rules LLM prompt for tolerance charts and material-specific lookup tables.

12. **Expand `schema_registry.json` systematically** — Build a `schema_gap_reporter.py` that outputs all `ExpName` paths that failed with `schema_root_failed` or `schema_attribute_failed` errors after processing a document — enabling targeted schema expansion.

13. **Rule versioning and conflict detection** — Track rule versions as source documents are updated. Flag contradictions between versions (e.g., `BendRadius >= 1.0` in v2021 vs `BendRadius >= 1.5` in v2024).

14. **Multi-document cross-referencing** — Consolidate the same rule appearing across multiple documents into a single canonical entry with multiple source references.

15. **Engineer feedback loop** — Allow engineers to correct `"Review Needed"` rules through a UI action that feeds corrections back to improve prompts and expand schema registries.

16. **Expanded domain coverage** — Add Forging, Stamping, Surface Treatment, Welding as HCL's scope grows. Each requires schema registry entries, domain definitions, and bucket exemplars.

17. **Formal field-level accuracy benchmarking** — Beyond Success/Review-Needed rate: compute field-level accuracy for `Feature1`, `Object1`, `ExpName`, `Operator`, `Value` against human-annotated ground truth.

---

## 11. Proposed Agentic Architecture for Next Phase

> **Framing:** This section proposes the recommended long-term architectural direction for the formalization pipeline. It is not a critique of the current V2 system — which is a substantial and measurable improvement over both V1 and Phase-3-Final. V2 is the right system to deploy today. The agentic approach is the right direction for the *next* major phase, once V2's real-world failure modes are documented through production usage.

### 11.1 The Core Problem: Single-Prompt Overload

The current Taxonomy V3 pipeline uses **a single LLM call** (Tier 2: `LLMExtractor`) to simultaneously determine everything about a manufacturing rule:

1. Manufacturing **domain** (SheetMetal vs Milling vs Drilling vs...)
2. Structural **bucket** (SimpleValidation vs ConditionalValidation vs DistanceRule vs...)
3. **Feature/Object** identification (which physical feature is being constrained?)
4. **Validation expression** (`ExpName`, `Operator`, `Value`)
5. **Filter conditions** (what restricts the rule's applicability?)
6. **Branch conditions** (if-then-else structure with matching value groups)
7. **AllowedParams** (which formula variables must be declared?)

This is an extremely cognitively demanding task for a single prompt. The pipeline compensates with dynamic context injection (Tier 1), a 17-check validator (Tier 4), and a targeted repair loop (Tier 5). However, the repair loop is **single-pass**: if repair fails, the rule is returned as "Review Needed."

**The valid output structures for a single rule vary enormously:**

| Rule Type | Required Structure |
|---|---|
| Simple dimension constraint | `SimpleValidation` — one `ValidationParam` with one operator and value |
| Conditional constraint | `ConditionalValidation` — linked `ConditionParam` branches + matching `ValidationParam` value groups |
| Distance constraint | `DistanceRule` — `Object1 + Object2` fields + formula in `ValidationParam` |
| Range constraint | `RangeValidation` — two operators and two values |
| Set membership constraint | `SetMembership` — `FlatFilter` with `ANY` operator |

A single generalist prompt cannot reliably select the correct template for all these cases — especially for rules that exhibit characteristics of multiple buckets simultaneously (e.g., a conditional distance rule where the threshold depends on material type).

### 11.2 Proposed: Specialist Agent Architecture

The solution is to decompose the monolithic extraction step into a **team of specialist agents**, each responsible for one narrowly-defined decision:

```
Rule Text Input
       │
       ▼
┌──────────────────────┐
│  Domain Agent        │  → "This rule is SheetMetal / Milling / ..."
│  (Specialist)        │    Uses domain definitions + rule vocabulary
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Bucket Agent        │  → "This is a ConditionalValidation rule"
│  (Specialist)        │    Uses bucket exemplars + structural patterns
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Entity Agent        │  → "Feature1=Hole, Object1=Drill, Object2=Part"
│  (Specialist)        │    Uses domain schema for entity recognition
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Math Agent          │  → "ExpName=Hole.Depth/Hole.Diameter, Op=<=, Val=3.0"
│  (Specialist)        │    Uses formula grammar + domain variable catalog
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Filter/Condition    │  → Extracts if-then-else branches and applicability
│  Agent (Specialist)  │    filters independently from validation logic
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Coordinator Agent   │  → Combines all outputs into final TaxonomyRule JSON
│  (Orchestrator)      │    Validates; routes failures to the failing agent only
└──────────────────────┘
```

### 11.3 Why This Is Better

| Dimension | Current Single-Prompt Approach | Proposed Multi-Agent Approach |
|---|---|---|
| **Error isolation** | One wrong field corrupts the entire output | Each agent fails independently; coordinator handles partial success |
| **Prompt complexity** | Single prompt must cover all decisions simultaneously | Each agent has a narrow, well-defined responsibility with focused context |
| **Schema coverage** | One LLM must know all domain schemas at once | Domain-specific agents receive only relevant schema context |
| **Repair granularity** | Repair re-prompts the entire extraction | Re-run only the failing agent with targeted correction |
| **Format flexibility** | Format determined in one shot | Bucket agent explicitly selects the correct structural template before extraction |
| **Extensibility** | Adding new domains/buckets requires modifying a large shared prompt | Add a new specialist agent; others remain unchanged |
| **Debuggability** | Hard to identify which field decision went wrong | Each agent's output is independently inspectable |
| **Parallel execution** | Sequential | Domain + Bucket agents can run in parallel; Entity agent needs domain result only |

### 11.4 Recommended Agent Roles

| Agent | Input | Output |
|---|---|---|
| **Domain Classifier Agent** | Rule text + document context | Domain name + confidence score |
| **Bucket Classifier Agent** | Rule text + domain context | Bucket name + structural template selection |
| **Entity Extraction Agent** | Rule text + domain schema | `Feature1/2`, `Object1/2` validated against schema |
| **Math Formalization Agent** | Rule text + entity context + schema paths | `ExpName` + `Operator` + `Value` + `AllowedParams` |
| **Filter/Condition Agent** | Rule text + entity context | `FilterParamList` + `ConditionParamList` (branch logic) |
| **Coordinator / Assembler Agent** | All agent outputs | Final `TaxonomyRule` JSON or targeted re-run request for specific agents |

The current `TaxonomyValidator` (17 checks) and `TaxonomyRepair` module remain fully valid as the validation layer consumed by the Coordinator.

### 11.5 Implementation Path

- Each specialist agent can be implemented as a **LangChain chain** or a **LangGraph node**, enabling parallel execution where possible.
- The Coordinator is a **LangGraph graph** with conditional edges — `schema_root_failed` routes back to Entity agent; `branch_alignment_failed` routes back to Filter/Condition agent.
- The existing `schema_registry.json` becomes the primary knowledge base for both the Entity and Math agents, passed as focused context for the specific domain.

### 11.6 Honest Generation Comparison

> **Important:** The current V2 system is a substantial improvement over V1, and V1 was a complete rebuild over Phase-3-Final. The agentic architecture is the natural next evolution — not a replacement of V2, but its logical successor.

| Dimension | Phase-3-Final | RAG-RuleSync V1 | RAG-RuleSync V2 (Current) | Proposed Agentic System |
|---|---|---|---|---|
| **Rule coverage** | Low | Medium | Medium-High | High |
| **Output correctness** | Low | Medium | Medium-High | High |
| **Error recovery** | None | Stage 4 self-validation | Single repair loop | Multi-hop targeted agent re-runs |
| **Novel rule handling** | Fails | Degrades gracefully | Partial ("Review Needed") | Better partial success with field-level attribution |
| **Debuggability** | None | Poor | Moderate | High |
| **Cost** | Very High (local models) | Medium (bulk LLM calls) | Lower (local pre-filter) | Similar to V2 (more calls but targeted) |
| **Implementation complexity** | Low | Medium | High | Very High |
| **Production readiness** | None | Low | **Moderate — Deploy Now** | Requires significant development |

**Conclusion:** Deploy V2 now. Build the agentic system in parallel as the next phase, informed by the failure patterns V2 reveals in production.

---

## 12. Glossary

| Term | Definition |
|---|---|
| **DFM** | Design for Manufacturability — engineering constraints ensuring a part design can be physically manufactured |
| **CAD** | Computer-Aided Design — software for engineering drawings and 3D models |
| **BucketList / format1.json** | HCL's proprietary JSON schema for DFM rule representation. Rules categorized into "buckets" with nested constraint parameters |
| **TaxonomyRule** | Pydantic model representing a single formalized DFM rule in `format1.json` schema |
| **ExpName** | Expression Name — a CAD-namespace dotted path (e.g., `Hole.Depth`, `SheetMetal.Thickness`) identifying a measurable attribute |
| **AllowedParams** | List of `ExpName` paths referenced in formula values (if value is `4.5*SheetMetal.Thickness`, then `SheetMetal.Thickness` must be in `AllowedParams`) |
| **ValidationParamList** | Core pass/fail rule checks within a `Constraints` object |
| **FilterParamList** | Applicability conditions — restrict which feature instances `ValidationParam` applies to |
| **ConditionParamList** | Branch parameters — enables if-then-else conditional rule logic |
| **Bucket** | Structural rule template: SimpleValidation, RangeValidation, ConditionalValidation, DistanceRule, SetMembership, AdditionalInfoValidation, FeatureInteraction, AssemblyRule, ProcessParameter |
| **Anchor Classification** | Comparing text window embeddings against known DFM rule exemplars to filter non-rule text locally |
| **TruthStore** | SQLite database recording immutable source text for every document block — enables verbatim extraction and provenance tracing |
| **Round-robin key rotation** | Cycling through a pool of API keys sequentially for each LLM call, distributing rate-limit consumption |
| **Schema Registry** | `schema_registry.json` — JSON database of all valid `Feature.Attribute` paths per manufacturing domain |
| **Repair loop** | Targeted LLM re-prompt with specific correction instructions based on validator error codes |
| **FAISS** | Facebook AI Similarity Search — in-memory vector index for fast cosine similarity queries |
| **sentence-transformers** | Library providing pre-trained text embedding models running on CPU |
| **Taxonomy V3** | Third generation DFM rule formalization pipeline (V2 addition) producing `format1.json` BucketList output |
| **spaCy** | NLP library used in `windower.py` for sentence-boundary detection respecting engineering unit abbreviations |
| **Groq** | Cloud LLM provider offering fast, OpenAI-compatible inference. Primary LLM provider |
| **FastAPI** | Python web framework with automatic Swagger docs and native async support — replaced Streamlit as the primary interface layer in V2, enabling proper client-server separation |
| **Vite** | Modern JavaScript build tool and development server for the React frontend |
| **LangChain** | LLM orchestration framework used in Core V2 `LLMStructurer` |
| **Pydantic** | Python data validation library used for API models, Taxonomy models, and configuration |

---

*Report prepared as part of RAG-RuleSync V2 project handover to HCL Technologies.*  
*Contributors: Rahul Dewani, Daksh Agarwal, Spandan Kewte, Raj Patle*  
*Document Date: September 5, 2026*  
*Repository state: September 2026 — Final Version*
