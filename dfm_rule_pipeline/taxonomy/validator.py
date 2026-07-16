import re
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from pydantic import ValidationError

from dfm_rule_pipeline.schema.features import features_dict

from .bucket_registry import is_supported_bucket
from .domain_normalizer import LATEST_DOMAINS, normalize_domain_name, schema_domain_key
from .knowledge import DOMAIN_SCHEMA_EXTENSIONS
from .models import (
    TaxonomyEnvelope,
    TaxonomyRule,
    TaxonomyValidationError,
    model_dump_compat,
    model_validate_compat,
)


LEGACY_FIELD_RE = re.compile(r"^(Recom|ExpName|Operator|Value)\d+$")
LEGACY_FIELDS = {"Recom", "ExpName1", "ExpName2", "Operator1", "Operator2", "Value1", "Value2", "Recom1", "Recom2"}
SUPPORTED_OPERATORS = {"", "=", "==", "!=", ">", ">=", "<", "<=", "ANY"}
RANGE_OPERATORS = {">", ">=", "<", "<="}
DOMAIN_PREFIXES = {
    "Assembly",
    "Additive",
    "AdditiveManufacturing",
    "DieCasting",
    "Drilling",
    "General",
    "InjectionMolding",
    "Mill",
    "Milling",
    "SheetMetal",
    "Sheetmetal",
    "SheetMetalForm",
    "SheetmetalForming",
    "Sheetmetal",
    "Tubing",
    "Turn",
    "Turning",
}
REF_RE = re.compile(r"\b[A-Z][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")


def _err(code: str, message: str, location: str, suggestion: str = "") -> TaxonomyValidationError:
    return TaxonomyValidationError(code=code, message=message, location=location, suggestion=suggestion)


def _split_attrs(raw: str) -> Set[str]:
    attrs: Set[str] = set()
    for piece in raw.split(","):
        attr = piece.strip()
        if not attr:
            continue
        alias_match = re.match(r"^([A-Za-z0-9_]+)\s*\(([A-Za-z0-9_]+)\)$", attr)
        if alias_match:
            attrs.add(alias_match.group(1))
            attrs.add(alias_match.group(2))
            continue
        attrs.add(attr)
    return attrs


def _parse_feature_schema(text: str) -> Dict[str, Set[str]]:
    parsed: Dict[str, Set[str]] = {}
    current_object: Optional[str] = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        object_match = re.match(r"Object:\s*([A-Za-z0-9_]+)", line)
        if object_match:
            current_object = object_match.group(1)
            parsed.setdefault(current_object, set())
            continue
        attrs_match = re.match(r"Attributes:\s*(.+)", line)
        if attrs_match and current_object:
            parsed.setdefault(current_object, set()).update(_split_attrs(attrs_match.group(1)))
    return parsed


def _merge_attrs(target: Dict[str, Set[str]], source: Dict[str, Set[str]]) -> None:
    for obj, attrs in source.items():
        target.setdefault(obj, set()).update(attrs)


