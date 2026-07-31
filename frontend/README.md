# RAG-RuleSync Frontend

React/Vite UI for document ingestion and rule formalization.

## Run

Start the FastAPI backend from the repo root:

```bash
python app.py
```

Start the frontend from this folder:

```bash
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

The frontend checks backend health at `http://localhost:8000/`.

## Rule Compiler

Use the **Rule Compiler** tab, enter one rule per line, optionally choose a domain override, and run the compiler.

The compiler calls:

```text
POST /process-rules
```
