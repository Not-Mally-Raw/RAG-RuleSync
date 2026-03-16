# RAG-RuleSync: Enterprise DFM Rule Extraction System Breakdown

## Overview
RAG-RuleSync is an end-to-end NLP and Large Language Model (LLM) processing pipeline designed to extract structured Design-for-Manufacturability (DFM) rules from unstructured manufacturing documents (PDFs, DOCX, TXT, Excel).

The system targets manufacturing manuals, checklists, and specifications, extracting plain English rules, judging their relevance, converting them to CAD-ready constraints (Abstract Syntax Trees), and exporting the results.

---

## 1. High-Level Architecture
The system consists of two primary macro-components:
1. **The Core Extraction Engine (`core/`)**: Responsible for document ingestion, text chunking, rate-limiting, and prompting the Groq LLM to perform "Level 1" bulk extraction. Output is strict JSON with zero ad-hoc post-validation coercion.
2. **The DFM Rule Pipeline (`dfm_rule_pipeline/`)**: Receives the raw LLM output and passes it through a 4-stage refinement process to determine exact intent, map rules to a 12-category manufacturing schema (e.g., *Sheetmetal*, *Drilling*, *Injection Moulding*), formalize the text into mathematical equations, and map generic variables to strict CAD namespace paths.

### Process Flow
1. **Document Upload**: User uploads `Spec.pdf` via the Streamlit UI or points a CLI arg to a directory.
2. **Ingestion (`DocumentLoader`)**: Returns plain text stripped of boilerplate.
3. **Chunking (`TextChunker`)**: Text is sliced into token-aware windows to respect LLM context limits.
4. **LLM Extraction (`EnhancedRuleEngine`)**: Groq models (default: `meta-llama/llama-4-scout-17b-16e-instruct`) extract rules using a "Mega-Prompt" (`core/prompts.py`).
5. **JSON Structuring**: The LLM outputs `ManufacturingRule` JSON arrays containing the `rule_text`, `dimensional_constraints`, `relational_constraints`, and `applicability_constraints`.
6. **Refinement Pipeline (`dfm_rule_pipeline/pipeline.py`)**: 
    - *Stage 1 (Intent)*: Determines if a rule is quantifiable, geometric, or an attribute rule.
    - *Stage 2 (Resolution)*: Evaluates the specific category/domain using `features_dict`.
    - *Stage 3 (Formalization)*: Paraphrases natural language constraints (e.g. *thickness should be at least 0.8mm*) into equations (e.g., `Thickness >= 0.8`).
    - *Stage 4 (Self Validation/AST)*: Complex compound logics are parsed into Abstract Syntax Trees for operator/operand validation.
7. **CAD Normalization (`dfm_rule_pipeline/formatter.py`)**: A mapping dictionary (`DOMAIN_CONFIG`) converts generic terms (`Thickness`) into system-specific variables (`SheetMetal.Thickness`).
8. **Export**: Process outputs a final dataset suitable for consumption by CAD checking software (`_FINAL_FORMATTED.csv`).

---

## 2. DFM Rule Contract (System Invariants)
The system is built around a non-code contract that defines how a rule must be represented.
- **Rule (atomic)**: Single, atomic manufacturing invariant.
- **Scope Domain**: Must define the `{process, item, feature}`.
- **Applicability (Hard Gates)**: A list of binary conditions such as material, process, or feature presence; outside these gates, the rule must not evaluate. For example: `material == "low carbon steel"`.
- **Constraints**: Evaluatable mathematical expressions containing a subject, operator (`<`, `<=`, `>=`, `==`, `!=`, `between`, `±`), value, and unit.
- **Severity**: Determines rule enforcement (`ENFORCEABLE` vs `ADVISORY`). *Advisory* rules apply heuristics like "avoid" or "for ease of...". *Enforceable* rules contain deterministic numeric limits.
- **Validation State**: 
    - `ENFORCEABLE`: When evaluatable constraints exist.
    - `ADVISORY_ONLY`: When severity = ADVISORY.
    - `INCOMPLETE`: When constraints are missing or ill-formed.

---

## 3. Directory & File Breakdown

### 3.1 Orchestration Tools (Root Directory)
- **`batch_extract_rules.py`**: CLI script for headless, recursive batch processing of directories containing PDFs. Good for large document drops.
- **`enhanced_streamlit_app.py` & `simple_streamlit_app.py`**: Streamlit UIs. Provide drag-and-drop document upload, analytics, and direct rule-text paste options.

