# RAG-RuleSync V2: Next-Generation DFM Rule Extraction Architecture

## Overview
RAG-RuleSync V2 represents a massive paradigm shift from the V1 architecture. While V1 relied heavily on brute-forcing raw LLM prompts (often hitting token limits, generating hallucinated data, and struggling with context), V2 introduces a highly optimized, 3-Phase pipeline. It blends local deterministic processing, local AI embeddings, and intelligent block-level LLM extraction to ensure zero duplication, perfect contextual resolution, and bypassed rate limits.

---

## 1. High-Level V2 Architecture

The new system splits responsibilities strictly to avoid LLM hallucination and reduce API costs.

### Phase 1: Structural Ingestion & Windowing (`core_v2/`)
Instead of just ripping plain text, V1 extracts hierarchical context.
1. **Parser (`parser.py`)**: Uses `PyMuPDF` to parse PDFs, identifying headers, paragraphs, and lists. It creates `StructuralBlock` objects, tagging each block of text with its parent `section_title`.
2. **Truth Store (`truth_store.py`)**: A local SQLite database (`temp_streamlit_truth_store.db`) that permanently records the exact, immutable text of every block and window. This prevents LLM hallucinations since we can always look up the source of truth.
3. **Windower (`windower.py`)**: Uses `SpaCy` to safely split paragraphs into `TextWindow` objects (sliding windows with overlap) without breaking engineering units (e.g., stopping mid-sentence at "0.3 in.").

### Phase 2: Anchor Classification (Local AI)
Before sending *anything* to an expensive LLM, we filter the document locally.
1. **Local Embeddings (`embeddings.py`)**: Uses lightweight `sentence-transformers` (default: `all-MiniLM-L6-v2`) running purely on the local CPU to convert text windows into mathematical vectors.
2. **FAISS Vector Store (`vector_store.py`)**: Stores the vectors for ultra-fast semantic search.
3. **Anchor Classification (`dfm_anchors.py`)**: Compares every window's vector against a set of known "DFM Anchor" rules (e.g., standard dimensional constraints). If the Cosine Similarity score is below a threshold, the window is discarded. **This eliminates ~80% of irrelevant text (like table of contents or company history) before Phase 3.**

### Phase 3: Block-Level LLM Extraction & Validation
The surviving candidate windows are finally sent to the cloud LLM (Groq) for structuring.
1. **Pre-Structuring Deduplication**: Rather than sending overlapping sliding windows (which causes duplication and sentence fragmentation), the pipeline groups candidates by their parent `block_id` and fetches the full, unfragmented paragraph from the `TruthStore`.
2. **Context-Aware Structuring (`llm_structurer.py`)**: 
    - Injects the `section_title` (e.g., "Sheet Metal Bend Radius") directly into the prompt alongside the full text block. 
    - The LLM extracts distinct constraints and uses the injected section title to automatically resolve context blindness and missing subjects (e.g., turning "It must be 2.0" into "Bend Radius must be 2.0").
3. **Multi-Hop Validator / Applicability Gate (`validator.py`)**: Resolves conflicts between extracted rules. If a new rule contradicts an existing rule, it checks the injected `section_title` metadata to determine if it is an entirely *new rule* for a different manufacturing process, or a *merge/refinement* of the existing rule.

---

## 2. Infrastructure & Stability Enhancements

### Round-Robin Key Rotation (`dfm_rule_pipeline/`)
To bypass strict free-tier rate limits, the LLM client was completely overhauled.
- **Single Source of Truth (`config.py`)**: Centralizes all model strings (`LLM_MODEL`, `EMBEDDING_MODEL`) and forces global `.env` loading.
- **Round-Robin Client (`client.py`)**: Accepts a comma-separated list of `GROQ_API_KEYS`. For every single extraction request, it instantly rotates to the next API key in the pool, effectively multiplying the tokens-per-minute threshold by the number of keys.
- **Graceful Failure**: If the entire pool of keys exhausts its rate limits, the pipeline intercepts the fatal exception and gracefully dumps all successfully processed rules to `phase3_partial_output.json`, ensuring zero data loss.

### Centralized Orchestration
- **`streamlit_v2.py`**: The central testing and visualization UI for the V2 pipeline. It visually maps the reduction of data from raw PDF -> Sliding Windows -> Anchor Candidates -> Extracted Rules -> Final Validated CSV.

---

## 3. Directory & File Breakdown (V2 Specific)

- **`core_v2/`**: The core engine containing the new extraction logic.
  - `dfm_anchors.py`: Local AI classification.
  - `embeddings.py`: Local `sentence-transformers` logic.
  - `llm_structurer.py`: Phase 3 step 1 extraction.
  - `parser.py`: PyMuPDF ingestion.
  - `truth_store.py`: SQLite source of truth.
  - `validator.py`: Phase 3 step 2 conflict resolution.
  - `vector_store.py`: FAISS logic.
  - `windower.py`: SpaCy windowing.

- **`dfm_rule_pipeline/`**: The modernized LLM connection architecture.
  - `config.py`: The supreme configuration registry.
  - `llm/client.py`: The round-robin, rate-limit bypassing OpenAI/Groq client.

- **`documentation/`**: Contains architectural documentation (`project_description_v2.md`).

- **Root Files**:
  - `streamlit_v2.py`: The V2 visualization GUI.
  - `temp_streamlit_truth_store.db`: The auto-managed SQLite database for the current active session.
  - `phase3_final_rules.csv` / `phase3_partial_output.json`: Output targets for Phase 3.

---

## 4. Why V2 Outperforms V1
1. **Cost**: By filtering 80% of text locally in Phase 2, LLM token costs drop dramatically.
2. **Accuracy**: Block-level deduplication prevents sentence fragmentation. Context injection prevents pronoun blindness.
3. **Speed**: Round-robin API rotation prevents 60-second sleep timeouts during long document extraction.
4. **Verifiability**: The `TruthStore` guarantees that every extracted rule can trace its lineage back to an exact character index in the original PDF.
