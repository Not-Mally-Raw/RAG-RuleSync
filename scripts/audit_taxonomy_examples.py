"""Audit formalized JSON examples from the taxonomy markdown.

This script is intentionally lightweight so it can be run whenever the
taxonomy document changes. It sends each final-schema JSON example through the
same normalization, canonicalization, and validation path used by the v3 API.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dfm_rule_pipeline.taxonomy.canonicalizer import canonicalize_envelope_payload
from dfm_rule_pipeline.taxonomy.models import model_dump_compat
from dfm_rule_pipeline.taxonomy.schema_factory import normalize_envelope_payload
from dfm_rule_pipeline.taxonomy.validator import TaxonomyValidator


DEFAULT_TAXONOMY_PATH = Path(r"C:\Users\patle\Downloads\Taxonomy_latest_draft_harshwardhan.md")
JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def is_placeholder(value: Any) -> bool:
    if value in ("", None):
        return True
    if isinstance(value, list):
        return all(is_placeholder(item) for item in value)
    return False


def final_schema_rule(rule: Any) -> bool:
    if not isinstance(rule, dict):
        return False
    constraints = rule.get("Constraints")
    if not isinstance(constraints, dict):
        return False
    required = {"Name", "RuleCategory", "Results", "RuleType", "Feature1", "Feature2", "Object1", "Object2"}
    if not required.issubset(rule):
        return False
    if "ValidationParamList" not in constraints:
        return False
    return any(str(rule.get(key, "")).strip() for key in ("Name", "RuleCategory", "Feature1", "Object1"))


def non_placeholder_params(params: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    for param in params:
        if not isinstance(param, dict):
            continue
        if is_placeholder(param.get("ExpName")) and is_placeholder(param.get("Operator")) and is_placeholder(param.get("Value")):
            continue
        result.append(param)
    return result


def flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from flatten_strings(item)


def infer_bucket(rule: Dict[str, Any]) -> str:
    constraints = rule.get("Constraints") or {}
    filters = non_placeholder_params(constraints.get("FilterParamList") or [])
    conditions = non_placeholder_params(constraints.get("ConditionParamList") or [])
    validations = non_placeholder_params(constraints.get("ValidationParamList") or [])
    additionals = [item for item in constraints.get("AdditionalParamList") or [] if isinstance(item, dict) and item.get("ExpName")]

    if rule.get("RuleType") == "Module":
        return "ModuleValidation"
    if rule.get("Feature1") == "Distance":
        return "DistanceRule"
    if len(conditions) > 1:
        return "NestedConditionalValidation"
    if conditions:
        return "ConditionalValidation"
    if len(validations) > 1:
        return "MultiExpressionValidation"
    if additionals:
        return "AdditionalInfoValidation"
    if filters:
        return "FilteredValidation"

    operators = [operator for param in validations for operator in flatten_strings(param.get("Operator")) if operator]
    values = [value.strip().lower() for param in validations for value in flatten_strings(param.get("Value")) if value]
    allowed = [value for param in validations for value in param.get("AllowedParams", []) if value]

    if "ANY" in operators:
        return "FeatureSetMembership"
    if len([operator for operator in operators if operator in {">", ">=", "<", "<="}]) >= 2:
        return "FeatureRangeValidation"
    if allowed:
        return "FeatureAllowedParamExpression"
    if any(value in {"yes", "no", "true", "false"} for value in values):
        return "FeatureBooleanValidation"
    return "FeatureSimpleValidation"


def extract_examples(markdown_path: Path) -> Tuple[List[Tuple[int, Dict[str, Any]]], List[Tuple[int, str]]]:
    text = markdown_path.read_text(encoding="utf-8", errors="ignore")
    examples: List[Tuple[int, Dict[str, Any]]] = []
    parse_failures: List[Tuple[int, str]] = []
    for index, block in enumerate(JSON_BLOCK_RE.findall(text), start=1):
        try:
            payload = json.loads(block)
        except json.JSONDecodeError as exc:
            parse_failures.append((index, str(exc)))
            continue
        if final_schema_rule(payload):
            examples.append((index, payload))
    return examples, parse_failures


def validate_example(block_index: int, rule: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    domain = rule.get("RuleCategory", "")
    bucket = infer_bucket(rule)
    normalized = normalize_envelope_payload(rule, fallback_domain=domain, fallback_bucket=bucket)
    canonical = canonicalize_envelope_payload(normalized, rule.get("Name", ""))
    _, errors = TaxonomyValidator().validate(canonical)
    return [model_dump_compat(error) for error in errors], canonical


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("taxonomy_path", nargs="?", default=str(DEFAULT_TAXONOMY_PATH))
    parser.add_argument("--show", type=int, default=25, help="Maximum failed examples to print.")
    args = parser.parse_args()

    taxonomy_path = Path(args.taxonomy_path)
    examples, parse_failures = extract_examples(taxonomy_path)
    failures = []
    buckets = Counter()
    domains = Counter()

    for block_index, rule in examples:
        bucket = infer_bucket(rule)
        buckets[bucket] += 1
        domains[rule.get("RuleCategory", "")] += 1
        errors, canonical = validate_example(block_index, rule)
        if errors:
            failures.append(
                {
                    "block": block_index,
                    "name": rule.get("Name", ""),
                    "domain": rule.get("RuleCategory", ""),
                    "bucket": bucket,
                    "errors": errors,
                    "canonical_rule": (canonical.get("taxonomy_rules") or [{}])[0],
                }
            )

    print(
        json.dumps(
            {
                "taxonomy_path": str(taxonomy_path),
                "examples": len(examples),
                "parse_failures": len(parse_failures),
                "validation_failures": len(failures),
                "domains": domains,
                "buckets": buckets,
            },
            indent=2,
            default=dict,
        )
    )

    for failure in failures[: args.show]:
        print(json.dumps(failure, indent=2))

    return 1 if failures or parse_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
