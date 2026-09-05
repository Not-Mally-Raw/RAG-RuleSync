# HCL DFM Rule Extraction — Comprehensive Handover & Technical Report

**Project:** RAG-RuleSync — Enterprise DFM Rule Extraction System
**Client:** HCL Technologies
**From:** Phase-3-Final (Previous Team)
**To:** RAG-RuleSync (Current Team)
**Date:** April 21, 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Core Deliverables — What We Cover & Do Not Cover](#3-core-deliverables--what-we-cover--do-not-cover)
4. [System Architecture & Implementation Detail](#4-system-architecture--implementation-detail)
   - 4.1 High-Level Architecture
   - 4.2 Core Extraction Engine (`core/`)
   - 4.3 DFM Rule Refinement Pipeline (`dfm_rule_pipeline/`)
   - 4.4 The DFM Rule Contract (System Invariants)
   - 4.5 Process Flow (End-to-End)
5. [Phase-3-Final: Previous Team's System](#5-phase-3-final-previous-teams-system)
   - 5.1 Architecture & File Structure
   - 5.2 Technology Stack
   - 5.3 Key Issues & Limitations
6. [RAG-RuleSync: Current Team's System](#6-rag-rulesync-current-teams-system)
   - 6.1 Architecture & File Structure
   - 6.2 Technology Stack
   - 6.3 Key Innovations
7. [Detailed Comparison: Phase-3-Final vs RAG-RuleSync](#7-detailed-comparison-phase-3-final-vs-rag-rulesync)
8. [Problems Solved & Our Approach](#8-problems-solved--our-approach)
9. [Technology Justification — What We Used, What Failed, What We Discarded](#9-technology-justification--what-we-used-what-failed-what-we-discarded)
10. [Pipeline Results & Sample Output](#10-pipeline-results--sample-output)
11. [Development Timeline (Monthly Milestones)](#11-development-timeline-monthly-milestones)
12. [Future Roadmap](#12-future-roadmap)
13. [Conclusion](#13-conclusion)

---

## 1. Executive Summary

RAG-RuleSync is an end-to-end NLP/LLM pipeline that extracts structured Design-for-Manufacturability (DFM) rules from unstructured manufacturing documents (PDFs, manuals, specifications). It was built by our team as a **complete architectural overhaul** of the previous team's Phase-3-Final prototype.

The system extracts plain-English manufacturing rules from documents, classifies them into 12 manufacturing domains, converts natural language constraints into CAD-ready mathematical expressions (Abstract Syntax Trees), and exports structured CSV output consumable by downstream CAD compliance software.

**Key Achievement:** The transition eliminated a ~35-package heavyweight stack (PyTorch + TensorFlow + PaddleOCR + Win32COM) in favor of a lean ~15-package LLM-first architecture, while adding capabilities the original system never had — automatic domain classification, 4-stage rule formalization, an AST engine, CI/CD pipelines, automated testing, and production-grade error handling.

---

## 2. Problem Statement

### The Business Challenge

Manufacturing organizations like HCL Technologies maintain extensive design guidelines in unstructured documents — PDFs, engineering manuals, checklists, and specification sheets. These documents contain critical DFM (Design for Manufacturability) rules such as:

- _"Minimum bend radius must be 1.5 times material thickness."_
- _"Wall thickness should be at least 0.8mm for injection molding."_
- _"Distance between hole and bend should be at least 2.5 times sheet metal thickness."_

**Currently**, these rules are:
1. **Manually read** by engineers from hundreds of pages of documentation.
2. **Manually interpreted** to identify constraints, parameters, and applicable conditions.
3. **Manually programmed** into CAD checking/compliance software using proprietary schema formats.

This process is **slow** (weeks per manual), **error-prone** (missed rules, misinterpreted constraints), **expensive** (requires senior engineering expertise), and **impossible to scale** across thousands of specification documents.

### The Technical Challenge

The core technical challenge is a **structured information extraction problem** with the following constraints:

1. **Input Diversity:** Rules exist in heterogeneous formats — embedded in prose paragraphs, bulleted lists, tables, figures, and across multiple pages.
2. **Domain Complexity:** Rules span 12 distinct manufacturing processes (Sheet Metal, Injection Molding, Turning, Milling, Drilling, Die Casting, Assembly, Tubing, Additive Manufacturing, Sheet Metal Forming, Model, General), each with unique feature schemas and attribute vocabularies.
3. **Constraint Complexity:** Rules contain simple numeric limits (`radius >= 1.0mm`), ratio-based constraints (`distance >= 5 × thickness`), compound conditional logic (`bend_radius >= MAX(0.5 × thickness, 0.80mm)`), and parametric relationships.
4. **Output Format:** Extracted rules must be transformed into exact CAD-namespace mathematical expressions using a strict schema (e.g., `Distance.MinValue/SheetMetal.Thickness >= 5.0`).

### What Existed Before

The Phase-3-Final system from the previous team was a **proof-of-concept** that:
- Could classify sentences as rule/non-rule using fine-tuned transformer models.
- Could send classified rules to an LLM for JSON conversion.
- **Could NOT** automatically classify domains, formalize rules into CAD math, validate output, or run without Windows.

---

## 3. Core Deliverables — What We Cover & Do Not Cover

### ✅ What We Cover

| Deliverable | Status | Description |
|-------------|--------|-------------|
| **PDF Text Rule Extraction** | ✅ Complete | Extract DFM rules from unstructured PDF text using LLM with token-aware chunking |
| **Multi-Format Ingestion** | ✅ Complete | Support for PDF, DOCX, TXT, Excel via PyMuPDF, python-docx, pandas |
| **Automatic Domain Classification** | ✅ Complete | AI-driven classification into 12 manufacturing domains |
| **Rule Formalization** | ✅ Complete | Convert natural language to CAD-ready math expressions (`SheetMetal.Thickness >= 0.8`) |
| **4-Stage Refinement Pipeline** | ✅ Complete | Intent → Resolution → Formalization → Validation |
| **AST Engine** | ✅ Complete | Abstract Syntax Tree for compound logic (`MAX()`, `IF/ELSE`) |
| **CAD-Namespace Normalization** | ✅ Complete | Map generic terms to system-specific variables via `DOMAIN_CONFIG` |
| **Streamlit Production UI** | ✅ Complete | Interactive web UI for PDF upload and rule visualization |
| **Batch CLI Processing** | ✅ Complete | Headless batch processing of PDF directories |
| **Python API** | ✅ Complete | Programmatic access for integration |
| **Multi-Provider LLM Failover** | ✅ Complete | Groq → Cerebras automatic failover with smart retry |
| **Resumable Extraction** | ✅ Complete | Chunk-level caching for interrupted runs |
| **Automated Testing** | ✅ Complete | 6 test suites (adapters, canonicalization, pipeline, production system) |
| **CI/CD Pipeline** | ✅ Complete | GitHub Actions (testing, linting, security, Docker) |
| **Documentation** | ✅ Complete | README, Project Description, comprehensive code documentation |

### ❌ What We Do Not Cover (Current Limitations)

| Limitation | Reason | Future Plan |
|------------|--------|-------------|
| **Table Rule Extraction** | Rules embedded within PDF tables are not extracted. System focuses on text-based rules. | Planned — see Future Roadmap |
| **Image/Diagram Rule Extraction** | Rules conveyed visually through diagrams or figures are not captured. | Out of current scope |
| **Containerized Deployment** | While Dockerfile exists in CI/CD, no production Kubernetes/cloud deployment is configured. | Planned — see Future Roadmap |
| **Multi-Language Support** | Only English-language documents are supported. | Not planned currently |
| **Real-Time Streaming** | Processing is batch-oriented; no live WebSocket streaming of results. | Low priority |
| **Fine-Grained Accuracy Metrics** | No formal precision/recall benchmarks against gold-standard datasets. | Planned for next phase |

---

## 4. System Architecture & Implementation Detail

### 4.1 High-Level Architecture

The system consists of two primary macro-components:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│              STAGE 1: Core Extraction Engine (core/)                        │
│                                                                              │
│   Document     Token-Aware     Mega-Prompt    LLM (Groq)    JSON Rules     │
│   Ingestion → Chunking      → (prompts.py) → (ChatGroq)  → (Zero         │
│   (PyMuPDF)   (tiktoken)                                     Mutation)     │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              STAGE 2: DFM Rule Pipeline (dfm_rule_pipeline/)                │
│                                                                              │
│   Stage 1          Stage 2          Stage 3            Stage 4              │
│   Intent      →    Resolution   →   Formalization  →   Self-Validation     │
│   Extraction       (Domain/         (Equations /       (LLM Self-          │
│   (Quantify?)       Category)        AST Engine)        Correction)        │
│                                                                              │
│                        ↓ Final Output                                       │
│                 Formatter → CAD-Ready CSV (_FINAL_FORMATTED.csv)            │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Core Extraction Engine (`core/`)

The Core Engine is responsible for ingesting documents, chunking text, and prompting the LLM to extract Level-1 raw rules with zero post-processing mutation.

| File | Purpose |
|------|---------|
| `prompts.py` | **Single source of truth.** Contains the `compiler_prompt` — a 450-line mega-prompt that maps 12 manufacturing domains, defines 3 constraint types (applicability, dimensional, relational), and provides 8 few-shot examples. |
| `enhanced_rule_engine.py` | LangChain integration (1,723 lines). Chains prompts to `ChatGroq` using `JsonOutputParser`. Handles chunking, token-aware windowing, rate limiting, model fallback, deduplication, TF-IDF quality scoring, and chunk caching. |
| `production_system.py` | Central facade (28 KB). Wraps extraction logic so external components don't manage async states. Supports both fast and enhanced pipelines. |
| `rule_extraction.py` | Foundational toolkit (42 KB). Contains `RuleExtractionSettings`, `AsyncRateLimiter`, `DocumentLoader`, and the fast extraction pipeline. |
| `interfaces.py` | Protocol-based interfaces following SOLID Dependency Inversion Principle. Defines `ITextLoader`, `IChunker`, `IRuleExtractor`, `IExporter`. |
| `adapters.py` | Adapter pattern implementations. Enables swapping loaders, chunkers, or LLM providers without altering core logic. |
| `orchestrator.py` | Thin DI-based coordinator composing loader → chunker → extractor → exporter. |
| `document_processor.py` | Async document processing facade with manufacturing keyword density analysis. |
| `chunk_cache.py` | File-backed chunk cache for resumable extraction. Atomic writes prevent corruption on interruption. |

### 4.3 DFM Rule Refinement Pipeline (`dfm_rule_pipeline/`)

This is the secondary reasoning module that takes raw LLM output and converts it into CAD-ready math.

#### Pipeline Stages

| Stage | File | Purpose |
|-------|------|---------|
| **Stage 1: Intent** | `stage1_intent_extraction.py` | LLM classifies: Is the rule quantifiable? Does it require geometry reasoning? Tolerance specification? |
| **Stage 2: Resolution** | `stage2_rule_resolution.py` | Categorizes into Attribute, Geometry, or Tolerance. Maps to correct 12-domain schema key. |
| **Stage 2a** | `stage2a_schema_consistency.py` | Validates mentioned objects/attributes against the domain schema. |
| **Stage 2b** | `stage2b_geometry_resolution.py` | For distance/spatial rules: extracts entity pairs and distance functions. |
| **Stage 2c** | `stage2c_tolerance_spec.py` | For tolerance rules: formalizes into `Tolerance()`, `Limits()`, `GDT()` representations. |
| **Stage 3: Formalization** | `stage3_formalization.py`, `stage3_attribute_formalization.py` | Creates the raw mathematical formula using schema-compliant variable names. |
| **Stage 4: Validation** | `stage4_self_validation.py` | LLM self-corrects by checking schema membership, formalism correctness, and variable validity. |

#### AST Engine (`ast_engine/`)

For rules with compound logic (e.g., `bend_radius >= MAX(0.5 * material_thickness, 0.80 mm)`), simple regex fails. The AST Engine handles this:

| File | Purpose |
|------|---------|
| `ast_nodes.py` | Defines `LogicOp` (max/min/and/or), `ComparisonOp` (>=, <=, ==), `MathLeaf` (expressions), `Constant` (numeric values) |
| `ast_builder.py` | Constructs syntax trees from LLM output |
| `ast_evaluator.py` | Evaluates trees against input parameters |
| `ast_validator.py` | Enforces operator validity and schema compliance |

#### Formatter (`formatter.py`)

The final normalization step:
- **`DOMAIN_CONFIG`**: Maps 12+ domain aliases to canonical CAD variable names (e.g., `Thickness` → `SheetMetal.Thickness` in Sheet Metal domain, `InjectionMolding.NominalThickness` in Injection Molding domain).
- **`normalize_algebra()`**: Algebraically rearranges expressions to canonicalize ratios (e.g., `Distance >= 5 * Thickness` → `Distance/Thickness >= 5`).
- **`generate_semantic_name()`**: Auto-generates human-readable rule names (e.g., "Hole to Bend Clearance", "Boss Draft Angle Limit").

#### Schema Layer (`schema/`)

| File | Purpose |
|------|---------|
| `features.py` / `feature_schema.py` | Complete feature/attribute definitions for all 12 manufacturing domains (353 lines of schema covering Assembly, Additive, Die Cast, Drill, General, Injection Moulding, Mill, Model, Sheetmetal, SMForm, Tubing, Turn) |
| `domain_definitions.py` | Rich semantic descriptions (12 KB) of every object in each domain — enabling the LLM to semantically match rules, not just keyword-match |
| `geometry_schema.py` | Distance/spatial relationship type definitions |
| `tolerance_schema.py` | Tolerance specification type definitions |
| `ast_schema.py` | AST serialization/deserialization |

#### LLM Client (`llm/`)

| File | Purpose |
|------|---------|
| `client.py` | Multi-provider LLM client with Groq (primary) → Cerebras (secondary) failover, intelligent wait-time extraction from rate-limit errors, and infinite retry loop |
| `prompts.py` | 7 specialized prompts for each pipeline stage: Intent, Domain Resolution, Geometry Math, Tolerance, Formalization, Self-Validation, Attribute Math (393 lines) |

### 4.4 The DFM Rule Contract (System Invariants)

Every extracted rule conforms to a non-code contract:

- **Rule (atomic):** Single, atomic manufacturing invariant.
- **Scope Domain:** Must define `{process, item, feature}`.
- **Applicability (Hard Gates):** Binary conditions (material, process, feature presence) outside which the rule must not evaluate. Example: `material == "low carbon steel"`.
- **Constraints:** Evaluatable mathematical expressions with subject, operator (`<`, `<=`, `>=`, `==`, `!=`, `between`, `±`), value, and unit.
- **Severity:**
  - `ENFORCEABLE` — deterministic numeric limits.
  - `ADVISORY` — heuristics like "avoid" or "for ease of...".
- **Validation State:**
  - `ENFORCEABLE` — when evaluatable constraints exist.
  - `ADVISORY_ONLY` — when severity = ADVISORY.
  - `INCOMPLETE` — when constraints are missing or ill-formed.

### 4.5 Process Flow (End-to-End)

1. **Document Upload** → User uploads `Spec.pdf` via Streamlit UI, CLI, or Python API.
2. **Ingestion** → `DocumentLoader` returns plain text stripped of boilerplate.
3. **Chunking** → `tiktoken` slices text into token-aware windows (800 tokens with 400 overlap) to respect LLM context limits.
4. **LLM Extraction** → Groq model (default: `meta-llama/llama-4-scout-17b-16e-instruct`) extracts rules using the Mega-Prompt (`core/prompts.py`).
5. **JSON Structuring** → LLM outputs `ManufacturingRule` JSON arrays with `rule_text`, `dimensional_constraints`, `relational_constraints`, and `applicability_constraints`.
6. **Refinement Pipeline** →
   - *Stage 1 (Intent):* Determines if a rule is quantifiable, geometric, or attribute-based.
   - *Stage 2 (Resolution):* Evaluates the specific category/domain using `features_dict`.
   - *Stage 3 (Formalization):* Translates constraints to equations (e.g., `Thickness >= 0.8`).
   - *Stage 4 (Self Validation/AST):* Validates operator/operand and schema compliance.
7. **CAD Normalization** → `formatter.py`'s `DOMAIN_CONFIG` converts generic terms to system-specific variables.
8. **Export** → Final `_FINAL_FORMATTED.csv` output for CAD checking software consumption.

---

## 5. Phase-3-Final: Previous Team's System

### 5.1 Architecture & File Structure

A monolithic, page-based Streamlit application with a linear manual workflow:

```
Phase-3-Final/
├── app.py                            # Streamlit entrypoint — downloads 5 HF models at startup
├── requirements.txt                  # ~35 heavy dependencies
├── data/                             # Sample PDFs + classification dataset
├── extractors/
│   ├── text.py                       # PDFMiner text extraction
│   ├── image.py                      # PyMuPDF image extraction
│   └── table.py                      # DETR + PaddleOCR + Win32COM table extraction (591 lines)
├── generators/
│   ├── features.py                   # Domain schema definitions (12 domains)
│   ├── classification_generator.py   # DistilBERT fine-tuning script
│   └── classification_generator2.py  # Electra/MiniLM fine-tuning script
└── pages/
    ├── uploader.py, textpreview.py, image_previews.py, table_preview.py
    ├── classification.py             # Binary rule/non-rule classification using HF models
    └── rule_generation.py            # LLM rule parsing with Groq/Cerebras
```

**12 files, ~2,015 lines of code, 1 developer (Rakrocks18), 6 commits over 11 days (July 2025).**

### 5.2 Technology Stack

~35 dependencies including PyTorch 2.7, TensorFlow 2.19, Keras 3.10, PaddleOCR, EasyOCR, Win32COM, HuggingFace Transformers, Sentence-Transformers, and 5 fine-tuned classification models hosted on HuggingFace Hub.

### 5.3 Key Issues & Limitations

| # | Issue | Severity |
|---|-------|----------|
| 1 | Hardcoded API keys (Groq, Cerebras, HuggingFace) in source code | 🔴 Critical |
| 2 | Windows-only: Win32COM at module-level import crashes on Linux/macOS | 🔴 Critical |
| 3 | 5 fine-tuned models required (~GBs download before app starts) | 🟡 High |
| 4 | Manual 4-step workflow — no end-to-end automation | 🟡 High |
| 5 | No rule formalization — raw LLM JSON is the final output | 🟡 High |
| 6 | No automatic domain classification — user must manually type `rule_type` | 🟡 High |
| 7 | No `.env` support, no environment variables | 🟡 High |
| 8 | Dual DL frameworks (PyTorch + TensorFlow) with TensorFlow unused | 🟡 Medium |
| 9 | Zero tests, no CI/CD, no documentation | 🟡 Medium |
| 10 | No rate limiting — hardcoded `time.sleep(2)` / `time.sleep(6)` | 🟡 Medium |
| 11 | Fragile table extraction with memory leaks (matplotlib figures not closed) | 🟡 Medium |
| 12 | Commented-out code, unused imports throughout | 🟢 Low |

---

## 6. RAG-RuleSync: Current Team's System

### 6.1 Architecture & File Structure

```
RAG-RuleSync/
├── README.md, Project_description.md  # Comprehensive documentation
├── requirements.txt                    # 15 lean dependencies
├── simple_streamlit_app.py             # Production Streamlit UI (293 lines)
├── batch_extract_rules.py              # CLI batch processing
├── .github/workflows/ci-cd.yml        # Full CI/CD pipeline
│
├── core/                               # Stage 1: Extraction Engine (9 files)
│   ├── prompts.py                      # Mega-Prompt — single source of truth
│   ├── enhanced_rule_engine.py         # LangChain integration (1,723 lines)
│   ├── production_system.py            # Central facade
│   ├── rule_extraction.py              # Foundational toolkit
│   ├── interfaces.py, adapters.py      # SOLID DIP
│   ├── orchestrator.py                 # DI coordinator
│   ├── document_processor.py           # Async document facade
│   └── chunk_cache.py                  # Resumable extraction cache
│
├── dfm_rule_pipeline/                  # Stage 2: Rule Refinement (25+ files)
│   ├── pipeline.py, formatter.py       # Pipeline + CAD normalization
│   ├── stages/ (8 files)               # 4-stage refinement pipeline
│   ├── ast_engine/ (4 files)           # AST for compound logic
│   ├── schema/ (6 files)              # Domain knowledge base
│   ├── llm/ (3 files)                 # Multi-provider LLM client
│   └── utils/ (4 files)              # Helpers
│
├── scripts/quick_extract.py            # CLI quick extraction
└── tests/ (6 files)                    # Automated test suites
```

**40+ files, ~10,000+ lines of code, 4 developers, 30 commits over 5 months.**

### 6.2 Technology Stack

| Category | Technology |
|----------|-----------|
| **LLM Orchestration** | LangChain + LangChain-Groq |
| **LLM Providers** | Groq (primary) + Cerebras (failover) via OpenAI-compatible SDK |
| **PDF Processing** | PyMuPDF |
| **Text Chunking** | tiktoken (token-aware) |
| **Data Validation** | Pydantic, Pydantic-Settings |
| **Analytics** | scikit-learn (TF-IDF, KMeans for dedup/clustering) |
| **Text Analysis** | textstat (readability metrics) |
| **Logging** | structlog (structured JSON) |
| **Configuration** | python-dotenv |
| **Testing** | pytest, pytest-asyncio |
| **CI/CD** | GitHub Actions + Dependabot |

**15 dependencies total. No PyTorch. No TensorFlow. No PaddleOCR. No Win32COM.**

### 6.3 Key Innovations

1. **Zero-Mutation Extraction Guarantee:** LLM output at Stage 1 is saved verbatim as JSON. No Pydantic coercion, no deduplication at extraction time. All post-processing is strictly delegated to the DFM pipeline.
2. **Mega-Prompt as Single Source of Truth:** A single 450-line prompt defines the entire extraction schema, classification rules, and output format — replacing multiple disjointed prompt strings.
3. **4-Stage DFM Refinement Pipeline:** Intent → Resolution → Formalization → Validation — each stage is an independent, testable module.
4. **AST Engine:** Handles compound conditional logic that simple regex cannot parse.
5. **Multi-Provider LLM Failover:** Automatic Groq → Cerebras failover with intelligent wait-time parsing from error messages.
6. **Resumable Chunk Caching:** `FileChunkCache` allows interrupted extractions to resume without re-processing.
7. **Semantic Domain Definitions:** Rich technical descriptions (12 KB) enable LLM semantic matching rather than keyword matching.
8. **SOLID Architecture:** Protocols, Adapters, Dependency Injection — components are swappable without modifying core logic.

---

## 7. Detailed Comparison: Phase-3-Final vs RAG-RuleSync

| Dimension | Phase-3-Final | RAG-RuleSync |
|-----------|---------------|--------------|
| **Approach** | Supervised ML classification + LLM | Pure LLM with RAG architecture |
| **Classification** | 5 fine-tuned models (binary rule/not-rule) | LLM zero-shot extraction via prompt engineering |
| **Domain Assignment** | Manual — user types `rule_type` | Automatic — LLM + AI Category Judge |
| **Rule Formalization** | ❌ None — raw LLM JSON output | ✅ 4-stage pipeline + AST engine → CAD math |
| **Variable Normalization** | No CAD namespace mapping | `DOMAIN_CONFIG` → strict CAD paths |
| **Document Ingestion** | PDF only (PDFMiner + DETR + PaddleOCR + Win32COM) | PDF, DOCX, TXT, Excel (PyMuPDF, python-docx, pandas) |
| **Chunking** | Sentence-level regex | Token-aware windowing (tiktoken) |
| **LLM Rate Limiting** | `time.sleep(2)` | Intelligent retry with error parsing |
| **LLM Failover** | None (manual provider selection) | Automatic Groq → Cerebras → infinite retry |
| **Authentication** | Hardcoded API keys | `.env` via python-dotenv |
| **Entry Points** | 1 (Streamlit) | 4 (Streamlit, Batch CLI, Python API, Quick Extract) |
| **Dependencies** | ~35 packages (PyTorch + TF) | ~15 packages (lean) |
| **Platform** | Windows-only | Cross-platform |
| **Tests** | 0 | 6 test suites |
| **CI/CD** | None | GitHub Actions (test, lint, security, Docker) |
| **Documentation** | None | README + Architecture doc (9.4 KB) |
| **Code** | 12 files, ~2,015 LOC | 40+ files, ~10,000+ LOC |
| **Team** | 1 developer, 6 commits | 4 developers, 30 commits |

---

## 8. Problems Solved & Our Approach

### Problem 1: Hardcoded Secrets

**Issue:** API keys for Groq (`gsk_aTac...`), Cerebras (`csk-hnp6...`), and HuggingFace (`hf_rHBDH...`) were committed directly in source code.

**Approach:** Implemented `python-dotenv` for environment-based configuration. All secrets load from `.env` (which is `.gitignore`'d). The `EnhancedConfig` class uses `pydantic-settings` with `env_file = ".env"`. Additionally, the engine explicitly rejects placeholder or hardcoded keys at startup:
```python
if self.config.groq_api_key.lower().startswith("sk-groq") or \
   self.config.groq_api_key == "your_actual_groq_api_key_here":
    raise ValueError("GROQ_API_KEY appears to be placeholder or hardcoded.")
```

### Problem 2: Windows-Only Execution

**Issue:** `extractors/table.py` instantiated Win32COM globally (`word = win32com.client.Dispatch("Word.Application")`), making the system completely Windows-locked and preventing CI/CD on Linux runners.

**Approach:** Eliminated the entire Win32COM + DETR + PaddleOCR table extraction pipeline. The system now focuses on text-based rule extraction using PyMuPDF, which is cross-platform. This decision was justified because DFM rules are primarily textual — table-based rules are a future enhancement.

### Problem 3: Binary Classifier Bottleneck

**Issue:** Required downloading 5 fine-tuned transformer models (~GBs) from HuggingFace before the app could start. The classifier only answered "is this a rule?" but could not determine domain or extract constraints.

**Approach:** Replaced the entire classification step with **prompt-engineered LLM extraction**. The 450-line Mega-Prompt in `core/prompts.py` instructs the LLM to simultaneously: (1) identify rules from raw text, (2) classify into 12 domains, (3) extract all constraint types. This eliminated all local model dependencies.

### Problem 4: Manual Domain Assignment

**Issue:** Users had to manually type the manufacturing domain for every rule in a Streamlit data editor.

**Approach:** Implemented automatic classification at three levels:
- **Level 1:** 5-step decision tree in the Mega-Prompt (check document title → process keywords → feature keywords → cross-cutting patterns → fallback to General).
- **Level 2:** AI Category Judge (`CATEGORY_JUDGE_PROMPT`) with domain fingerprints for direct text input.
- **Level 3:** `stage2_rule_resolution.py` validates and corrects using semantic matching against `domain_definitions.py`.

### Problem 5: No Rule Formalization

**Issue:** Raw LLM JSON was the final output — no validation, normalization, or conversion to CAD-ready expressions.

**Approach:** Built the entire `dfm_rule_pipeline/` module with:
- 4-stage pipeline (Intent → Resolution → Formalization → Validation).
- `formatter.py` with `DOMAIN_CONFIG` for 12-domain variable substitution.
- `normalize_algebra()` for algebraic canonicalization.
- AST engine for compound conditional logic.

### Problem 6: No Rate Limiting or Failover

**Issue:** Hardcoded `time.sleep(2)` / `time.sleep(6)` with no retry logic or provider failover.

**Approach:** Built `LLMClient` with:
- Automatic Groq → Cerebras failover.
- Intelligent wait-time parsing from error messages (extracts "try again in 17m18s" from Groq 429 errors).
- Infinite retry loop that never crashes the pipeline.
- `FileChunkCache` for resumable extraction so progress isn't lost during rate-limit pauses.

### Problem 7: No Testing or CI/CD

**Issue:** Zero tests, no automation.

**Approach:** Added:
- 6 pytest test files covering adapters, canonicalization, enhanced candidates, layer-1 pipeline, and full production system integration.
- GitHub Actions CI/CD with multi-Python testing, `flake8`/`black`/`isort` linting, `bandit`/`safety` security scanning, coverage reporting, and Docker image builds.
- Dependabot for automated weekly dependency updates.

### Problem 8: Pydantic Over-Validation (Internal Refactor)

**Issue:** In early RAG-RuleSync versions (pre-January 2026), rules were heavily validated by Pydantic parsers, which silently mutated LLM output and ran through semantic deduplication and clustering inside the extraction loop.

**Approach:** Major refactor in January 2026:
- Replaced Pydantic-based output parsing with `JsonOutputParser` (LangChain).
- Consolidated all prompt logic into `core/prompts.py` as the Single Source of Truth.
- Outputs now flow verbatim from LLM to `.json` files ("Zero Mutation" guarantee).
- All post-processing delegated strictly to `dfm_rule_pipeline/`.

---

## 9. Technology Justification — What We Used, What Failed, What We Discarded

### ✅ Technologies We Use & Why

| Technology | Justification |
|-----------|---------------|
| **LangChain + LangChain-Groq** | Provides structured prompt chaining, `ChatPromptTemplate` for system/human message separation, and `JsonOutputParser` for reliable JSON extraction without heavy Pydantic coercion. Chosen over raw API calls for maintainability and composability. |
| **Groq API** | Offers extremely fast LLM inference (low latency) with generous free-tier rate limits. Primary provider for all extraction and refinement calls. |
| **Cerebras API** | Secondary failover provider when Groq hits daily token limits. Provides automatic load balancing without user intervention. |
| **OpenAI-compatible SDK** | Both Groq and Cerebras expose OpenAI-compatible endpoints, allowing a single `LLMClient` class to interface with both using the same code. |
| **PyMuPDF (fitz)** | Industry-standard PDF text extraction. Fast, cross-platform, handles complex layouts. Replaced PDFMiner which had issues with CID character encoding. |
| **tiktoken** | OpenAI's tokenizer ensures chunks respect LLM context window limits precisely. Prevents mid-sentence truncation that sentence-level regex splitting caused. |
| **Pydantic + Pydantic-Settings** | Used strictly for configuration validation (`EnhancedConfig`) and data models (`ManufacturingRule`). Not used for LLM output coercion (that was removed in the Jan 2026 refactor). |
| **scikit-learn (TF-IDF + KMeans)** | Used for lightweight semantic deduplication and rule clustering in post-processing. TF-IDF cosine similarity detects near-duplicate rules. KMeans groups similar rules (disabled by default via `enable_rule_clustering: bool = False`). |
| **textstat** | Provides readability metrics (`flesch_reading_ease`, `automated_readability_index`) for document analysis and rule complexity scoring. Lightweight alternative to full NLP libraries. |
| **structlog** | Structured JSON logging for production monitoring. Enables log aggregation and search without parsing unstructured log strings. |
| **python-dotenv** | Secure, standard approach for managing API keys and configuration. Prevents accidental key commits. |
| **pytest + pytest-asyncio** | Standard Python testing framework with async support for testing the `asyncio`-based extraction engine. |
| **GitHub Actions** | Industry-standard CI/CD. Multi-job pipeline: test → lint → security → Docker build → performance benchmark. |
| **Dependabot** | Automated weekly dependency updates with grouped PRs for minor/patch versions. Prevents dependency rot. |

### ❌ Technologies That Failed / Were Abandoned

| Technology | What Happened | Why It Failed | Evidence |
|-----------|---------------|---------------|----------|
| **Qdrant (Vector Store)** | Initially planned for RAG-based rule retrieval. Code stubs exist (`use_qdrant=False` parameter in `ProductionRuleExtractionSystem`). | The vector store retrieval added latency and complexity without improving extraction quality. The Mega-Prompt approach with direct LLM extraction proved more effective than similarity-search-based RAG. | `production_system.py` line 102: `use_qdrant: bool = False`, always disabled. `scripts/quick_extract.py` line 139: `use_qdrant=False`. |
| **FAISS** | Not used. | Qdrant was tried first; when vector-store RAG was abandoned, FAISS was never needed. | No references found in codebase. |
| **Pydantic Output Parsing** | Used in early versions (pre-Jan 2026) for LLM output validation. | Pydantic validators silently coerced/mutated LLM output, causing data integrity issues. Rules were being altered during extraction. | `Project_description.md`: "The Pydantic logic was removed in favor of `JsonOutputParser`." Commit `1d378d4` (Jan 8, 2026): "Refactor: Restore mega-prompt as single source of truth with JSON-only output." |
| **Semantic Deduplication + KMeans Clustering (in extraction loop)** | Originally ran inside the extraction loop. | Added latency and aggressively deduplicated rules, sometimes removing valid variants. | `enhanced_rule_engine.py` line 462: `enable_rule_clustering: bool = False` (feature disabled). Still exists as optional post-processing but disabled by default. |
| **EnhancedVectorManager** | Type hints and conditional imports exist. | Vector-enhanced extraction was experimental and never stabilized. | `enhanced_rule_engine.py` line 41: `from .enhanced_vector_utils import EnhancedVectorManager` (TYPE_CHECKING only). |
| **spaCy** | Referenced in CI/CD (`python -m spacy download en_core_web_sm`). | Not actively used in the current pipeline. Appears to be a CI/CD artifact from an earlier version that used NER for entity extraction. | Only in `ci-cd.yml`; no `import spacy` in any Python file. |
| **PyTorch + TensorFlow** (Phase-3) | Powered the 5 fine-tuned binary classifiers. | Massive dependency footprint for a binary yes/no question that the LLM solves better with zero-shot prompting. | Completely eliminated in RAG-RuleSync. |
| **PaddleOCR + DETR** (Phase-3) | Table structure recognition + cell OCR. | Windows-only, compute-heavy, fragile (memory leaks from matplotlib), and DFM rules are primarily text-based. | Completely eliminated in RAG-RuleSync. |
| **Win32COM** (Phase-3) | PDF→DOCX conversion for native table parsing. | Windows-locked. Makes CI/CD impossible on Linux runners. | Completely eliminated in RAG-RuleSync. |
| **HuggingFace Hub model downloads** (Phase-3) | Auto-downloaded 5 classification models on startup. | Multi-GB downloads, slow startup, model versioning issues. | Completely eliminated in RAG-RuleSync. |

### ⚙️ Technologies We Kept From Phase-3 (Evolved Form)

| Technology | Phase-3 Usage | RAG-RuleSync Usage | Change |
|-----------|---------------|-------------------|--------|
| **Streamlit** | Multi-page app with 6 pages | Single-page production UI with tabs | Simplified & modernized |
| **Groq/Cerebras** | Manual provider selection, hardcoded keys | Multi-provider failover, `.env`-based auth | Major upgrade |
| **`features_dict`** (12-domain schema) | Used only in prompt generation | Used across entire pipeline: prompt gen, domain resolution, schema validation, formatting | Central to architecture |
| **Pandas** | DataFrame operations | Rule data handling + CSV export | Same role |

---

## 10. Pipeline Results & Sample Output

### Level-1 Extraction Output (from `core/`)

When processing the HCL sheet metal rules dataset, the pipeline extracts rules in this JSON format:

```json
{
  "source_pdf": "DFXRuleSample.xlsx - SheetMetal.csv",
  "rule_count": 20,
  "rules": [
    {
      "rule_text": "Distance between bridges should be atleast 4.5 times sheet thickness",
      "rule_type": "SheetMetal",
      "applicability_constraints": {
        "material": "any",
        "process": "sheet metal fabrication",
        "feature": "bridge",
        "location": "relative positioning"
      },
      "dimensional_constraints": ["Distance >= 4.5 times sheet thickness"],
      "relational_constraints": ["Distance between bridge features"]
    }
  ]
}
```

### Final Formatted Output (from `dfm_rule_pipeline/formatter.py`)

After the 4-stage refinement pipeline, the output is a CAD-ready CSV:

```csv
RuleText,Status,DecisionCode,RuleCategory,dfm_json
"Distance between bridges should be at least 4.5 times sheet thickness",Success,formalized,Sheet Metal,"{""RuleCategory"":""Sheet Metal"",""Name"":""Bridge Spacing Requirement"",""Feature1"":""Distance"",""Object1"":""Bridge"",""Object2"":""Bridge"",""ExpName"":""Distance.MinValue/SheetMetal.Thickness"",""Operator"":"">="",""Recom"":4.5}"
```

### Test Dataset Results

From the test fixtures (`dfm_rule_pipeline/tests/final.json`):

| Metric | Value |
|--------|-------|
| **Documents Processed** | 2 (SheetMetal + SMForm rule sets) |
| **Total Rules Extracted** | 26 |
| **SheetMetal Rules** | 20 |
| **SMForm Rules** | 6 |
| **Domain Classification Accuracy** | 100% (all rules correctly assigned to SheetMetal / SMForm) |
| **Constraint Extraction Rate** | 100% (all dimensional constraints captured) |
| **Relational Extraction Rate** | 100% (all multi-feature relationships identified) |
| **Material-Specific Rules** | Correctly identified (e.g., "6061-T6" material for flange rules) |

### Sample Rules Successfully Formalized

| Rule Text | CAD Expression | Domain |
|-----------|---------------|--------|
| "Distance between bridges should be at least 4.5 times sheet thickness" | `Distance.MinValue/SheetMetal.Thickness >= 4.5` | Sheet Metal |
| "Card guide length should be at most 127.0 mm" | `CardGuide.Length <= 127.0` | Sheet Metal |
| "Bend radius should be at least 1.3 times the sheet metal nominal thickness" | `Bend.Radius/SheetMetalForm.NominalThickness >= 1.3` | SMForm |
| "For part with material 6061-T6, flange radius should be at least 1.0 mm" | `Flange.Radius >= 1.0` (with constraint: `PartBody.Material == 6061-T6`) | Sheet Metal |
| "Distance between curl and bends should be at least 4.5× sheet thickness plus twice rolled hem radius" | `(Distance.MinValue - 2*RolledHem.Radius)/SheetMetal.Thickness >= 4.5` | Sheet Metal |

---

## 11. Development Timeline (Monthly Milestones)

### Phase-3-Final (Previous Team)

| Period | Milestone |
|--------|-----------|
| **July 2025** | Initial commit. Built Streamlit multi-page app, binary classification with 5 HF models, Groq/Cerebras rule parsing. 6 commits, single developer. Development stopped. |

### RAG-RuleSync (Our Team)

| Period | Key Achievement |
|--------|----------------|
| **October 2025** | Project inception. Initial working RAG system built and imported. First end-to-end rule extraction from PDFs without classification models. Project description documented. |
| **November 2025** | SOLID principles refactoring — introduced Protocol interfaces, Adapter pattern, and Dependency Injection. Started new branch (`nov-10-update`) with clean history. |
| **January 2026** | **Major milestone month.** Consolidated mega-prompt as single source of truth. Removed Pydantic output coercion in favor of `JsonOutputParser`. Added DFM normalization pipeline (`dfm_rule_pipeline/`). Level-1 prompt tuning achieved 64-rule extraction target. Switched to GPT-OSS-20B model. Dependabot activated with dependency bumps (numpy, langchain, plotly). |
| **February 2026** | Rule formatting architecture finalized. Formatter rectified with proper `DOMAIN_CONFIG` variable substitution. Pipeline integration testing. |
| **March 2026** | Final testing and validation. Redundant files cleaned up. Semantic domain keyword mapping added. Single-rule entry support added. Pipeline stable and verified on HCL test datasets. |

---

## 12. Future Roadmap

### 12.1 Known Issues to Address

| Issue | Impact | Plan |
|-------|--------|------|
| **Advisory Rules Skipped** | Stage 1 marks non-quantifiable rules as "Skipped" — advisory rules (e.g., "avoid sharp corners") are not formalized. | Implement an advisory rule handler that captures qualitative guidance as metadata without requiring mathematical expressions. |
| **Rate Limit Sensitivity** | Heavy reliance on free-tier Groq API means large document batches can hit daily token limits, requiring hour-long waits. | Implement token budgeting, smarter batch scheduling, and explore self-hosted LLM options (e.g., Ollama with local models). |
| **Schema Gaps** | Rules referencing objects/attributes not in the 12-domain `features_dict` fall through as "Schema Gap" failures. | Continuously expand the feature schema based on new DFM documents. Build an automated schema gap reporter. |
| **No Formal Accuracy Benchmarks** | Pipeline results are verified manually; no automated precision/recall metrics against gold-standard datasets. | Create a formal benchmarking suite with annotated test sets and automated scoring. |
| **spaCy Dependency in CI** | `ci-cd.yml` downloads `en_core_web_sm` but spaCy isn't actually used. This wastes CI time. | Remove the spaCy step from CI/CD. |

### 12.2 Planned Enhancements

#### Table Rule Extraction
Many manufacturing documents contain critical rules inside tables (e.g., tolerance charts, material-thickness lookup tables). Currently, these are missed because the pipeline only processes text.

**Plan:**
- Integrate table detection and extraction (using libraries like `pdfplumber` or `camelot` instead of the Phase-3 DETR + PaddleOCR approach) to identify tabular data in PDFs.
- Develop a specialized table-to-rules LLM prompt that converts structured table data into individual atomic rules.
- Merge table-extracted rules into the existing DFM pipeline for formalization.

#### Production Deployment
The pipeline currently runs locally or in CI/CD. It is not deployed as a production service.

**Plan:**
- Create a production-ready `Dockerfile` with optimized multi-stage builds.
- Deploy to a cloud platform (AWS/GCP/Azure) using containerized services.
- Add a FastAPI REST endpoint alongside the Streamlit UI for API-driven integrations.
- Implement proper authentication, rate limiting, and monitoring (Prometheus/Grafana).
- Configure Kubernetes manifests or docker-compose for reliable orchestration.

#### Additional Future Items
- **Multi-document cross-referencing:** Track rules that span multiple documents and identify conflicts.
- **Rule versioning:** Maintain version history of extracted rules as source documents are updated.
- **Feedback loop:** Allow engineers to correct misclassified rules and feed corrections back to improve prompts.
- **Expanded domain coverage:** Add new manufacturing domains as HCL's scope grows (e.g., Forging, Stamping, Surface Treatment).

---

## 13. Conclusion

The transition from Phase-3-Final to RAG-RuleSync represents a **complete architectural overhaul** — not an incremental update. Every major limitation of the original system has been addressed:

| Dimension | Before (Phase-3) | After (RAG-RuleSync) |
|-----------|-------------------|----------------------|
| **Approach** | Supervised ML + LLM | Pure LLM with RAG |
| **Automation** | Manual 4-step workflow | End-to-end automated |
| **Output** | Raw LLM JSON | CAD-ready formalized math |
| **Dependencies** | ~35 heavy packages | ~15 lightweight |
| **Security** | Hardcoded API keys | `.env`-based config |
| **Testing** | 0 tests | 6 test suites + CI/CD |
| **Documentation** | None | README + 9.4 KB arch doc |
| **Platform** | Windows-only | Cross-platform |
| **Team** | 1 dev, 6 commits | 4 devs, 30 commits |
| **Quality** | Prototype | Production-grade |

The system is now a functional, documented, tested, and CI/CD-enabled pipeline that transforms unstructured manufacturing documents into structured CAD-ready constraints. The identified future work items (table extraction, production deployment, accuracy benchmarking) represent natural extensions of an already stable foundation.

---

*Report prepared by the RAG-RuleSync development team.*
*Contributors: Rahul Dewani, Daksh Agarwal, Spandan Kewte, Raj Patle*
*Last updated: April 21, 2026*
