import json
from dfm_rule_pipeline.llm.prompts import FORMALIZATION_PROMPT
from dfm_rule_pipeline.schema.feature_schema import features_dict


def formalize_rule(llm, schema_mapping_json: str) -> str:
    print("\n🔹 STAGE 3: FORMALIZATION")

    # --------------------------------------------------
    # Parse schema mapping
    # --------------------------------------------------
    try:
        validated = json.loads(schema_mapping_json)
    except Exception:
        return json.dumps({
            "formalism": None,
            "equation": None,
            "ast": None,
            "reasoning": "Schema mapping JSON could not be parsed."
        })

    # --------------------------------------------------
    # Respect deferrals
    # --------------------------------------------------
    if validated.get("schema_valid") is False:
        return json.dumps({
            "formalism": None,
            "equation": None,
            "ast": None,
            "reasoning": validated.get("error", "Rule not eligible for formalization.")
        })

    domain = validated.get("domain")
    schema_text = features_dict.get(domain, features_dict.get("General"))

    # --------------------------------------------------
    # LLM formalization
    # --------------------------------------------------
    prompt = FORMALIZATION_PROMPT.format(
        validated_json=json.dumps(validated, indent=2),
        schema_context=schema_text
    )

    raw = llm.call(prompt).strip()

    if "```" in raw:
        raw = raw.split("```", 1)[1].replace("json", "").strip()

    print(f"    → Formalization Output: {raw}")

    # --------------------------------------------------
    # Enforce output contract
    # --------------------------------------------------
    try:
        parsed = json.loads(raw)

        formalism = parsed.get("formalism")

        if formalism not in ("equation", "AST", None):
            raise ValueError("Invalid formalism type")

        if formalism == "equation" and not parsed.get("equation"):
            raise ValueError("Equation formalism without equation")

        if formalism == "AST" and not parsed.get("ast"):
            raise ValueError("AST formalism without AST")

    except Exception as e:
        return json.dumps({
            "formalism": None,
            "equation": None,
            "ast": None,
            "reasoning": f"Formalization output invalid: {e}"
        })

    return raw
