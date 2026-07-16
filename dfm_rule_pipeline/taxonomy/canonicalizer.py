from copy import deepcopy
import re
from typing import Any, Dict, List

from .knowledge import (
    GLOBAL_PATH_ALIASES,
    MODULE_EXPRESSION_PREFIXES,
    OBJECT_ALIASES_BY_DOMAIN,
    PATH_ALIASES_BY_DOMAIN,
    THICKNESS_VARIABLE_BY_DOMAIN,
)
from .schema_factory import normalize_envelope_payload, placeholder_filter


REF_RE = re.compile(r"\b[A-Z][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")
RANGE_WORDS = {"between", "range"}


def _aliases_for_domain(domain: str) -> Dict[str, str]:
    aliases = dict(GLOBAL_PATH_ALIASES)
    aliases.update(PATH_ALIASES_BY_DOMAIN.get(domain, {}))
    return aliases


def _canonical_path(domain: str, value: Any) -> str:
    if not isinstance(value, str):
        return "" if value is None else str(value)
    compact = re.sub(r"\s*/\s*", "/", value.strip())
    aliases = _aliases_for_domain(domain)
    if compact in aliases:
        return aliases[compact]

    lowered = compact.lower()
    if lowered in {"sheet thickness", "material thickness", "nominal thickness", "normal thickness"}:
        return THICKNESS_VARIABLE_BY_DOMAIN.get(domain, compact)
    return compact


def _map_expression_refs(domain: str, expression: Any) -> str:
    if not isinstance(expression, str):
        return "" if expression is None else str(expression)
    mapped = re.sub(r"\s*/\s*", "/", expression.strip())
    for source, target in sorted(_aliases_for_domain(domain).items(), key=lambda item: len(item[0]), reverse=True):
        mapped = mapped.replace(source, target)
    return mapped


def _clear_module_applicability_filters(rule: Dict[str, Any]) -> None:
    filters = rule.setdefault("Constraints", {}).get("FilterParamList", [])
    cleaned = []
    for item in filters:
        exp_name = item.get("ExpName", "") if isinstance(item, dict) else ""
        if exp_name in {"ModuleParams.IsSheetMetalPart"}:
            continue
        cleaned.append(item)
    rule["Constraints"]["FilterParamList"] = cleaned or [placeholder_filter()]


def _normalize_objects(rule: Dict[str, Any], domain: str) -> None:
    aliases = OBJECT_ALIASES_BY_DOMAIN.get(domain, {})
    for key in ("Object1", "Object2"):
        value = rule.get(key, "")
        if value in aliases:
            rule[key] = aliases[value]


def _first_scalar(value: Any) -> str:
    try:
        return str(value[0][0][0])
    except Exception:
        return ""


def _set_single_validation_value(validation: Dict[str, Any], value: str) -> None:
    validation["Value"] = [[[value]]]


def _normalize_ratio_expname_value(validation: Dict[str, Any], domain: str) -> None:
    exp_name = validation.get("ExpName", "")
    if not isinstance(exp_name, str) or not exp_name.startswith("Distance.MinValue/"):
        return

    left, right = exp_name.split("/", 1)
    param = _canonical_path(domain, right)
    if "." not in param:
        return

    validation["ExpName"] = _canonical_path(domain, left)
    validation["AllowedParams"] = [param]

    current = _first_scalar(validation.get("Value"))
    if current and "*" not in current:
        _set_single_validation_value(validation, f"{current}*{param}")
    else:
        _set_single_validation_value(validation, _map_expression_refs(domain, current))


def _normalize_operator_words(param: Dict[str, Any]) -> None:
    operators = param.get("Operator", [[""]])
    if not isinstance(operators, list):
        return
    normalized = []
    changed = False
    for group in operators:
        if not isinstance(group, list):
            normalized.append(group)
            continue
        clean_group = []
        for op in group:
            op_str = str(op).strip()
            lowered = op_str.lower()
            if lowered in RANGE_WORDS:
                clean_group.extend([">", "<"])
                changed = True
            elif lowered in {"in", "any", "one of", "from list"}:
                clean_group.append("ANY")
                changed = True
            else:
                clean_group.append(op_str)
        normalized.append(clean_group)
    if changed:
        param["Operator"] = normalized


