import json
from dfm_rule_pipeline.schema.domain_definitions import DOMAIN_DEFINITIONS
from dfm_rule_pipeline.llm.prompts import DOMAIN_RESOLVER_PROMPT


def _build_definitions_block() -> str:
    """Format all domain definitions into a single text block for the prompt."""
    blocks = []
    for domain, definitions in DOMAIN_DEFINITIONS.items():
        blocks.append(f"### {domain}\n{definitions.strip()}")
    return "\n\n".join(blocks)


# Pre-build once at import time
_DEFINITIONS_BLOCK = _build_definitions_block()


def resolve_domain_semantic(llm, rule_text: str) -> dict:
    """
    Use the LLM to semantically match a rule to its manufacturing domain.
    Returns {"domain": str, "confidence": str, "reasoning": str}.
    """
    prompt = DOMAIN_RESOLVER_PROMPT.format(
        domain_definitions_block=_DEFINITIONS_BLOCK,
        rule_text=rule_text
    )

    try:
        raw = llm.call(prompt)
        # Strip markdown fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        result = json.loads(cleaned)
        domain = result.get("domain", "General")

        # Validate the domain exists in our definitions
        if domain not in DOMAIN_DEFINITIONS:
            domain = "General"

        return {
            "domain": domain,
            "confidence": result.get("confidence", "low"),
            "reasoning": result.get("reasoning", "")
        }
    except Exception as e:
        print(f"    ⚠️ Domain resolver LLM failed: {e}. Defaulting to General.")
        return {"domain": "General", "confidence": "low", "reasoning": f"LLM call failed: {e}"}


def resolve_rule_category_and_domain(llm, intent: dict, rule_text: str = "") -> dict:
    """
    Stage 2: Determine rule category (Advisory/Tolerance/Geometry/Attribute)
    and manufacturing domain (via LLM semantic matching).
    """
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

    # 2. Determine Domain via LLM semantic matching
    current_domain = intent.get("domain", "General")

    if current_domain == "General":
        domain_result = resolve_domain_semantic(llm, rule_text)
        current_domain = domain_result["domain"]

    return {
        "rule_category": category,
        "primary_domain": current_domain
    }