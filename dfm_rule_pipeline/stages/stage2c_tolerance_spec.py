import json
import re

from dfm_rule_pipeline.schema.feature_schema import features_dict
from dfm_rule_pipeline.schema.tolerance_schema import TOLERANCE_TYPES, GDT_KEYWORDS
from dfm_rule_pipeline.llm.prompts import TOLERANCE_PROMPT

def resolve_tolerance(llm, rule_text: str, intent_input) -> dict:
    # ------------------------------------------------------------------
    # STRICT INPUT NORMALIZATION
    # ------------------------------------------------------------------
    if isinstance(intent_input, str):
        try:
            intent = json.loads(intent_input)
        except Exception:
            return {
                "status": "Failed",
                "tolerance_valid": False,
                "error": "Intent is not valid JSON"
            }
    else:
        intent = intent_input

    # --- FIX START ---
    # OLD CODE (Broken):
    # tolerance_context = intent.get("tolerance")
    # if not tolerance_context: return Failed...

    # NEW CODE (Robust):
    # We pass the WHOLE intent as context, but we don't require 
    # a pre-existing "tolerance" object.
    tolerance_context = intent.get("tolerance") or {} 
    # --- FIX END ---

    # ------------------------------------------------------------------
    # LLM FORMALIZATION
    # ------------------------------------------------------------------
    # We use rule_text as the primary source of truth.
    prompt = TOLERANCE_PROMPT.format(
        rule_text=rule_text,
        intent_json=json.dumps(intent, indent=2), # Pass full intent for context
        schema_context=features_dict.get("General", "")
    )

    raw = llm.call(prompt)
    if not isinstance(raw, str):
        raw = str(raw)

    expression = (
        raw.replace("```python", "")
           .replace("```", "")
           .strip()
           .strip('"')
           .strip("'")
    )

    if not expression:
        return {
            "status": "Failed",
            "tolerance_valid": False,
            "error": "Empty tolerance expression"
        }

    # ------------------------------------------------------------------
    # SEMANTIC TOLERANCE TYPE DETECTION
    # ------------------------------------------------------------------
    parsed_type = None

    if expression.startswith("Tolerance("):
        parsed_type = "Bilateral"

    elif expression.startswith("Limits("):
        parsed_type = "Limits"

    elif expression.startswith(("Max(", "Min(")):
        parsed_type = "SingleLimit"

    elif expression.startswith("GDT("):
        match = re.search(r"GDT\s*\(\s*([A-Za-z]+)", expression)
        if not match:
            return {
                "status": "Deferred",
                "tolerance_valid": False,
                "error": "Malformed GDT expression"
            }

        gdt_type = match.group(1)
        if gdt_type not in GDT_KEYWORDS:
            return {
                "status": "Deferred",
                "tolerance_valid": False,
                "error": f"Unsupported GD&T type: {gdt_type}"
            }
        
        parsed_type = "GDT"

    if parsed_type not in TOLERANCE_TYPES:
        return {
            "status": "Deferred",
            "tolerance_valid": False,
            "error": f"Unsupported tolerance formalism: {expression}"
        }

    # ------------------------------------------------------------------
    # SUCCESS
    # ------------------------------------------------------------------
    return {
        "status": "Success",
        "tolerance_valid": True,
        "formalism": "Tolerance",
        "equation": expression,
        "reasoning": f"Resolved {parsed_type} tolerance specification"
    }