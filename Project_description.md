# RAG-RuleSync V2: Next-Generation DFM Rule Extraction & Formalisation

## Overview

RAG-RuleSync is an enterprise Design-for-Manufacturability (DFM) rule extraction pipeline built for HCL Technologies. It blends local deterministic processing, local AI embeddings, and intelligent LLM structuring to transform unstructured PDF documents into CAD-ready constraints in the **BucketList `format1.json` schema**.

---

## 1. High-Level System Architecture

The system splits responsibilities into two distinct, sequential parts:

### Part 1: Document Extraction Engine (`core_v2/`)
1. **Parser (`parser.py`)**: Uses `PyMuPDF` to parse PDFs, identifying headers, paragraphs, and lists. It creates `StructuralBlock` objects, tagging each block with its hierarchical `section_title`.
2. **Truth Store (`truth_store.py`)**: A thread-safe SQLite database storing the exact, immutable text of every block and sliding window. Every extracted rule can be traced back to exact character indices in the source PDF.
3. **Windower (`windower.py`)**: Uses `spaCy` to safely split paragraphs into overlapping `TextWindow` objects without breaking engineering units (e.g., stopping mid-sentence at "0.3 in.").
4. **Local Embeddings (`embeddings.py`) & Vector Store (`vector_store.py`)**: Generates 384-dim dense embeddings using `all-MiniLM-L6-v2` locally on CPU and indexes them in an in-memory `FAISS` vector store.
5. **Anchor Classification (`dfm_anchors.py`)**: Scores each window vector against known DFM Anchor rules via cosine similarity. Windows below threshold (0.25) are discarded, **filtering ~80% of irrelevant boilerplate locally before any cloud LLM call**.
6. **Candidate Assembler (`candidate_assembler.py`) & LLM Structurer (`llm_structurer.py`)**: Groups surviving candidate windows by parent `block_id` and prompts Groq LLM for verbatim extraction with section-title context resolution.

### Part 2: Version 3 Rule Formalisation Pipeline (`dfm_rule_pipeline/taxonomy/`)
1. **Bucket & Domain Classification (`bucket_classifier.py`)**: 3-tier classifier (Regex → Embedding Cosine → LLM Fallback) categorizing the rule into one of 12 domains and 9 structural buckets.
2. **Dynamic Prompt Building (`prompt_context.py`)**: Injects domain schema paths from `schema_registry.json` and bucket exemplars.
3. **Flat LLM Extraction (`llm_extractor.py`)**: Extracts an intermediate flat data structure representing features, objects, validation expressions, and conditional branches.
4. **Deterministic Schema Assembly (`assembler.py`)**: Assembles the flat extraction into the deeply-nested `format1.json` (`TaxonomyRule`) schema.
5. **17-Check Schema Validation (`validator.py`)**: Deterministically enforces schema membership, boolean states, array depths, operator validity, and formula variable declarations (`AllowedParams`).
6. **Targeted Self-Repair Loop (`repair.py`)**: If validation fails, re-prompts the LLM with error-code-specific diagnostics rather than generic retry prompts.

---

## 2. Infrastructure & Stability Enhancements

### Round-Robin Key Rotation (`dfm_rule_pipeline/llm/client.py`)
- Centralizes model strings in `dfm_rule_pipeline/config.py`.
- Accepts a comma-separated list of `GROQ_API_KEYS` in `.env`, automatically rotating to the next key on each API call to multiply tokens-per-minute throughput.
- If all keys are exhausted, gracefully flushes successfully processed rules to `phase3_partial_output.json` to prevent data loss.

### Production FastAPI Backend (`app.py`)
- Exposes `POST /upload-document` (Part 1 Extraction) and `POST /process-rules-taxonomy` (Part 2 Version 3 Formalisation).
- Interactive OpenAPI documentation at `http://localhost:8000/docs`.

### Modern React 18 SPA (`frontend/`)
- Single Page Application with clean UI for document uploading and rule formalisation inspection.

---

## 3. Directory & File Breakdown

- **`core_v2/`**: Part 1 Extraction Engine
  - `parser.py`: PyMuPDF layout-aware ingestion.
  - `truth_store.py`: SQLite immutable provenance store.
  - `windower.py`: spaCy sentence windowing.
  - `embeddings.py`: Local `sentence-transformers` CPU embedding.
  - `vector_store.py`: FAISS vector index.
  - `dfm_anchors.py`: Local anchor classification filter.
  - `candidate_assembler.py`: Paragraph reconstruction.
  - `llm_structurer.py`: Verbatim LLM rule extraction.
  - `validator.py`: Conflict and overlap resolution.

- **`dfm_rule_pipeline/`**: Part 2 Formalisation Pipeline
  - `taxonomy/`: **Version 3 Canonical Formalisation Pipeline** (6 tiers, 17-check validator, format1 schema).
  - `config.py`: Central environment configuration.
  - `llm/client.py`: Multi-key round-robin Groq client.
  - `schema/`: 12-domain feature definitions and descriptions.
  - `stages/`, `ast_engine/`, `pipeline.py`, `formatter.py`: Legacy auxiliary modules (retained for backward compatibility).

- **`frontend/`**: React 18 / Vite SPA dashboard.
- **`tests/`**: 11 automated pytest suites covering extraction, indexing, taxonomy engine, and format1 coverage.
