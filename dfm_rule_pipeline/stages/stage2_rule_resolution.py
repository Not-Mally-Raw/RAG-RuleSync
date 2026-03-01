import json
from schema.feature_schema import features_dict

DOMAIN_KEYWORDS = {
    "Sheetmetal": ["sheet metal", "bend", "flange", "hem", "cutout", "emboss", "gusset", "louver", "stamp", "bridge", "spoon"],
    "Turn": ["turn", "groove", "bore", "relief"],
    "Mill": ["mill", "pocket", "fillet", "chamfer"],
    "Drill": ["drill", "counterbore", "countersink", "tapping"],
    "Injection Moulding": ["injection", "mould", "mold", "rib", "boss", "draft"],
    "Die Cast": ["die cast", "die-cast", "mold wall"],
    "Tubing": ["tube", "tubing", "uniform bend"],
    "Assembly": ["assembly", "fastener", "bolt", "nut", "interference"],
    "Additive": ["additive", "3d print", "layer", "overhang"],
}

def resolve_rule_category_and_domain(intent: dict, rule_text: str = "") -> dict:
    rule_intent = intent.get("rule_intent", {})
    
    # 1. Determine Category
    rule_type = rule_intent.get("type", "advisory")
    requires_geometry = rule_intent.get("requires_geometry", False)
    requires_tolerance = rule_intent.get("requires_tolerance", False)

    if rule_type == "advisory" and not (requires_geometry or requires_tolerance):
        category = "Advisory"
    elif requires_tolerance:
        category = "Tolerance"
    elif requires_geometry:
        category = "Geometry"
    else:
        category = "Attribute"

    # 2. Determine Domain (Only if not already set by explicit override)
    # If the intent already has a domain from Priority 1, we preserve it.
    current_domain = intent.get("domain", "General")
    
    if current_domain == "General":
        rule_lower = rule_text.lower()
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(k in rule_lower for k in keywords):
                current_domain = domain
                break
    
    return {
        "rule_category": category,
        "primary_domain": current_domain
    }