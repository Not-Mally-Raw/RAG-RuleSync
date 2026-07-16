from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

from .domain_normalizer import normalize_domain_name


BUCKET_RULE_TYPE_MAP = {
    "FeatureSimpleValidation": "Feature",
    "FeatureRangeValidation": "Feature",
    "FeatureSetMembership": "Feature",
    "FeatureBooleanValidation": "Feature",
    "FeatureTypedValueValidation": "Feature",
    "FeatureAllowedParamExpression": "Feature",
    "FilteredValidation": "Feature",
    "ConditionalValidation": "Feature",
    "AdditionalInfoValidation": "Feature",
    "DistanceRule": "Feature",
    "ModuleValidation": "Module",
    "MultiExpressionValidation": "Feature",
    "NestedConditionalValidation": "Feature",
    "MultiRuleDivergence": "Feature",
}


def placeholder_filter() -> Dict[str, Any]:
    return {"ExpName": "", "Operator": [""], "Value": [""]}


def placeholder_condition() -> Dict[str, Any]:
    return {"ExpName": "", "Operator": [[""]], "Value": [[[""]]]}


def placeholder_validation() -> Dict[str, Any]:
    return {"ExpName": "", "Operator": [[""]], "Value": [[[""]]], "AllowedParams": [""]}


def placeholder_additional() -> Dict[str, Any]:
    return {"ExpName": ""}


def placeholder_user() -> Dict[str, Any]:
    return {"ParamName": "", "DisplayName": "", "Value": [""], "MinValue": "", "MaxValue": ""}


def constraints_skeleton() -> Dict[str, Any]:
    return {
        "FilterParamList": [placeholder_filter()],
        "ConditionParamList": [placeholder_condition()],
        "ValidationParamList": [placeholder_validation()],
        "AdditionalParamList": [placeholder_additional()],
        "UserParamList": [placeholder_user()],
    }


def final_schema_skeleton() -> Dict[str, Any]:
    return {
        "Name": "",
        "RuleCategory": "",
        "Results": "",
        "RuleType": "",
        "Feature1": "",
        "Feature2": "",
        "Object1": "",
        "Object2": "",
        "Constraints": constraints_skeleton(),
    }


def _ensure_list(value: Any, fallback: List[Any]) -> List[Any]:
    if isinstance(value, list) and value:
        return value
    return deepcopy(fallback)


def _to_schema_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def _stringify_list(value: Any) -> Any:
    if isinstance(value, list):
        return [_stringify_list(item) for item in value]
    return _to_schema_string(value)


def _normalize_filter_param(value: Any) -> Dict[str, Any]:
    base = deepcopy(value) if isinstance(value, dict) else {}
    defaults = placeholder_filter()
    for key, default in defaults.items():
        base[key] = base.get(key, default)
    base["ExpName"] = _to_schema_string(base.get("ExpName"))
    base["Operator"] = _stringify_list(_ensure_list(base.get("Operator"), [""]))
    base["Value"] = _stringify_list(_ensure_list(base.get("Value"), [""]))
    return base


def _normalize_condition_param(value: Any) -> Dict[str, Any]:
    base = deepcopy(value) if isinstance(value, dict) else {}
    defaults = placeholder_condition()
    for key, default in defaults.items():
        base[key] = base.get(key, default)
    base["ExpName"] = _to_schema_string(base.get("ExpName"))
    base["Operator"] = _stringify_list(_ensure_list(base.get("Operator"), [[""]]))
    base["Value"] = _stringify_list(_ensure_list(base.get("Value"), [[[""]]]))
    return base


def _normalize_validation_param(value: Any) -> Dict[str, Any]:
    base = deepcopy(value) if isinstance(value, dict) else {}
    defaults = placeholder_validation()
    for key, default in defaults.items():
        base[key] = base.get(key, default)
    base["ExpName"] = _to_schema_string(base.get("ExpName"))
    base["Operator"] = _stringify_list(_ensure_list(base.get("Operator"), [[""]]))
    base["Value"] = _stringify_list(_ensure_list(base.get("Value"), [[[""]]]))
    base["AllowedParams"] = _stringify_list(_ensure_list(base.get("AllowedParams"), [""]))
    return base


def _normalize_additional_param(value: Any) -> Dict[str, Any]:
    base = deepcopy(value) if isinstance(value, dict) else {}
    defaults = placeholder_additional()
    for key, default in defaults.items():
        base[key] = base.get(key, default)
    base["ExpName"] = _to_schema_string(base.get("ExpName"))
    return base