def _add_virtuals(schema_key: str, parsed: Dict[str, Set[str]]) -> None:
    model_schema = _parse_feature_schema(features_dict.get("Model", ""))
    _merge_attrs(parsed, model_schema)

    parsed.setdefault("Distance", set()).update({"MinValue", "Value", "CustomValue"})
    parsed.setdefault("PartFace", set()).update({"Color"})
    parsed.setdefault("PartBody", set()).update(
        {"Material", "Length", "Width", "Height", "DiagonalLength", "TightBoxDiagonalLength", "NominalThickness"}
    )
    parsed.setdefault("PartEdge", set()).update({"IsSharp", "Distance", "MinDistance"})

    if schema_key == "Sheetmetal":
        parsed.setdefault("SheetMetal", set()).update({"Thickness", "IsSheetMetalPart"})
        parsed.setdefault("Sheetmetal", set()).update({"Thickness", "IsSheetMetalPart"})
        parsed.setdefault("PartBody", set()).update({"Material", "NominalThickness"})
    elif schema_key == "SMForm":
        parsed.setdefault("SheetMetalForm", set()).update({"NominalThickness", "NormalThickness"})
        parsed.setdefault("SheetmetalForming", set()).update({"NominalThickness", "NormalThickness"})
        parsed.setdefault("Hole", set()).update({"Diameter", "Radius"})
    elif schema_key == "Injection Moulding":
        parsed.setdefault("InjectionMolding", set()).update({"NominalThickness"})
        parsed.setdefault("PartBody", set()).update({"NominalThickness"})
    elif schema_key == "Die Cast":
        parsed.setdefault("PartBody", set()).update({"NominalThickness"})
    elif schema_key == "Assembly":
        parsed.setdefault("Component", set()).update({"Material"})
    elif schema_key == "Additive":
        parsed.setdefault("AdditiveManufacturing", set()).update({"NominalThickness", "PrintSize", "SubProcessType"})
    elif schema_key == "Mill":
        parsed.setdefault("Mill", set()).update({"Machinability"})
        parsed.setdefault("Milling", set()).update({"Machinability"})
        parsed.setdefault("PartBody", set()).update({"NominalThickness"})
    elif schema_key == "Turn":
        parsed.setdefault("Turn", set()).update({"Body"})
        parsed.setdefault("Turning", set()).update({"Body"})
        parsed.setdefault("PartBody", set()).update({"NominalThickness"})

    taxonomy_domain = normalize_domain_name(schema_key)
    if taxonomy_domain in DOMAIN_SCHEMA_EXTENSIONS:
        for obj, attrs in DOMAIN_SCHEMA_EXTENSIONS[taxonomy_domain].items():
            parsed.setdefault(obj, set()).update(attrs)


@lru_cache(maxsize=32)
def domain_schema(domain: str) -> Dict[str, Set[str]]:
    schema_key = schema_domain_key(domain)
    parsed = _parse_feature_schema(features_dict.get(schema_key, ""))
    _add_virtuals(schema_key, parsed)
    return parsed


def extract_schema_refs(expr: Any) -> List[str]:
    if not isinstance(expr, str) or not expr:
        return []
    return sorted(set(REF_RE.findall(expr)))


def _case_lookup(mapping: Dict[str, Set[str]], key: str) -> Optional[str]:
    if key in mapping:
        return key
    lowered = key.lower()
    for candidate in mapping:
        if candidate.lower() == lowered:
            return candidate
    return None


def _attr_lookup(attrs: Set[str], key: str) -> Optional[str]:
    if key in attrs:
        return key
    lowered = key.lower()
    for candidate in attrs:
        if candidate.lower() == lowered:
            return candidate
    return None


def validate_schema_ref(ref: str, domain: str, location: str) -> List[TaxonomyValidationError]:
    parts = ref.split(".")
    if len(parts) < 2:
        return []

    schema = domain_schema(domain)

    if len(parts) >= 3 and parts[0] in DOMAIN_PREFIXES:
        prefixed_root = _case_lookup(schema, parts[1])
        if prefixed_root and _attr_lookup(schema[prefixed_root], parts[2]):
            return []

    root = _case_lookup(schema, parts[0])
    if not root:
        return [
            _err(
                "schema_root_failed",
                f"Root object {parts[0]} is not valid for {normalize_domain_name(domain) or domain}.",
                location,
                "Use an object from the detected domain schema or correct the rule domain.",
            )
        ]

    attr = parts[1]
    if not _attr_lookup(schema[root], attr):
        return [
            _err(
                "schema_attribute_failed",
                f"Attribute {attr} is not valid for {root} in {normalize_domain_name(domain) or domain}.",
                location,
                "Use a valid attribute for the root object in the domain feature schema.",
            )
        ]
    return []


def _is_placeholder(value: Any) -> bool:
    if value in ("", None):
        return True
    if isinstance(value, list):
        return all(_is_placeholder(item) for item in value)
    return False


def _param_is_placeholder(param: Any) -> bool:
    return _is_placeholder(getattr(param, "ExpName", "")) and _is_placeholder(getattr(param, "Operator", [])) and _is_placeholder(
        getattr(param, "Value", [])
    )


