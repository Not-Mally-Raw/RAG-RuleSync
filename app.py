import os
import uvicorn
import sys
import tempfile
import json
import logging
from pathlib import Path
from typing import List, Optional

# --- Add Paths to sys.path ---
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "dfm_rule_pipeline"))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Core V2 Imports ---
from core_v2.parser import LayoutAwareParser
from core_v2.windower import SlidingWindowGenerator
from core_v2.truth_store import TruthStore
from core_v2.embeddings import EmbeddingManager
from core_v2.vector_store import VectorStore
from core_v2.dfm_anchors import DFMAnchorClassifier
from core_v2.candidate_assembler import CandidateAssembler
from core_v2.llm_structurer import LLMStructurer, deduplicate_extracted_rules

# --- Pipeline & Formatter Imports ---
from dfm_rule_pipeline.llm.client import LLMClient
from dfm_rule_pipeline.config import EMBEDDING_MODEL
from dfm_rule_pipeline.schema.feature_schema import features_dict
from dfm_rule_pipeline.pipeline import is_intrinsic_dimension, normalize_domain_key
from dfm_rule_pipeline.formatter import process_row

# --- Taxonomy V3 Imports ---
from dfm_rule_pipeline.taxonomy import (
    TaxonomyFormalizationService,
    RuleInput as TaxonomyRuleInput
)

# Stages
from dfm_rule_pipeline.stages.stage1_intent_extraction import extract_intent
from dfm_rule_pipeline.stages.stage2_rule_resolution import resolve_rule_category_and_domain
from dfm_rule_pipeline.stages.stage2b_geometry_resolution import resolve_geometry
from dfm_rule_pipeline.stages.stage2c_tolerance_spec import resolve_tolerance
from dfm_rule_pipeline.stages.stage3_attribute_formalization import formalize_attribute_rule

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("RAG-RuleSync-API")

