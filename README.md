# RAG-RuleSync V2

RAG-RuleSync V2 is an enterprise-grade Design-for-Manufacturability (DFM) rule extraction pipeline. It utilizes layout-aware PDF ingestion, local semantic anchor vector classification, block-level deduplication, context resolution, and round-robin Groq API key rotation to build CAD-ready mathematical constraints from unstructured documents.

### 📚 Documentation
For an architectural deep dive and component breakdown, see **[Project_description.md](Project_description.md)**.

---

## Getting Started

### 1. Installation
Install project dependencies:
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory. Add your Groq API key (or multiple keys separated by commas for round-robin rotation):
```bash
GROQ_API_KEY=gsk_key1,gsk_key2,...
GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

### 3. Running the System

#### Option 1: Streamlit V2 UI
Run the interactive Streamlit testing and visualization application:
```bash
python -m streamlit run streamlit_v2.py
```
Open your browser to the URL displayed in the terminal (usually `http://localhost:8501`).

#### Option 2: FastAPI Backend
Run the backend web service for production API integrations:
```bash
uvicorn app:app --reload --port 8000
```
API endpoints will be served at `http://localhost:8000`. You can inspect the interactive docs at `http://localhost:8000/docs`.

---

## Output Formats
Extraction outputs flow from raw JSON block chunks into a unified CSV structure:
- **`phase3_partial_output.json`**: Temporary JSON backup of successfully extracted rules if rate limits are hit.
- **`phase3_final_rules.csv`**: CAD-normalized mathematical rules containing the category, operators, features, variables, and verbatim source texts.
