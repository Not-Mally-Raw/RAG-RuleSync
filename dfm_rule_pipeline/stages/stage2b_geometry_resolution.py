import json
import re
from dfm_rule_pipeline.llm.prompts import GEO_MATH_PROMPT
from dfm_rule_pipeline.schema.feature_schema import features_dict

# --------------------------------------------------
# STRONG ENTITY NORMALIZATION
# --------------------------------------------------
# Mapped STRICTLY to schema/feature_schema.py keys
ENTITY_NORMALIZATION = {
    # --- COMMON GEOMETRY ---
    "hole": "Hole",
    "holes": "Hole",
    "adjacent holes": "Hole",
    "edge": "PartEdge",
    "edges": "PartEdge",
    "edge of a hole": "PartEdge",
    "part edge": "PartEdge",
    
    # --- SHEET METAL ---
    "bend": "Bend",
    "bends": "Bend",
    "bend line": "Bend",
    "flange": "Flange",
    "flanges": "Flange",
    "cutout": "Cutout",
    "cutouts": "Cutout",
    "hem": "Hem",
    "hems": "Hem",
    "curl": "RolledHem",
    "curls": "RolledHem",
    "rolled hem": "RolledHem",
    "bridge": "Bridge",
    "bridges": "Bridge",
    "gusset": "Gusset",
    "gussets": "Gusset",
    "lance": "Lance",
    "louver": "Louver",
    "notch": "Notch",
    "dowel": "Dowel",
    "card guide": "CardGuide",
    "spoon": "Spoon",
    "emboss": "Emboss",
    "embosses": "Emboss",
    "emboss feature": "Emboss",
    "extruded hole": "ExtrudedHole",
    "dimple": "Dimple",
    "dimples": "Dimple",
    "slot": "SimpleCutout",
    "tab": "Tab",
    "weld": "Weld",

    # --- MACHINING (MILL/TURN/DRILL) ---
    "counterbore": "CBHole",
    "counterbores": "CBHole",
    "countersunk hole": "CSHole",
    "countersunk holes": "CSHole",
    "cs hole": "CSHole",
    "countersink": "CSHole",
    "countersinks": "CSHole",
    "pocket": "Pocket",
    "fillet": "Fillet",
    "bored hole": "BoredHole", # Turn specific

    # --- INJECTION MOLDING / DIE CASTING ---
    "boss": "Boss",
    "rib": "Rib",
    "wall": "Wall",
    
    # --- ASSEMBLY / TUBING ---
    "bolt": "Bolt",
    "tube": "Tube",
    "pipe": "Tube"
}

def normalize_entity(raw: str):
    if not raw: 
        return None

    text = raw.lower().strip()

    # exact match
    if text in ENTITY_NORMALIZATION:
        return ENTITY_NORMALIZATION[text]

    # fuzzy recovery: find known token inside phrase
    # Sorted by length descending to catch "countersunk hole" before "hole"
    for key in sorted(ENTITY_NORMALIZATION.keys(), key=len, reverse=True):
        if key in text:
            return ENTITY_NORMALIZATION[key]

    return None


# --------------------------------------------------
# GEOMETRY RESOLUTION
# --------------------------------------------------

def resolve_geometry(llm, rule_text: str, intent: dict) -> dict:
    if isinstance(intent, str):
        intent = json.loads(intent)

    geo = intent.get("raw_geometry_relation") or intent.get("geometry_relation")
    if not geo:
        return {
            "geometry_valid": False,
            "error": "No explicit geometry relation found"
        }

    raw_from = geo.get("from")
    raw_to = geo.get("to")

    entity_a = normalize_entity(raw_from)
    entity_b = normalize_entity(raw_to)

    # 🔒 Adjacent / spacing rules → same-entity geometry
    if entity_a and not entity_b:
        entity_b = entity_a

    # 🔒 Explicit adjacent keyword fallback
    if not entity_b and "adjacent" in rule_text.lower():
        entity_b = entity_a

    if not entity_a or not entity_b:
        # Return error so we can debug, but structure it safely
        return {
            "geometry_valid": False,
            "error": f"Geometry entity could not be resolved: '{raw_from}' -> {entity_a}, '{raw_to}' -> {entity_b}"
        }

    rule_type = intent.get("rule_intent", {}).get("type", "").lower()
    operator = "<=" if rule_type == "max" else ">="

    geo_function = f"Distance({entity_a}, {entity_b})"

    prompt = GEO_MATH_PROMPT.format(
        rule_text=rule_text,
        geo_function=geo_function,
        entity_a=entity_a,
        entity_b=entity_b,
        schema_context=features_dict.get(intent.get("domain", "General"), features_dict.get("General", ""))
    )

    raw_rhs = llm.call(prompt)
    rhs = str(raw_rhs).replace("```", "").strip()

    if not rhs:
        return {
            "geometry_valid": False,
            "error": "Geometry RHS expression missing"
        }

    return {
        "geometry_valid": True,
        "formalism": "Geometry",
        "geometry": {
            "relation": "distance",
            "from": entity_a,
            "to": entity_b,
            "operator": operator,
            "rhs": rhs
        },
        "reasoning": "Resolved explicit feature-to-feature spatial constraint"
    }