def _normalize_any_values(param: Dict[str, Any]) -> None:
    operators = param.get("Operator", [])
    active_ops = [op for group in operators if isinstance(group, list) for op in group if op]
    if active_ops != ["ANY"]:
        return

    values = param.get("Value", [])
    if not isinstance(values, list) or not values:
        return
    branch = values[0]
    if not isinstance(branch, list):
        return
    if len(branch) == 1 and isinstance(branch[0], list) and len(branch[0]) > 1:
        param["Value"] = [[[str(item)] for item in branch[0]]]
    elif all(isinstance(item, str) for item in branch):
        param["Value"] = [[[str(item)] for item in branch]]


def _normalize_range_values(param: Dict[str, Any]) -> None:
    operators = param.get("Operator", [])
    for group_idx, ops in enumerate(operators):
        if not isinstance(ops, list):
            continue
        active_ops = [op for op in ops if op]
        if len(active_ops) != 2 or not all(op in {">", ">=", "<", "<="} for op in active_ops):
            continue
        values = param.get("Value", [])
        if not values or not isinstance(values[0], list):
            continue
        if group_idx < len(values[0]) and isinstance(values[0][group_idx], list) and len(values[0][group_idx]) == 2:
            continue
        flat = []
        for branch in values:
            if isinstance(branch, list):
                for group in branch:
                    if isinstance(group, list):
                        flat.extend(group)
                    else:
                        flat.append(group)
            else:
                flat.append(branch)
        if len(flat) >= 2:
            param["Value"] = [[[str(flat[0]), str(flat[1])]]]


def _extract_refs(expression: Any) -> List[str]:
    if not isinstance(expression, str) or not expression:
        return []
    return sorted(set(REF_RE.findall(expression)))


def _ensure_allowed_params(validation: Dict[str, Any]) -> None:
    exp_refs = set(_extract_refs(validation.get("ExpName", "")))
    value_refs = set()
    for branch in validation.get("Value", []):
        if not isinstance(branch, list):
            continue
        for group in branch:
            if not isinstance(group, list):
                continue
            for value in group:
                value_refs.update(_extract_refs(value))

    allowed = [item for item in validation.get("AllowedParams", [""]) if item]
    for ref in sorted(value_refs - exp_refs - set(allowed)):
        allowed.append(ref)
    validation["AllowedParams"] = allowed or [""]


def _replace_identifier_alias(text: str, alias: str, replacement: str) -> str:
    return re.sub(rf"(?<![A-Za-z0-9_]){re.escape(alias)}(?![A-Za-z0-9_])", replacement, text)


def _normalize_user_param_aliases(rule: Dict[str, Any]) -> None:
    constraints = rule.setdefault("Constraints", {})
    user_params = constraints.get("UserParamList", [])
    alias_to_name: Dict[str, str] = {}

    for user_param in user_params:
        if not isinstance(user_param, dict):
            continue
        param_name = str(user_param.get("ParamName", "") or "").strip()
        if not param_name:
            continue
        values = user_param.get("Value", [])
        if not isinstance(values, list):
            values = [values]
        symbolic_values = []
        for value in values:
            alias = str(value or "").strip()
            if alias and alias != param_name and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", alias):
                alias_to_name[alias] = param_name
                symbolic_values.append(alias)
        if symbolic_values and all(str(value or "").strip() in symbolic_values for value in values):
            user_param["Value"] = [""]

    if not alias_to_name:
        return

    for validation in constraints.get("ValidationParamList", []):
        if not isinstance(validation, dict):
            continue
        normalized_values = []
        for branch in validation.get("Value", []):
            normalized_branch = []
            for group in branch:
                normalized_group = []
                for value in group:
                    updated = str(value)
                    for alias, param_name in alias_to_name.items():
                        updated = _replace_identifier_alias(updated, alias, param_name)
                    normalized_group.append(updated)
                normalized_branch.append(normalized_group)
            normalized_values.append(normalized_branch)
        validation["Value"] = normalized_values