def _legacy_fields(payload: Any, location: str = "$") -> List[str]:
    found: List[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_location = f"{location}.{key}"
            if key in LEGACY_FIELDS or LEGACY_FIELD_RE.match(key):
                found.append(child_location)
            found.extend(_legacy_fields(value, child_location))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            found.extend(_legacy_fields(item, f"{location}[{idx}]"))
    return found


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)


def _validate_operator_groups(groups: List[List[str]], location: str) -> List[TaxonomyValidationError]:
    errors: List[TaxonomyValidationError] = []
    if not isinstance(groups, list) or not all(isinstance(group, list) for group in groups):
        return [_err("operator_shape_invalid", "Operator must be a list of string lists.", location)]
    for group_idx, group in enumerate(groups):
        for op in group:
            if op not in SUPPORTED_OPERATORS:
                errors.append(
                    _err(
                        "unsupported_operator",
                        f"Operator {op} is not supported.",
                        f"{location}[{group_idx}]",
                        "Use one of =, ==, !=, >, >=, <, <=, or ANY.",
                    )
                )
    return errors


def _validate_filter_operator(operators: List[str], location: str) -> List[TaxonomyValidationError]:
    if not isinstance(operators, list) or not all(isinstance(op, str) for op in operators):
        return [_err("operator_shape_invalid", "Filter Operator must be a flat list of strings.", location)]
    return [
        _err("unsupported_operator", f"Operator {op} is not supported.", f"{location}[{idx}]")
        for idx, op in enumerate(operators)
        if op not in SUPPORTED_OPERATORS
    ]


def _value_branch_count(value: List[List[List[str]]]) -> int:
    return len(value) if isinstance(value, list) else 0


def _validate_range_and_any(param: Any, location: str) -> List[TaxonomyValidationError]:
    errors: List[TaxonomyValidationError] = []
    branch_specific_operators = (
        len(param.Operator) > 1
        and len(param.Operator) == len(param.Value)
        and all(isinstance(branch, list) and len(branch) == 1 for branch in param.Value)
    )
    if branch_specific_operators:
        for branch_idx, ops in enumerate(param.Operator):
            active_ops = [op for op in ops if op]
            if len(active_ops) == 2 and all(op in RANGE_OPERATORS for op in active_ops):
                if len(param.Value[branch_idx][0]) != 2:
                    errors.append(
                        _err(
                            "range_shape_invalid",
                            "Range validation must provide exactly two values for the branch-specific range operator group.",
                            f"{location}.Value[{branch_idx}][0]",
                            'Use Value branch [["lower", "upper"]] for branch-specific range operators.',
                        )
                    )
            elif active_ops == ["ANY"]:
                branch = param.Value[branch_idx]
                if not branch or any(not isinstance(item, list) or len(item) != 1 for item in branch):
                    errors.append(
                        _err(
                            "any_shape_invalid",
                            "ANY validation must encode each allowed value as a separate single-value list.",
                            f"{location}.Value[{branch_idx}]",
                            'Use Value [[["A"], ["B"]]], not [[["A", "B"]]].',
                        )
                    )
        return errors

    for group_idx, ops in enumerate(param.Operator):
        active_ops = [op for op in ops if op]
        if len(active_ops) == 2 and all(op in RANGE_OPERATORS for op in active_ops):
            for branch_idx, branch in enumerate(param.Value):
                if group_idx >= len(branch) or len(branch[group_idx]) != 2:
                    errors.append(
                        _err(
                            "range_shape_invalid",
                            "Range validation must provide exactly two values for the range operator group.",
                            f"{location}.Value[{branch_idx}][{group_idx}]",
                            'Use Value [[["lower", "upper"]]] for a one-branch range.',
                        )
                    )
        if active_ops == ["ANY"]:
            for branch_idx, branch in enumerate(param.Value):
                if not branch or any(not isinstance(item, list) or len(item) != 1 for item in branch):
                    errors.append(
                        _err(
                            "any_shape_invalid",
                            "ANY validation must encode each allowed value as a separate single-value list.",
                            f"{location}.Value[{branch_idx}]",
                            'Use Value [[["A"], ["B"]]], not [[["A", "B"]]].',
                        )
                    )
    return errors


