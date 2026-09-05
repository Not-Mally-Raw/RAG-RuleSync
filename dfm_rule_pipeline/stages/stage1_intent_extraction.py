import json
from dfm_rule_pipeline.llm.prompts import INTENT_PROMPT
# We removed call_with_timeout import because we trust the client's infinite loop

def extract_intent(llm, rule_text: str) -> dict:
    print("🧠 extract_intent ENTERED")
    print("🧠 rule_text:", rule_text)

    # -------------------------------
    # LLM CALL (BLOCKING & ROBUST)
    # -------------------------------
    # The llm.call() method now handles all retries, failovers (Groq->Cerebras),
    # and wait loops internally. We just wait for the result.
    
    prompt = INTENT_PROMPT.format(rule_text=rule_text)
    print("📤 INTENT PROMPT LENGTH:", len(prompt))
    print("📤 CALLING LLM (intent)")

    try:
        # No timeout wrapper. We wait until the client succeeds.
        raw = llm.call(prompt)
    except Exception as e:
        # This catches legitimate crashes (auth errors, etc), not timeouts.
        print("❌ LLM FATAL ERROR:", e)
        return _intent_fallback(f"LLM Call Failed: {e}")

    print("🧠 RAW LLM OUTPUT:", repr(raw))

    raw = str(raw).strip()
    # print("🧠 RAW STRIPPED:", repr(raw)) # Optional debug

    # -------------------------------
    # SAFE JSON EXTRACTION
    # -------------------------------
    def _safe_json_load(raw: str):
        # print("🧠 JSON BEFORE LOAD:", repr(raw))

        # HARD STRIP non-JSON junk
        start = raw.find("{")
        end = raw.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("No valid JSON object found")

        raw_json = raw[start:end + 1]

        # print("🧠 JSON FINAL STRING:", raw_json)
        return json.loads(raw_json)

    try:
        parsed = _safe_json_load(raw)

        if not isinstance(parsed, dict):
            raise TypeError("Top-level JSON is not an object")

        # -------------------------------
        # KEY NORMALIZATION
        # -------------------------------
        cleaned = {}
        for k, v in parsed.items():
            if isinstance(k, str):
                k_clean = k.strip().strip('"').strip()
            else:
                k_clean = str(k)

            cleaned[k_clean] = v

        parsed = cleaned

        # print("🧠 PARSED JSON TYPE:", type(parsed))
        # print("🧠 PARSED JSON KEYS:", list(parsed.keys()))

    except Exception as e:
        print("❌ INTENT PARSE FAILED:", e)
        return _intent_fallback(f"Intent parse failure: {e}")

    # -------------------------------
    # STRUCTURAL NORMALIZATION
    # -------------------------------
    parsed.setdefault("geometry_relation", None)
    parsed.setdefault("tolerance", None)
    parsed.setdefault("attribute_constraint", None)
    parsed.setdefault("reasoning", "")

    # -------------------------------
    # RULE INTENT CANONICALIZATION
    # -------------------------------
    parsed["rule_intent"] = {
        "type": parsed.get("rule_type", "advisory"),
        "is_quantifiable": bool(parsed.get("is_quantifiable", False)),
        "requires_geometry": bool(parsed.get("requires_geometry", False)),
        "requires_tolerance": bool(parsed.get("requires_tolerance", False)),
    }

    return parsed


# -------------------------------------------------
# FALLBACK (SINGLE SOURCE OF TRUTH)
# -------------------------------------------------
def _intent_fallback(reason: str) -> dict:
    return {
        "rule_intent": {
            "type": "advisory",
            "is_quantifiable": False,
            "requires_geometry": False,
            "requires_tolerance": False
        },
        "geometry_relation": None,
        "tolerance": None,
        "attribute_constraint": None,
        "reasoning": reason
    }