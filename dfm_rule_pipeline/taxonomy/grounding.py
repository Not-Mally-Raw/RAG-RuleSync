import re
from typing import Any, Dict, Iterable, List, Set

from .knowledge import OBJECT_TEXT_ALIASES
from .models import TaxonomyValidationError


REF_RE = re.compile(r"\b[A-Z][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")
ALWAYS_ALLOWED_ROOTS = {
    "Distance",
    "ModuleParams",
    "SheetMetal",
    "Sheetmetal",
    "SheetMetalForm",
    "SheetmetalForming",
    "PartBody",
    "PartFace",
    "InjectionMolding",
    "AdditiveManufacturing",
    "Mill",
    "Milling",
    "Turn",
    "Turning",
}


def _err(code: str, message: str, location: str, suggestion: str = "") -> TaxonomyValidationError:
    return TaxonomyValidationError(code=code, message=message, location=location, suggestion=suggestion)


def _split_camel(value: str) -> str:
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", value)
    return re.sub(r"\s+", " ", spaced).strip()


def _term_in_text(text: str, term: str) -> bool:
    normalized = term.strip().lower()
    if not normalized:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text) is not None


def _aliases_for_object(obj: str) -> Set[str]:
    aliases = set(OBJECT_TEXT_ALIASES.get(obj, []))
    aliases.add(obj)
    aliases.add(_split_camel(obj))
    aliases.add(obj.replace("_", " "))
    return {alias.lower() for alias in aliases if alias}


def _object_is_grounded(rule_text: str, obj: str) -> bool:
    if not obj:
        return True
    text = rule_text.lower()
    return any(_term_in_text(text, alias) for alias in _aliases_for_object(obj))


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)


def _schema_refs(rule: Dict[str, Any]) -> Iterable[str]:
    constraints = rule.get("Constraints", {}) if isinstance(rule, dict) else {}
    for param_list in ("FilterParamList", "ConditionParamList", "ValidationParamList", "AdditionalParamList"):
        for param in constraints.get(param_list, []):
            if not isinstance(param, dict):
                continue
            for field in ("ExpName", "Value", "AllowedParams"):
                for text in _flatten_strings(param.get(field, "")):
                    yield from REF_RE.findall(text)


def validate_grounding(rule_text: str, payload: Dict[str, Any]) -> List[TaxonomyValidationError]:
    errors: List[TaxonomyValidationError] = []
    if not rule_text or not isinstance(payload, dict):
        return errors

    rules = payload.get("taxonomy_rules", [])
    if not isinstance(rules, list):
        return errors

    for rule_idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        base = f"$.taxonomy_rules[{rule_idx}]"

        for object_key in ("Object1", "Object2"):
            obj = str(rule.get(object_key, "") or "")
            if obj and not _object_is_grounded(rule_text, obj):
                errors.append(
                    _err(
                        "object_grounding_failed",
                        f"{object_key} {obj} is not grounded in the source rule text.",
                        f"{base}.{object_key}",
                        "Use an object named in the rule text or a valid taxonomy alias; do not copy objects from examples.",
                    )
                )

        for ref in _schema_refs(rule):
            root = ref.split(".", 1)[0]
            if root in ALWAYS_ALLOWED_ROOTS:
                continue
            if not _object_is_grounded(rule_text, root):
                errors.append(
                    _err(
                        "object_grounding_failed",
                        f"Formula reference {ref} uses object {root}, which is not grounded in the source rule text.",
                        f"{base}.Constraints",
                        "Replace copied or unrelated formula references with schema paths for objects named in the rule.",
                    )
                )

    return errors