def _normalize_user_param(value: Any) -> Dict[str, Any]:
    base = deepcopy(value) if isinstance(value, dict) else {}
    defaults = placeholder_user()
    for key, default in defaults.items():
        base[key] = base.get(key, default)
    base["ParamName"] = _to_schema_string(base.get("ParamName"))
    base["DisplayName"] = _to_schema_string(base.get("DisplayName"))
    base["Value"] = _stringify_list(_ensure_list(base.get("Value"), [""]))
    base["MinValue"] = _to_schema_string(base.get("MinValue"))
    base["MaxValue"] = _to_schema_string(base.get("MaxValue"))
    return base


def normalize_constraints(payload: Any) -> Dict[str, Any]:
    constraints = payload if isinstance(payload, dict) else {}
    normalized = {
        "FilterParamList": [
            _normalize_filter_param(item)
            for item in _ensure_list(constraints.get("FilterParamList"), [placeholder_filter()])
        ],
        "ConditionParamList": [
            _normalize_condition_param(item)
            for item in _ensure_list(constraints.get("ConditionParamList"), [placeholder_condition()])
        ],
        "ValidationParamList": [
            _normalize_validation_param(item)
            for item in _ensure_list(constraints.get("ValidationParamList"), [placeholder_validation()])
        ],
        "AdditionalParamList": [
            _normalize_additional_param(item)
            for item in _ensure_list(constraints.get("AdditionalParamList"), [placeholder_additional()])
        ],
        "UserParamList": [
            _normalize_user_param(item)
            for item in _ensure_list(constraints.get("UserParamList"), [placeholder_user()])
        ],
    }
    for key, value in constraints.items():
        if key not in normalized:
            normalized[key] = value
    return normalized


def normalize_rule_payload(
    payload: Any,
    domain: Optional[str] = None,
    bucket: Optional[str] = None,
) -> Dict[str, Any]:
    data = deepcopy(payload) if isinstance(payload, dict) else {}
    base = deepcopy(data)
    defaults = final_schema_skeleton()
    for key, default in defaults.items():
        if key == "Constraints":
            continue
        base[key] = base.get(key, default)
    for key in ("Name", "RuleCategory", "Results", "RuleType", "Feature1", "Feature2", "Object1", "Object2"):
        base[key] = _to_schema_string(base.get(key))

    normalized_domain = normalize_domain_name(domain or base.get("RuleCategory") or "")
    if normalized_domain:
        base["RuleCategory"] = normalized_domain
    base["Results"] = "Validation"
    if not base.get("RuleType"):
        base["RuleType"] = "Module" if bucket == "ModuleValidation" else "Feature"
    if bucket == "ModuleValidation" and not data.get("RuleType"):
        base["RuleType"] = "Module"
    if base.get("RuleType") in BUCKET_RULE_TYPE_MAP:
        base["RuleType"] = BUCKET_RULE_TYPE_MAP[base["RuleType"]]
    if bucket in BUCKET_RULE_TYPE_MAP and base.get("RuleType") not in {"Feature", "Module"}:
        base["RuleType"] = BUCKET_RULE_TYPE_MAP[bucket]

    base["Constraints"] = normalize_constraints(data.get("Constraints"))
    return base


def normalize_envelope_payload(payload: Any, fallback_domain: str, fallback_bucket: str) -> Dict[str, Any]:
    if isinstance(payload, list):
        data: Dict[str, Any] = {"taxonomy_rules": payload}
    elif isinstance(payload, dict) and "taxonomy_rules" in payload:
        data = deepcopy(payload)
    elif isinstance(payload, dict) and "TaxonomyRules" in payload:
        data = {
            "domain": payload.get("domain", payload.get("RuleCategory", "")),
            "bucket": payload.get("bucket", payload.get("RuleType", "")),
            "taxonomy_rules": payload.get("TaxonomyRules", []),
        }
    elif isinstance(payload, dict) and "Constraints" in payload:
        data = {"taxonomy_rules": [payload]}
    elif isinstance(payload, dict) and isinstance(payload.get("rule"), dict):
        data = {"taxonomy_rules": [payload["rule"]]}
    elif isinstance(payload, dict) and isinstance(payload.get("taxonomy_rule"), dict):
        data = {"taxonomy_rules": [payload["taxonomy_rule"]]}
    else:
        data = {"taxonomy_rules": []}

    domain = normalize_domain_name(data.get("domain") or fallback_domain)
    bucket = data.get("bucket") or fallback_bucket
    rules = data.get("taxonomy_rules") or []
    if not isinstance(rules, list):
        rules = [rules]

    return {
        "domain": domain,
        "bucket": bucket,
        "taxonomy_rules": [normalize_rule_payload(rule, domain=domain, bucket=bucket) for rule in rules],
    }
