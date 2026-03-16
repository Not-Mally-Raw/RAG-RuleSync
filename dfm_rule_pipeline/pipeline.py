import json
import os
import csv
from tqdm import tqdm

from stages.stage1_intent_extraction import extract_intent
from stages.stage2_rule_resolution import resolve_rule_category_and_domain
from stages.stage2b_geometry_resolution import resolve_geometry
from stages.stage2c_tolerance_spec import resolve_tolerance
from stages.stage3_formalization import formalize_rule
from stages.stage4_self_validation import self_validate
from stages.stage3_attribute_formalization import formalize_attribute_rule
from stages.stage2_attribute_resolution import requires_ast
from ast_engine.ast_validator import ASTValidator
from schema.ast_schema import serialize_ast

# 1. IMPORT FEATURES DICT
from schema.feature_schema import features_dict 

OUTPUT_FILE = "output/dfm_results.csv"

CSV_HEADERS = [
    "rule_text", "status", "resolution_status", "formalism", 
    "rule_json", "equation", "ast", "reasoning", "error", "domain"
]

def append_result(row: dict):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    exists = os.path.isfile(OUTPUT_FILE)
    safe = {}
    for k in CSV_HEADERS:
        v = row.get(k, "")
        if isinstance(v, (dict, list)):
            safe[k] = json.dumps(v)
        elif v is None:
            safe[k] = ""
        else:
            safe[k] = str(v)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not exists: writer.writeheader()
        writer.writerow(safe)

def is_intrinsic_dimension(intent: dict) -> bool:
    INTRINSIC_ATTRS = {"width", "height", "depth", "radius", "diameter", "thickness", "length", "angle"}
    attrs = intent.get("mentioned_attributes", [])
    return any(a.lower() in INTRINSIC_ATTRS for a in attrs)

# --- RECTIFIED HELPER: ROBUST DOMAIN NORMALIZER ---
def normalize_domain_key(raw_domain: str) -> str:
    """
    Standardizes input (e.g., 'Sheet Metal') to match features_dict keys (e.g., 'Sheetmetal').
    Priority 2: Prevent fallback to 'General' when a specific intent exists.
    """
    if not raw_domain: return "General"
    
    # Clean string for comparison
    clean_input = raw_domain.strip().lower().replace(" ", "")
    
    # 1. Direct key search (Sheetmetal vs Sheet Metal)
    for key in features_dict.keys():
        if key.lower().replace(" ", "") == clean_input:
            return key
            
    # 2. Specific Mapping for common XLSX variations
    mapping = {
        "sheetmetal": "Sheetmetal",
        "sheetmetalforming": "SMForm",
        "smf": "SMForm",
        "injectionmolding": "Injection Moulding",
        "molding": "Injection Moulding",
        "diecasting": "Die Cast",
        "additivemanufacturing": "Additive",
        "assembly": "Assembly"
    }
    
    return mapping.get(clean_input, "General")

def run_pipeline(llm, rules_data):
    print("🔥 ENTERED run_pipeline (Strict Category Mode)")

    for entry in tqdm(rules_data, desc="Processing Rules"):
        rule_text = entry.get("rule_text") if isinstance(entry, dict) else str(entry)
        explicit_domain = entry.get("rule_type") # This comes from XLSX 'Category'
        
        if not rule_text or not rule_text.strip(): continue
        rule_text = rule_text.strip()

        try:
            # STAGE 1: Intent
            intent = extract_intent(llm, rule_text)
            
            # --- PRIORITY 1: EXPLICIT CATEGORY OVERRIDE ---
            if explicit_domain:
                intent["domain"] = normalize_domain_key(explicit_domain)
            
            rule_intent = intent["rule_intent"]
            if not rule_intent.get("is_quantifiable", False):
                append_result({
                    "rule_text": rule_text, "status": "Skipped", "resolution_status": "skipped",
                    "reasoning": intent.get("reasoning"), "domain": intent.get("domain", "Unknown")
                })
                continue

            # STAGE 2: Category Resolution (Keep Category, but protect Domain)
            resolution = resolve_rule_category_and_domain(llm, intent, rule_text)
            category = resolution["rule_category"]
            
            # Only use guesser if explicit_domain was missing or yielded 'General'
            if not explicit_domain or intent["domain"] == "General":
                 intent["domain"] = resolution["primary_domain"]

            # CRITICAL: Re-check normalization to ensure key exists in features_dict
            intent["domain"] = normalize_domain_key(intent["domain"])
            schema_text = features_dict.get(intent["domain"], "")

            # Intrinsic dimension check
            if category == "Geometry" and is_intrinsic_dimension(intent):
                category = "Attribute"

            # Route to correct stage based on determined Category
            if category == "Geometry":
                geo = resolve_geometry(llm, rule_text, intent)
                append_result({
                    "rule_text": rule_text, "status": "Deferred", "resolution_status": "deferred_geometry",
                    "formalism": "Geometry", "rule_json": geo.get("geometry"), 
                    "reasoning": geo.get("reasoning"), "domain": intent["domain"]
                })
            elif category == "Tolerance":
                tol = resolve_tolerance(llm, rule_text, intent)
                append_result({
                    "rule_text": rule_text, "status": "Deferred", "resolution_status": "deferred_tolerance",
                    "formalism": "Tolerance" if tol.get("tolerance_valid") else None,
                    "equation": tol.get("equation"), "reasoning": tol.get("reasoning"), "domain": intent["domain"]
                })
            elif category == "Attribute":
                result = formalize_attribute_rule(llm, rule_text, intent, schema_context=schema_text)
                
                # Equation or AST handling
                if result.get("formalism") == "equation":
                    append_result({
                        "rule_text": rule_text, "status": "Success", "resolution_status": "formalized",
                        "formalism": "equation", "equation": result["equation"],
                        "reasoning": result["reasoning"], "domain": intent["domain"]
                    })
                else:
                    append_result({
                        "rule_text": rule_text, "status": "Deferred", "resolution_status": "deferred_attribute",
                        "reasoning": result.get("reasoning"), "domain": intent["domain"]
                    })
        except Exception as e:
            append_result({"rule_text": rule_text, "status": "Review Needed", "error": str(e), "domain": explicit_domain})

    print("✅ Pipeline complete:", OUTPUT_FILE)