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

# --- NEW HELPER: DOMAIN NORMALIZER ---
def normalize_domain_key(raw_domain: str) -> str:
    """
    Matches input 'SheetMetal' to system key 'Sheetmetal' (Case-insensitive).
    Returns 'General' if no match found.
    """
    if not raw_domain: return "General"
    
    # 1. Exact Match
    if raw_domain in features_dict:
        return raw_domain
        
    # 2. Case-Insensitive Match
    raw_lower = raw_domain.lower()
    for key in features_dict.keys():
        if key.lower() == raw_lower:
            return key
            
    # 3. Fallback
    return "General"

def run_pipeline(llm, rules_data):
    print("🔥 ENTERED run_pipeline (Explicit Domain Mode)")

    for entry in tqdm(rules_data, desc="Processing Rules"):
        rule_text = entry.get("rule_text") if isinstance(entry, dict) else str(entry)
        
        # --- NEW: EXTRACT EXPLICIT DOMAIN ---
        explicit_domain = entry.get("rule_type") # e.g., "SheetMetal"
        
        if not rule_text or not rule_text.strip(): continue
        rule_text = rule_text.strip()

        try:
            # STAGE 1: Intent
            intent = extract_intent(llm, rule_text)
            rule_intent = intent["rule_intent"]

            if not rule_intent.get("is_quantifiable", False):
                append_result({
                    "rule_text": rule_text,
                    "status": "Skipped",
                    "resolution_status": "skipped",
                    "reasoning": intent.get("reasoning"),
                    "domain": explicit_domain or "Unknown"
                })
                continue

            # STAGE 2: Category & Domain Resolution
            # We still run this to get the 'Category' (Geometry vs Attribute)
            resolution = resolve_rule_category_and_domain(intent, rule_text)
            category = resolution["rule_category"]
            
            # --- CRITICAL FIX: OVERRIDE DOMAIN ---
            if explicit_domain:
                # Use the JSON's domain, normalized to match our Schema Keys
                intent["domain"] = normalize_domain_key(explicit_domain)
            else:
                # Fallback to keyword guessing
                intent["domain"] = resolution["primary_domain"]

            # Schema Context Loading (Now guaranteed correct)
            schema_text = features_dict.get(intent["domain"], "")

            # Category Correction (Geometry -> Attribute for intrinsic)
            if category == "Geometry" and is_intrinsic_dimension(intent):
                category = "Attribute"

            # STAGE 2b: Geometry
            if category == "Geometry":
                geo = resolve_geometry(llm, rule_text, intent)
                append_result({
                    "rule_text": rule_text,
                    "status": "Deferred",
                    "resolution_status": "deferred_geometry",
                    "formalism": "Geometry",
                    "rule_json": geo.get("geometry"),
                    "reasoning": geo.get("reasoning"),
                    "domain": intent["domain"]
                })
                continue

            # STAGE 2c: Tolerance
            if category == "Tolerance":
                tol = resolve_tolerance(llm, rule_text, intent)
                append_result({
                    "rule_text": rule_text,
                    "status": "Deferred",
                    "resolution_status": "deferred_tolerance",
                    "formalism": "Tolerance" if tol.get("tolerance_valid") else None,
                    "equation": tol.get("equation"),
                    "reasoning": tol.get("reasoning"),
                    "domain": intent["domain"]
                })
                continue

            # STAGE 3: Attribute
            if category == "Attribute":
                result = formalize_attribute_rule(
                    llm,
                    rule_text,
                    intent,
                    schema_context=schema_text  # Passing the CORRECT schema now
                )

                if result.get("formalism") == "equation":
                    append_result({
                        "rule_text": rule_text,
                        "status": "Success",
                        "resolution_status": "formalized",
                        "formalism": "equation",
                        "equation": result["equation"],
                        "reasoning": result["reasoning"],
                        "domain": intent["domain"]
                    })
                    continue

                # AST Validation
                validator = ASTValidator(allowed_variables={"ModuleParams", "Bend", "Hole", "Slot", "Emboss", "Counterbore"})
                if result.get("formalism") == "AST" and validator.validate(result["ast"]):
                    append_result({
                        "rule_text": rule_text,
                        "status": "Success",
                        "resolution_status": "formalized",
                        "formalism": "AST",
                        "ast": serialize_ast(result["ast"]),
                        "reasoning": result["reasoning"],
                        "domain": intent["domain"]
                    })
                    continue
                
                append_result({
                    "rule_text": rule_text,
                    "status": "Deferred",
                    "resolution_status": "deferred_attribute",
                    "reasoning": result.get("reasoning"),
                    "domain": intent["domain"]
                })
                continue

        except Exception as e:
            append_result({
                "rule_text": rule_text,
                "status": "Review Needed",
                "resolution_status": "failed",
                "error": str(e),
                "domain": entry.get("rule_type", "Unknown")
            })

    print("✅ Pipeline complete:", OUTPUT_FILE)