### 3.2 Core Extraction Engine (`core/`)
- **`rule_extraction.py`**: The foundational extraction toolkit containing data models (`RuleExtractionSettings`), rate limiters (`AsyncRateLimiter`), and basic document loaders.
- **`prompts.py`**: The single source of truth for the extraction engine. Contains the massive `compiler_prompt` which maps out 12 manufacturing domains and dictates the entire JSON output schema to the LLM. 
- **`enhanced_rule_engine.py`**: The LangChain integration. Chains the prompts to `ChatGroq` using a `JsonOutputParser` to parse output efficiently without using heavy Pydantic coercion. 
- **`production_system.py`**: The central facade (`ProductionRuleExtractionSystem`) wrapping the extraction logic so external UI components don't have to manage async states directly. 
- **SOLID Enhancements** (`interfaces.py`, `adapters.py`, `orchestrator.py`): Provide dependency injection structures, making it easier to swap out chunkers, loaders, or LLM providers without altering core extraction logic. 

### 3.3 Rule Refinement Factory (`dfm_rule_pipeline/`)
This module houses the secondary reasoning step that takes string limits and turns them into CAD math.
- **`pipeline.py`**: Iterates through incoming rules and manages the routing through the 4 stages.
- **`formatter.py`**: The final normalization script. It takes generic `equation` or `ast` outputs from the pipeline and replaces dummy variables using `DOMAIN_CONFIG` (e.g. changing `Distance` to `Distance.MinValue` depending on the domain context). It also creates human-readable semantic rule names.

#### `stages/` Directory
- **`stage1_intent_extraction.py`**: LLM-driven check to see if a rule contains quantifiable elements. 
- **`stage2_rule_resolution.py`**: Categorizes the rule.
- **`stage2a_schema_consistency.py` / `stage2b_geometry_resolution.py` / `stage2c_tolerance_spec.py`**: Sub-routing stages based on whether the rule is relating to geometry (distance between two holes), tolerance limits, or general part attributes.
- **`stage3_attribute_formalization.py` / `stage3_formalization.py`**: Creates the raw formula from the LLM based on schema definitions.
- **`stage4_self_validation.py`**: Uses LLMs to self-correct obvious logic errors.

#### `ast_engine/` Directory
- **`ast_nodes.py`, `ast_builder.py`, `ast_evaluator.py`, `ast_validator.py`**: For rules containing compound/complex logic (e.g., `bend_radius >= MAX(0.5*material_thickness, 0.80 mm)`), simply pulling Regex strings fails. The AST engine breaks statements down into syntax trees to enforce operator validity.

---

## 4. Historical Refactoring Context
Note: In January 2026, the `core/enhanced_rule_engine.py` underwent a major refactor.
**Before**: Rules were heavily validated and altered by Pydantic parsers, and ran through semantic deduplication and clustering algorithms inside the extraction loop.
- **After**: The Pydantic logic was removed in favor of `JsonOutputParser`. All LLM prompt instructions were heavily consolidated into `core/prompts.py` (making it the Single Source of Truth). Outputs are now returned verbatim from the LLM directly into temporary `.json` files, offering a "Zero Mutation" guarantee at the extraction level. Post-processing has been strictly delegated to `dfm_rule_pipeline`.

---

## 5. Technology Stack & Dependencies
To build off this repo, you should be familiar with the following core libraries:
- **LLM/Orchestration**: `langchain`, `langchain-groq` (Groq models are the primary engine used to bypass rate limits and improve speed).
- **Document Ingestion**: `PyMuPDF` (PDFs), `python-docx` (Word), `pandas` (Excel/CSV).
- **Text Processing & Chunking**: `tiktoken` (token-aware slicing), `textstat` (readability metrics).
- **Analytics & Interface**: `streamlit` (UI), `structlog` (JSON structured logging).

---

## 6. Example Data Payloads

### 6.1 Level-1 Output (from `core/`)
When the Groq LLM extracts a rule from `core/enhanced_rule_engine.py`, it guarantees the following JSON shape. This strict format is forced by the Mega-Prompt in `core/prompts.py`:
```json
{
  "source_pdf": "design_guidelines.pdf",
  "rule_count": 1,
  "rules": [
    {
      "rule_text": "Minimum wall thickness is 0.8mm for injection molding",
      "rule_type": "Injection Moulding",
      "applicability_constraints": {
        "material": "any",
        "process": "injection molding",
        "feature": "wall",
        "location": "any"
      },
      "dimensional_constraints": [
        "Wall thickness: >= 0.8 mm"
      ],
      "relational_constraints": [
        "None"
      ]
    }
  ],
  "processing_time": 4.2,
  "chunks_processed": 1
}
```

### 6.2 Formalized Output (from `dfm_rule_pipeline/`)
After `dfm_rule_pipeline/formatter.py` processes the JSON above, it translates it into CAD-ready constraints output to `_FINAL_FORMATTED.csv`:
```csv
RuleCategory,Name,Feature1,Feature2,Object1,Object2,ExpName,Operator,Recom,RuleText
Injection Molding,Wall Thickness Limit,Attribute,,,Tolerance,InjectionMolding.NominalThickness,>=,True,Minimum wall thickness is 0.8mm for injection molding
```
