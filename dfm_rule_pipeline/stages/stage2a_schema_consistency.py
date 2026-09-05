import json
from dfm_rule_pipeline.schema.feature_schema import features_dict

# ------------------------------------------------------------------
# CANONICAL MAP (STRICT, EXPLICIT, SCHEMA-BOUND)
# ------------------------------------------------------------------
GEOMETRY_ENTITY_CANONICAL_MAP = {
    "Counterbore": "CBHole",
    "Countersink": "CSHole",
    "Counterdrill": "CDHole",
    "Curl": "RolledHem",
    "Hem": "Hem",
    "Edge": "PartEdge"
}


def extract_domain_objects(schema_text: str) -> set:
    objs = set()
    for line in schema_text.splitlines():
        if line.strip().startswith("Object:"):
            objs.add(line.split("Object:")[1].strip())
    return objs


def canonicalize_entity(entity: str, domain_objects: set) -> str:
    if not entity:
        return entity

    root = entity.split(".")[0]

    if root in domain_objects:
        return entity

    mapped = GEOMETRY_ENTITY_CANONICAL_MAP.get(root)
    if mapped and mapped in domain_objects:
        suffix = entity[len(root):]
        return mapped + suffix

    return entity


def check_schema_consistency(intent_json_str: str) -> str:
    """
    Strict schema consistency checker.
    Supports Geometry v1 and Geometry v2.
    """

    try:
        data = intent_json_str if isinstance(intent_json_str, dict) else json.loads(intent_json_str)
    except Exception:
        return json.dumps({
            "schema_consistent": False,
            "error": "Invalid JSON from intent stage"
        })

    domain = data.get("domain")
    geometry = data.get("geometry_relation")
    tolerance = data.get("tolerance")

    geometry_version = data.get("geometry_version", "v1")
    geometry_scope = data.get("geometry_scope")

    # ---------------------------------------------------------
    # 1. DOMAIN
    # ---------------------------------------------------------
    if domain not in features_dict:
        return json.dumps({
            "schema_consistent": False,
            "error": f"Schema Gap: Unknown domain '{domain}'"
        })

    domain_schema_text = features_dict[domain]
    domain_objects = extract_domain_objects(domain_schema_text)

    # ---------------------------------------------------------
    # 2. GEOMETRY CHECK
    # ---------------------------------------------------------
    if geometry:
        if geometry_version == "v2":
            # ---- Geometry v2: Cross-domain ----
            if not geometry_scope:
                return json.dumps({
                    "schema_consistent": False,
                    "error": "Geometry v2 requires geometry_scope"
                })

            for side in ["from", "to"]:
                ent = geometry.get(side)
                if not isinstance(ent, dict):
                    return json.dumps({
                        "schema_consistent": False,
                        "error": "Geometry v2 entities must be qualified objects"
                    })

                ent_domain = ent.get("domain")
                ent_name = ent.get("entity")

                if ent_domain not in features_dict:
                    return json.dumps({
                        "schema_consistent": False,
                        "error": f"Unknown geometry domain '{ent_domain}'"
                    })

                ent_schema_text = features_dict[ent_domain]
                ent_objects = extract_domain_objects(ent_schema_text)

                if ent_name not in ent_objects:
                    return json.dumps({
                        "schema_consistent": False,
                        "error": (
                            f"Schema Gap: Geometry entity '{ent_name}' "
                            f"not in domain '{ent_domain}'"
                        )
                    })

        else:
            # ---- Geometry v1: Single-domain ----
            for side in ["from", "to"]:
                ent = geometry.get(side)
                if not ent:
                    continue

                canonical = canonicalize_entity(ent, domain_objects)
                root = canonical.split(".")[0]

                if root not in domain_objects:
                    return json.dumps({
                        "schema_consistent": False,
                        "error": (
                            f"Schema Gap: Geometry entity '{ent}' "
                            f"not defined in '{domain}'"
                        )
                    })

                geometry[side] = canonical

    # ---------------------------------------------------------
    # 3. TOLERANCE (DOMAIN-LOCAL ONLY)
    # ---------------------------------------------------------
    if tolerance:
        tol_obj = tolerance.get("object")
        if tol_obj and tol_obj not in domain_objects:
            return json.dumps({
                "schema_consistent": False,
                "error": f"Schema Gap: Tolerance object '{tol_obj}' not defined"
            })

    # ---------------------------------------------------------
    # PASS
    # ---------------------------------------------------------
    return json.dumps({
        "schema_consistent": True
    })
