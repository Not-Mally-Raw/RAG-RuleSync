import json
import re
from llm.prompts import ATTRIBUTE_MATH_PROMPT

# ------------------------------------------------------------------
# HELPER: FORCE PASCAL CASE (The "Fixer")
# ------------------------------------------------------------------
def enforce_pascal_case(equation: str) -> str:
    """
    Forces 'object.attribute' patterns to 'Object.Attribute'.
    Example: 
      'slot.width' -> 'Slot.Width' (If and only if Slot is a valid schema object)
    """
    if not equation: 
        return equation

    def title_match(m):
        obj = m.group(1)
        attr = m.group(2)
        
        if obj.lower() == "moduleparams":
            obj = "ModuleParams" 
        else:
            obj = obj[0].upper() + obj[1:]
            
        attr = attr[0].upper() + attr[1:]
        return f"{obj}.{attr}"

    return re.sub(r"\b([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)\b", title_match, equation)

# ------------------------------------------------------------------
# MAIN FUNCTION
# ------------------------------------------------------------------
def formalize_attribute_rule(llm, rule_text: str, intent: dict, schema_context: str):
    
    attr = intent.get("attribute_constraint")
    if attr and isinstance(attr, dict) and attr.get("entity") and attr.get("attribute"):
        lhs = f"{attr['entity']}.{attr['attribute']}"
    else:
        lhs = "Target Unknown (Derive from Rule Text)"

    try:
        raw_output = llm.call(
            ATTRIBUTE_MATH_PROMPT.format(
                rule_text=rule_text,
                lhs=lhs,
                schema_context=schema_context
            )
        )
    except Exception as e:
        return {"formalism": None, "reasoning": f"LLM Generation Failed: {str(e)}"}

    expr = str(raw_output).strip().strip('"').strip("'")

    # -------------------------------------------------------
    # HANDLE SCHEMA GAP (NULL)
    # -------------------------------------------------------
    if not expr or expr.lower() == "null" or expr.lower() == "none":
        return {
            "formalism": None,
            "reasoning": "Schema Gap: Rule requires attributes not present in the strict schema."
        }

    # -------------------------------------------------------
    # FORCE CONSISTENCY
    # -------------------------------------------------------
    expr = enforce_pascal_case(expr)

    if "max(" in expr or "min(" in expr or " if " in expr:
        return {
            "formalism": "equation",
            "equation": expr,
            "reasoning": "Conditional attribute constraint expressed as equation."
        }

    return {
        "formalism": "equation",
        "equation": expr,
        "reasoning": "Attribute constraint expressed as equation."
    }