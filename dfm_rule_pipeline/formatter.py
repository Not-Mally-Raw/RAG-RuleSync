import csv
import json
import logging
import re
import sys
from pathlib import Path

# -----------------------------
# Setup & Logging
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("DFM_FORMATTER")

# -----------------------------
# Domain Configuration
# -----------------------------
DOMAIN_CONFIG = {
    "sheetmetal": {"RuleCategory": "Sheet Metal", "ThickVar": "SheetMetal.Thickness", "Aliases": ["ModuleParams.Thickness", "NormalThickness"]},
    "sheet metal": {"RuleCategory": "Sheet Metal", "ThickVar": "SheetMetal.Thickness", "Aliases": ["ModuleParams.Thickness"]},
    "smform": {"RuleCategory": "Sheet Metal Forming", "ThickVar": "SheetMetalForm.NominalThickness", "Aliases": ["ModuleParams.NormalThickness"]},
    "turn": {"RuleCategory": "Turning", "ThickVar": "PartBody.NominalThickness", "Aliases": ["ModuleParams.Thickness"]},
    "turning": {"RuleCategory": "Turning", "ThickVar": "PartBody.NominalThickness", "Aliases": ["ModuleParams.Thickness"]},
    "mill": {"RuleCategory": "Milling", "ThickVar": "PartBody.NominalThickness", "Aliases": ["ModuleParams.Thickness"]},
    "drill": {"RuleCategory": "Drilling", "ThickVar": "PartBody.NominalThickness", "Aliases": ["ModuleParams.Thickness"]},
    "injection moulding": {"RuleCategory": "Injection Molding", "ThickVar": "InjectionMolding.NominalThickness", "Aliases": ["ModuleParams.NominalThickness"]},
    "die cast": {"RuleCategory": "Die Casting", "ThickVar": "PartBody.NominalThickness", "Aliases": ["WallThickness.MinValue"]},
    "additive": {"RuleCategory": "Additive Manufacturing", "ThickVar": "AMFace.MinThickness", "Aliases": ["ModuleParams.NominalThickness"]},
    "assembly": {"RuleCategory": "Assembly", "ThickVar": "Component.Thickness", "Aliases": []},
    "tubing": {"RuleCategory": "Tubing", "ThickVar": "Tube.OuterDiameter", "Aliases": ["ModuleParams.Thickness"]},
    "general": {"RuleCategory": "General", "ThickVar": "PartBody.NominalThickness", "Aliases": ["ModuleParams.Thickness"]}
}

# -----------------------------
# Logic Helpers
# -----------------------------
def clean_str(s):
    return s.strip() if isinstance(s, str) else ""

def split_camel_case(text):
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', text)

def generate_semantic_name(rule_text, feature, obj1, obj2, exp_name):
    # 1. Cleanup
    o1 = obj1.replace("Simple", "") if obj1 else ""
    o2 = obj2.replace("Simple", "") if obj2 else ""
    feat = feature.replace("Simple", "")
    
    # 2. Geometry
    if feat == "Distance" or "Distance" in exp_name:
        if o1 and o2:
            return f"{o1} Spacing Requirement" if o1 == o2 else f"{o1} to {o2} Clearance"
        if o1: return f"{o1} Clearance Check"
        return "Feature Clearance Check"

    # 3. Attribute
    attr_match = re.search(r'\.([a-zA-Z0-9]+)', exp_name)
    attr = attr_match.group(1) if attr_match else ""
    if attr:
        clean_attr = split_camel_case(attr)
        target = o1 if o1 else feat
        return f"{target} {clean_attr} Limit" if target else f"{clean_attr} Limit"

    # 4. Fallback
    clean_text = re.sub(r"[^a-zA-Z0-9 ]", "", rule_text)
    words = [w for w in clean_text.split() if w.lower() not in {'should','must','is','are','be','the','ensure'}]
    return " ".join(words[:4]).title() + " Rule"

def substitute_variables(expression, domain_cfg):
    if not expression: return expression
    target_var = domain_cfg["ThickVar"]
    for alias in domain_cfg["Aliases"]:
        expression = expression.replace(alias, target_var)
    expression = expression.replace("Distance(Hole, Hole)", "Distance.MinValue")
    expression = expression.replace("Distance(", "Distance.MinValue") 
    return expression

def normalize_algebra(lhs, operator, rhs, domain_cfg):
    thick_var = domain_cfg["ThickVar"]
    lhs = substitute_variables(lhs, domain_cfg)
    rhs = substitute_variables(rhs, domain_cfg)
    
    if "max(" in rhs.lower() or "min(" in rhs.lower() or "tolerance(" in lhs.lower():
        return lhs, operator, rhs

    esc_var = re.escape(thick_var)
    pattern = rf"(\d+\.?\d*)\s*\*\s*{esc_var}|{esc_var}\s*\*\s*(\d+\.?\d*)"
    match = re.search(pattern, rhs)
    
    if match:
        constant = match.group(1) if match.group(1) else match.group(2)
        remainder = re.sub(pattern, "", rhs).strip()
        new_lhs = lhs
        if remainder:
            if remainder.startswith("+"):
                term = remainder.strip("+ ")
                new_lhs = f"({lhs} - {term})"
            elif remainder.startswith("-"):
                term = remainder.strip("- ")
                new_lhs = f"({lhs} + {term})"
            else:
                return lhs, operator, rhs
        return f"{new_lhs}/{thick_var}", operator, float(constant)

    try:
        val = float(rhs)
    except ValueError:
        val = rhs 
    return lhs, operator, val