def _normalize_module_ratio(rule: Dict[str, Any], validation: Dict[str, Any], domain: str) -> None:
    exp_name = _canonical_path(domain, validation.get("ExpName", ""))
    allowed = validation.get("AllowedParams", [""])
    allowed_refs = [_canonical_path(domain, item) for item in allowed if item]

    if exp_name == "Turn.Body.Length/Turn.Body.MinOuterDiameter":
        validation["ExpName"] = exp_name
        validation["AllowedParams"] = [""]
        rule["RuleType"] = "Module"
        return

    if allowed_refs and allowed_refs[0] == "Turn.Body.Length/Turn.Body.MinOuterDiameter":
        validation["ExpName"] = allowed_refs[0]
        validation["AllowedParams"] = [""]
        rule["RuleType"] = "Module"


def _normalize_module_material(rule: Dict[str, Any], validation: Dict[str, Any], domain: str) -> None:
    exp_name = _canonical_path(domain, validation.get("ExpName", ""))
    if exp_name != "PartBody.Material":
        return
    validation["ExpName"] = exp_name
    rule["RuleType"] = "Module"
    _clear_module_applicability_filters(rule)


def _normalize_module_expression(rule: Dict[str, Any], validation: Dict[str, Any]) -> None:
    expression = str(validation.get("ExpName", ""))
    if any(expression.startswith(prefix) for prefix in MODULE_EXPRESSION_PREFIXES):
        rule["RuleType"] = "Module"


def _normalize_module_rule_shape(rule: Dict[str, Any]) -> None:
    if rule.get("RuleType") != "Module":
        return
    rule["Feature1"] = ""
    rule["Feature2"] = ""
    rule["Object1"] = ""
    rule["Object2"] = ""


def _normalize_validation(validation: Dict[str, Any], domain: str, rule: Dict[str, Any]) -> None:
    validation["ExpName"] = _canonical_path(domain, validation.get("ExpName", ""))
    validation["AllowedParams"] = [
        _canonical_path(domain, item) if item else ""
        for item in validation.get("AllowedParams", [""])
    ]
    validation["Value"] = [
        [
            [_map_expression_refs(domain, leaf) for leaf in group]
            for group in branch
        ]
        for branch in validation.get("Value", [[[""]]])
    ]
    _normalize_operator_words(validation)
    _normalize_any_values(validation)
    _normalize_range_values(validation)
    _normalize_ratio_expname_value(validation, domain)
    _normalize_module_ratio(rule, validation, domain)
    _normalize_module_material(rule, validation, domain)
    _ensure_allowed_params(validation)
    _normalize_module_expression(rule, validation)


def _normalize_rule(rule: Dict[str, Any], domain: str) -> None:
    _normalize_objects(rule, domain)
    constraints = rule.setdefault("Constraints", {})
    validations = constraints.setdefault("ValidationParamList", [])
    if not validations:
        validations.append({"ExpName": "", "Operator": [[""]], "Value": [[[""]]], "AllowedParams": [""]})

    for validation in validations:
        if isinstance(validation, dict):
            _normalize_validation(validation, domain, rule)

    for param in constraints.get("ConditionParamList", []):
        if isinstance(param, dict):
            param["ExpName"] = _canonical_path(domain, param.get("ExpName", ""))
            _normalize_operator_words(param)
            _normalize_range_values(param)

    for param in constraints.get("FilterParamList", []):
        if isinstance(param, dict):
            param["ExpName"] = _canonical_path(domain, param.get("ExpName", ""))

    for param in constraints.get("AdditionalParamList", []):
        if isinstance(param, dict):
            param["ExpName"] = _canonical_path(domain, param.get("ExpName", ""))

    _normalize_user_param_aliases(rule)
    _normalize_module_rule_shape(rule)


def canonicalize_envelope_payload(payload: Dict[str, Any], rule_text: str = "") -> Dict[str, Any]:
    data = deepcopy(payload)
    domain = data.get("domain", "")
    rules: List[Dict[str, Any]] = data.get("taxonomy_rules", [])
    for rule in rules:
        if isinstance(rule, dict):
            _normalize_rule(rule, domain or rule.get("RuleCategory", ""))
    return normalize_envelope_payload(data, fallback_domain=domain, fallback_bucket=data.get("bucket", ""))