# Initialize FastAPI
app = FastAPI(
    title="RAG-RuleSync API",
    description="FastAPI interface for the Enterprise DFM Rule Extraction System.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global models
embedder = None
classifier = None
llm_client = None
taxonomy_service = None

@app.on_event("startup")
def startup_event():
    global embedder, classifier, llm_client, taxonomy_service
    logger.info("Initializing embedding manager, classifier, and LLM client...")
    embedder = EmbeddingManager(model_name=EMBEDDING_MODEL)
    classifier = DFMAnchorClassifier(embedder, threshold=0.25)
    llm_client = LLMClient()
    taxonomy_service = TaxonomyFormalizationService(llm_client=llm_client, embedder=embedder)
    logger.info("Initialization complete.")

# --- Models ---
class RuleInput(BaseModel):
    rule_text: str = Field(..., description="The verbatim or resolved manufacturing rule text.")
    rule_type: Optional[str] = Field(None, description="Optional explicit domain/category override (e.g. 'Sheetmetal', 'Injection Moulding').")

class ProcessRulesRequest(BaseModel):
    rules: List[RuleInput]

# --- Endpoints ---
@app.get("/")
def read_root():
    return {"status": "running", "message": "RAG-RuleSync API is online."}

@app.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    """
    Pipeline 1: Document Upload & L1 Extraction.
    Accepts a PDF document, parses it, chunks it, detects candidates via anchor similarities,
    resolves pronouns/contexts, and returns Level-1 extracted verbatim and resolved rules.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    # Save PDF to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)
        
    try:
        # 1. Parse blocks
        parser = LayoutAwareParser()
        payload = parser.parse(tmp_path)
        
        # 2. Generate sliding windows
        windower = SlidingWindowGenerator(window_size=3, stride=1)
        windows = windower.generate(payload.blocks)
        
        if not windows:
            return []
            
        # 3. Cache inside SQLite temporary DB (unique per request to ensure thread safety)
        db_file = Path(tempfile.mktemp(suffix=".db"))
        truth_store = TruthStore(db_file)
        truth_store.store_document(payload, windows)
        
        # 4. Generate embeddings
        texts = [w.text for w in windows]
        embeddings = embedder.embed(texts)
        
        # 5. Index in FAISS
        vstore = VectorStore(dimension=embedder.dimension)
        window_ids = [w.window_id for w in windows]
        vstore.add(embeddings, window_ids)
        
        # 6. Anchor similarity classification
        classifications = classifier.classify_batch(embeddings)
        candidate_windows = []
        for i, (is_rule, score) in enumerate(classifications):
            if is_rule:
                candidate_windows.append(windows[i])
                
        logger.info(f"Classified {len(candidate_windows)} rule candidate windows out of {len(windows)}")
        
        # 7. Candidate assembly & Context retrieval
        assembler = CandidateAssembler(context_sentences=2)
        extraction_units = assembler.assemble(candidate_windows)
        
        # 8. Structuring using LLM
        structurer = LLMStructurer(llm_client)
        all_extracted_rules = []
        for unit in extraction_units:
            extracted = structurer.structure(
                unit.target_text,
                unit.unit_id,
                context_text=unit.context_text,
                source_window_ids=unit.source_window_ids,
            )
            all_extracted_rules.extend(extracted)
            
        # 9. Deduplication
        deduped_rules = deduplicate_extracted_rules(all_extracted_rules)
        
        # Cleanup truth store temporary file
        if db_file.exists():
            try:
                db_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp database: {e}")
                
        # Format response
        response = []
        for r in deduped_rules:
            response.append({
                "rule_text": r.rule_text,
                "resolved_rule_text": r.resolved_rule_text,
                "source_window_ids": r.source_window_ids
            })
            
        return response
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to extract rules from document: {str(e)}")
        
    finally:
        # Cleanup temporary PDF
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp PDF: {e}")

@app.post("/process-rules")
def process_rules(payload: ProcessRulesRequest):
    """
    Pipeline 2: DFM Refinement, Formalization & Schema Formatting.
    Accepts rule sentences/resolved rules, checks for intent, resolves categories & domains,
    generates math equations/ASTs, and formats them into strict target CAD schemas.
    """
    results = []
    
    for rule in payload.rules:
        rule_text = rule.rule_text.strip()
        explicit_domain = rule.rule_type
        
        if not rule_text:
            continue
            
        try:
            # Stage 1: Intent Extraction
            intent = extract_intent(llm_client, rule_text)
            
            # Explicit category override
            if explicit_domain:
                intent["domain"] = normalize_domain_key(explicit_domain)
                
            rule_intent = intent["rule_intent"]
            if not rule_intent.get("is_quantifiable", False):
                row = {
                    "rule_text": rule_text,
                    "status": "Skipped",
                    "resolution_status": "skipped",
                    "reasoning": intent.get("reasoning"),
                    "domain": intent.get("domain", "Unknown")
                }
                
                # Format skipped rules cleanly
                formatted = process_row(row)
                if formatted:
                    results.append(clean_formatted_response(formatted))
                continue
                
            # Stage 2: Category & Domain Resolution
            resolution = resolve_rule_category_and_domain(llm_client, intent, rule_text)
            category = resolution["rule_category"]
            
            if not explicit_domain or intent["domain"] == "General":
                intent["domain"] = resolution["primary_domain"]
                
            intent["domain"] = normalize_domain_key(intent["domain"])
            schema_text = features_dict.get(intent["domain"], "")
            
            # Intrinsic dimension check
            if category == "Geometry" and is_intrinsic_dimension(intent):
                category = "Attribute"
                
            # Route by category
            row = {}
            if category == "Geometry":
                geo = resolve_geometry(llm_client, rule_text, intent)
                row = {
                    "rule_text": rule_text,
                    "status": "Deferred",
                    "resolution_status": "deferred_geometry",
                    "formalism": "Geometry",
                    "rule_json": json.dumps(geo.get("geometry")) if isinstance(geo.get("geometry"), (dict, list)) else geo.get("geometry"),
                    "reasoning": geo.get("reasoning"),
                    "domain": intent["domain"]
                }
            elif category == "Tolerance":
                tol = resolve_tolerance(llm_client, rule_text, intent)
                row = {
                    "rule_text": rule_text,
                    "status": "Deferred",
                    "resolution_status": "deferred_tolerance",
                    "formalism": "Tolerance" if tol.get("tolerance_valid") else None,
                    "equation": tol.get("equation"),
                    "reasoning": tol.get("reasoning"),
                    "domain": intent["domain"]
                }
            elif category == "Attribute":
                result = formalize_attribute_rule(llm_client, rule_text, intent, schema_context=schema_text)
                if result.get("formalism") == "equation":
                    row = {
                        "rule_text": rule_text,
                        "status": "Success",
                        "resolution_status": "formalized",
                        "formalism": "equation",
                        "equation": result["equation"],
                        "reasoning": result["reasoning"],
                        "domain": intent["domain"]
                    }
                else:
                    row = {
                        "rule_text": rule_text,
                        "status": "Deferred",
                        "resolution_status": "deferred_attribute",
                        "reasoning": result.get("reasoning"),
                        "domain": intent["domain"]
                    }
            
            # Format row using formatting pipeline
            formatted = process_row(row)
            if formatted:
                results.append(clean_formatted_response(formatted))
            else:
                results.append({
                    "RuleText": rule_text,
                    "Status": "Review Needed",
                    "DecisionCode": "Failure(Formatting Failed)",
                    "RuleCategory": intent.get("domain", "General"),
                    "dfm_json": None
                })
                
        except Exception as e:
            logger.error(f"Error processing rule '{rule_text}': {e}", exc_info=True)
            results.append({
                "RuleText": rule_text,
                "Status": "Review Needed",
                "DecisionCode": f"Failure({str(e)})",
                "RuleCategory": explicit_domain or "Unknown",
                "dfm_json": None
            })
            
    return results

def clean_formatted_response(formatted: dict) -> dict:
    """Utility to clean up double-nested JSON strings in the formatter response."""
    cleaned = dict(formatted)
    
    # Check dfm_json column
    dfm_json = cleaned.get("dfm_json")
    if dfm_json and isinstance(dfm_json, str):
        try:
            cleaned["dfm_json"] = json.loads(dfm_json)
        except Exception:
            pass
            
    # Normalize dictionary key casing for consistency
    return {
        "rule_text": cleaned.get("RuleText"),
        "status": cleaned.get("Status"),
        "decision_code": cleaned.get("DecisionCode"),
        "rule_category": cleaned.get("RuleCategory"),
        "dfm_rule": cleaned.get("dfm_json")
    }

@app.post("/process-rules-taxonomy")
def process_rules_taxonomy_endpoint(payload: ProcessRulesRequest):
    """
    Pipeline V3: DFM Refinement and Taxonomy-based DFM Rule Formalization.
    Converts manufacturing rules to deeply nested format1 JSON structures
    aligned with domain schemas. Supports auto-repair loops.
    """
    results = []
    for rule in payload.rules:
        # Convert app-level RuleInput model to taxonomy package RuleInput model
        tax_input = TaxonomyRuleInput(
            rule_text=rule.rule_text,
            rule_type=rule.rule_type
        )
        try:
            res = taxonomy_service.formalize_rule(tax_input)
            results.append(res)
        except Exception as e:
            logger.error(f"Failed processing rule under taxonomy endpoint: {e}", exc_info=True)
            results.append({
                "rule_text": rule.rule_text,
                "status": "Review Needed",
                "decision_code": f"endpoint_error({str(e)})",
                "domain": rule.rule_type or "General",
                "bucket": "SimpleValidation",
                "taxonomy_rules": [],
                "validation_errors": []
            })
    return results

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