def _validate_refs(expressions: Iterable[str], domain: str, location: str) -> List[TaxonomyValidationError]:
    errors: List[TaxonomyValidationError] = []
    for expression in expressions:
        for ref in extract_schema_refs(expression):
            errors.extend(validate_schema_ref(ref, domain, location))
    return errors


def _allowed_params_missing(param: Any, location: str, domain: str) -> List[TaxonomyValidationError]:
    errors: List[TaxonomyValidationError] = []
    exp_refs = set(extract_schema_refs(param.ExpName))
    value_refs = set()
    for value in _flatten_strings(param.Value):
        value_refs.update(extract_schema_refs(value))
    allowed = {item for item in param.AllowedParams if item}
    missing = sorted(ref for ref in value_refs if ref not in exp_refs and ref not in allowed)
    for ref in missing:
        errors.append(
            _err(
                "allowed_params_missing",
                f"Formula reference {ref} must be mirrored in AllowedParams.",
                f"{location}.AllowedParams",
                "Add the schema reference to AllowedParams or move it into ExpName if it is part of the measured expression.",
            )
        )
    errors.extend(_validate_refs(allowed, domain, f"{location}.AllowedParams"))
    return errors


class TaxonomyValidator:
    def validate(self, payload: Any) -> Tuple[Optional[TaxonomyEnvelope], List[TaxonomyValidationError]]:
        errors: List[TaxonomyValidationError] = []
        for field_location in _legacy_fields(payload):
            errors.append(
                _err(
                    "legacy_field_detected",
                    "Legacy flat-only field is not allowed in taxonomy v3 output.",
                    field_location,
                    "Use the final nested Constraints schema only.",
                )
            )

        try:
            envelope = model_validate_compat(TaxonomyEnvelope, payload)
        except ValidationError as exc:
            errors.append(
                _err(
                    "model_parse_failed",
                    str(exc),
                    "$",
                    "Return the exact taxonomy envelope with domain, bucket, and taxonomy_rules.",
                )
            )
            return None, errors

        domain = normalize_domain_name(envelope.domain)
        if not domain:
            errors.append(_err("model_parse_failed", "Envelope domain is required.", "$.domain"))
        elif domain not in LATEST_DOMAINS:
            errors.append(
                _err(
                    "schema_root_failed",
                    f"Domain {envelope.domain} is not supported by taxonomy v3.",
                    "$.domain",
                    "Use a supported taxonomy domain such as SheetMetal, Drilling, Assembly, or General.",
                )
            )

        if not envelope.bucket:
            errors.append(_err("unsupported_bucket", "Envelope bucket is required.", "$.bucket"))
        elif not is_supported_bucket(envelope.bucket):
            errors.append(_err("unsupported_bucket", f"Bucket {envelope.bucket} is not supported.", "$.bucket"))

        if not envelope.taxonomy_rules:
            errors.append(_err("model_parse_failed", "At least one taxonomy rule is required.", "$.taxonomy_rules"))

        for idx, rule in enumerate(envelope.taxonomy_rules):
            errors.extend(self._validate_rule(rule, domain or envelope.domain, envelope.bucket, idx))

        return envelope, errors

    def _validate_rule(self, rule: TaxonomyRule, domain: str, bucket: str, rule_idx: int) -> List[TaxonomyValidationError]:
        errors: List[TaxonomyValidationError] = []
        base = f"$.taxonomy_rules[{rule_idx}]"
        constraints = rule.Constraints

        if normalize_domain_name(rule.RuleCategory) != normalize_domain_name(domain):
            errors.append(
                _err(
                    "schema_root_failed",
                    "RuleCategory must match the envelope domain.",
                    f"{base}.RuleCategory",
                    "Use the normalized taxonomy domain in both envelope.domain and RuleCategory.",
                )
            )

        if rule.Results != "Validation":
            errors.append(
                _err(
                    "result_field_invalid",
                    "Results must be the literal value Validation.",
                    f"{base}.Results",
                    "Put equations only in Constraints.ValidationParamList; Results is not an expression field.",
                )
            )

        if rule.RuleType not in {"Feature", "Module"}:
            errors.append(
                _err(
                    "model_parse_failed",
                    f"RuleType {rule.RuleType} is not supported.",
                    f"{base}.RuleType",
                    'Use "Feature" or "Module".',
                )
            )

        if rule.RuleType == "Module" and any([rule.Feature1, rule.Feature2, rule.Object1, rule.Object2]):
            errors.append(
                _err(
                    "module_feature_conflict",
                    "Module rules must not fill Feature1, Feature2, Object1, or Object2.",
                    f"{base}.RuleType",
                    "Leave feature/object fields empty for ModuleValidation.",
                )
            )

        if bucket == "DistanceRule" or rule.Feature1 == "Distance":
            if not rule.Object1 or not rule.Object2:
                errors.append(
                    _err(
                        "distance_object_missing",
                        "Distance rules must include Object1 and Object2.",
                        f"{base}.Object1",
                        "Set Object1 and Object2 to the two measured objects.",
                    )
                )

        non_placeholder_validation_count = 0
        for idx, param in enumerate(constraints.FilterParamList):
            location = f"{base}.Constraints.FilterParamList[{idx}]"
            if _param_is_placeholder(param):
                continue
            errors.extend(_validate_filter_operator(param.Operator, f"{location}.Operator"))
            errors.extend(_validate_refs([param.ExpName], domain, f"{location}.ExpName"))
            errors.extend(_validate_refs(_flatten_strings(param.Value), domain, f"{location}.Value"))

        condition_branch_counts: List[int] = []
        for idx, param in enumerate(constraints.ConditionParamList):
            location = f"{base}.Constraints.ConditionParamList[{idx}]"
            if _param_is_placeholder(param):
                continue
            errors.extend(_validate_operator_groups(param.Operator, f"{location}.Operator"))
            errors.extend(_validate_range_and_any(param, location))
            errors.extend(_validate_refs([param.ExpName], domain, f"{location}.ExpName"))
            errors.extend(_validate_refs(_flatten_strings(param.Value), domain, f"{location}.Value"))
            condition_branch_counts.append(_value_branch_count(param.Value))

        for idx, param in enumerate(constraints.ValidationParamList):
            location = f"{base}.Constraints.ValidationParamList[{idx}]"
            if _param_is_placeholder(param):
                continue
            non_placeholder_validation_count += 1
            errors.extend(_validate_operator_groups(param.Operator, f"{location}.Operator"))
            errors.extend(_validate_range_and_any(param, location))
            errors.extend(_validate_refs([param.ExpName], domain, f"{location}.ExpName"))
            errors.extend(_validate_refs(_flatten_strings(param.Value), domain, f"{location}.Value"))
            errors.extend(_allowed_params_missing(param, location, domain))

        for idx, param in enumerate(constraints.AdditionalParamList):
            location = f"{base}.Constraints.AdditionalParamList[{idx}]"
            if not param.ExpName:
                continue
            errors.extend(_validate_refs([param.ExpName], domain, f"{location}.ExpName"))

        if non_placeholder_validation_count == 0:
            errors.append(
                _err(
                    "model_parse_failed",
                    "At least one non-placeholder validation parameter is required.",
                    f"{base}.Constraints.ValidationParamList",
                    "Put pass/fail checks in ValidationParamList.",
                )
            )

        if condition_branch_counts:
            first_count = condition_branch_counts[0]
            if any(count != first_count for count in condition_branch_counts):
                errors.append(
                    _err(
                        "branch_alignment_failed",
                        "All condition entries must have the same branch count.",
                        f"{base}.Constraints.ConditionParamList",
                        "Align condition branch tables by index.",
                    )
                )
            for idx, param in enumerate(constraints.ValidationParamList):
                if _param_is_placeholder(param):
                    continue
                branch_count = _value_branch_count(param.Value)
                if branch_count != first_count:
                    errors.append(
                        _err(
                            "branch_alignment_failed",
                            "Validation value branch count must match condition branch count.",
                            f"{base}.Constraints.ValidationParamList[{idx}].Value",
                            "Provide one validation value branch for each condition branch.",
                        )
                    )

        return errors


def errors_to_dicts(errors: List[TaxonomyValidationError]) -> List[Dict[str, Any]]:
    return [model_dump_compat(error) for error in errors]
