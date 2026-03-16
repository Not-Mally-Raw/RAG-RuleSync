# RAG-RuleSync

RAG-RuleSync is an end-to-end NLP/LLM pipeline that extracts structured Design-for-Manufacturability (DFM) rules from unstructured PDFs, manuals, and specifications. It extracts rules, assigns logic, and formats them into exact CAD-ready mathematical constraints.

### 📚 Documentation
For an in-depth, file-by-file breakdown of the system architecture, constraints, and pipelines, please see **[Project_description.md](Project_description.md)**.

---

## Quick Start Guide

### 1. Installation
Install the required packages.
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory and add your Groq API key.
```bash
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

### 3. Running the System

#### Option 1: Streamlit UI (Recommended)
Launch the interactive web interface to upload PDFs and visualize the extraction real-time.
```bash
python -m streamlit run simple_streamlit_app.py
```
Open your browser to `http://localhost:8503`. Output tables are saved to the `output/` directory as `_FINAL_FORMATTED.csv`.

#### Option 2: Batch Processing Script
Use the batch script to process an entire folder of PDFs concurrently. Note: Be cautious with strict API rate limits when doing bulk extractions.
```bash
python batch_extract_rules.py --input /path/to/pdfs --output output/compiled_rules
```

#### Option 3: Python API
```python
import asyncio
from core.enhanced_rule_engine import EnhancedConfig, EnhancedRuleEngine

config = EnhancedConfig()
engine = EnhancedRuleEngine(config)

result = asyncio.run(engine.extract_rules_from_text(
    'Wall thickness must be at least 0.8mm for injection molding.',
    filename='my_document.pdf'
))

print(f"Extraction result: {result}")
```

---

## Output Format
Data flows from raw JSON extractions (`output/{pdf_name}.json`) into the final structured schema handled by the DFM refinement pipeline (`output/{pdf_name}_FINAL_FORMATTED.csv`). The CSV contains:
- `RuleCategory`: E.g., Sheet Metal, Turning, Injection Molding.
- `Name`: Semantically generated rule name.
- `Operator` / `ExpName`: The CAD-ready mathematical operators constraints (e.g., `SheetMetal.Thickness >= 0.8`).
- `RuleText`: Verbatim text.