def parse_equation_string(eq_str):
    pattern = r"(>=|<=|==|!=|\bbetween\b|\bin\b|>|<)"
    match = re.search(pattern, eq_str)
    if match:
        operator = match.group(1)
        parts = eq_str.split(operator, 1)
        return parts[0].strip(), operator.strip(), parts[1].strip()
    return None, None, None

# -----------------------------
# Row Processor
# -----------------------------
def process_row(row):
    # 1. NORMALIZED KEY LOOKUP
    rule_text = row.get("rule_text") or row.get("RuleText") or ""
    status = clean_str(row.get("status") or row.get("Status"))
    status_lower = status.lower()
    decision = clean_str(row.get("resolution_status") or row.get("DecisionCode"))
    reasoning = clean_str(row.get("reasoning") or row.get("error") or "Unknown Reason")
    
    # 3. DOMAIN LOOKUP
    raw_domain = clean_str(row.get("domain") or row.get("RuleCategory") or "General").lower()
    config = DOMAIN_CONFIG.get(raw_domain, DOMAIN_CONFIG["general"])
    category_name = config["RuleCategory"]

    # ----------------------------------------------------
    # FAILURE HANDLING
    # ----------------------------------------------------
    # If the rule is marked skipped/invalid, or lacks text, fail immediately
    if not rule_text:
        return None # Only skip if text is totally missing
        
    if status_lower in ["skipped", "invalid", "review needed", "failed"]:
        return {
            "RuleText": rule_text,
            "Status": status,
            "DecisionCode": f"Failure({reasoning})",
            "RuleCategory": category_name,
            "dfm_json": ""
        }

    # Map the JSON/Equation fields
    raw_json_str = row.get("rule_json") or row.get("GeometryJSON")
    raw_eq_str = row.get("equation") or row.get("Equation") or row.get("ast")

    # If status is Success/Deferred but NO DATA found
    if not (raw_json_str or raw_eq_str):
        # Check if it was a Schema Gap (often in 'deferred')
        fail_reason = reasoning if reasoning else "No logic extracted"
        if "schema gap" in fail_reason.lower():
            fail_reason = "Schema Gap"
            
        return {
            "RuleText": rule_text,
            "Status": status,
            "DecisionCode": f"Failure({fail_reason})",
            "RuleCategory": category_name,
            "dfm_json": ""
        }

    # ----------------------------------------------------
    # PROCESSING LOGIC (Success Path)
    # ----------------------------------------------------
    lhs_raw, op_raw, rhs_raw = "", "", ""
    feature1, feature2, obj1, obj2 = "Attribute", "", "", ""
    
    # Path A: Geometry (JSON)
    if raw_json_str:
        try:
            geo = json.loads(raw_json_str)
            obj1 = geo.get("from", "")
            obj2 = geo.get("to", "")
            feature1 = "Distance"
            
            eq_str_internal = geo.get("rhs", "")
            lhs_raw, op_raw, rhs_raw = parse_equation_string(eq_str_internal)
            
            if "Distance" in lhs_raw: lhs_raw = "Distance.MinValue"
        except json.JSONDecodeError:
            return {
                "RuleText": rule_text,
                "Status": status,
                "DecisionCode": "Failure(Invalid Geometry JSON)",
                "RuleCategory": category_name,
                "dfm_json": ""
            }

    # Path B: Equation (String)
    elif raw_eq_str:
        if raw_eq_str.strip().startswith("Tolerance("):
            lhs_raw, op_raw, feature1, obj1 = raw_eq_str, "Function", "Tolerance", "Tolerance"
        else:
            lhs_raw, op_raw, rhs_raw = parse_equation_string(raw_eq_str)
            if lhs_raw and "." in lhs_raw:
                obj1 = lhs_raw.split(".")[0]
                feature1 = obj1 

    # Final check if parsing succeeded
    if not lhs_raw: 
        return {
            "RuleText": rule_text,
            "Status": status,
            "DecisionCode": "Failure(Equation Parsing Failed)",
            "RuleCategory": category_name,
            "dfm_json": ""
        }

    # 4. Normalization & Naming
    if op_raw == "Function":
        exp_name, final_op, recom = lhs_raw, "True", True
    else:
        exp_name, final_op, recom = normalize_algebra(lhs_raw, op_raw, rhs_raw, config)
    
    final_name = generate_semantic_name(rule_text, feature1, obj1, obj2, exp_name)

    dfm_rule = {
        "RuleCategory": category_name,
        "Name": final_name,
        "Feature1": feature1,
        "Feature2": feature2,
        "Object1": obj1,
        "Object2": obj2,
        "ExpName": exp_name,
        "Operator": final_op,
        "Recom": recom
    }
    
    return {
        "RuleText": rule_text,
        "Status": "Success",
        "DecisionCode": decision if decision else "formalized",
        "RuleCategory": category_name,
        "dfm_json": json.dumps(dfm_rule) 
    }

# -----------------------------
# Execution
# -----------------------------
def run_pipeline(input_file, output_file):
    input_path = Path(input_file)
    output_path = Path(output_file)
    processed_count = 0
    
    with input_path.open("r", encoding="utf-8-sig") as f_in, \
         output_path.open("w", encoding="utf-8", newline="") as f_out:
        
        reader = csv.DictReader(f_in)
        fieldnames = ["RuleText", "Status", "DecisionCode", "RuleCategory", "dfm_json"]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            result = process_row(row)
            if result:
                writer.writerow(result)
                processed_count += 1
                
    logger.info(f"Processed: {processed_count} rows | Output: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python formatter.py <input.csv> <output.csv>")
    else:
        run_pipeline(sys.argv[1], sys.argv[2])