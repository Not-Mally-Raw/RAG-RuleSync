"""Audit the 89 legacy DFX rule samples against taxonomy v3 validation.

The samples file contains source rule text plus an old flat DFM format. This
module parses that legacy format into a v3-like rule envelope only for testing
and regression coverage; it does not drive the production endpoint.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dfm_rule_pipeline.taxonomy.bucket_registry import classify_bucket
from dfm_rule_pipeline.taxonomy.canonicalizer import canonicalize_envelope_payload
from dfm_rule_pipeline.taxonomy.domain_normalizer import normalize_domain_name
from dfm_rule_pipeline.taxonomy.models import model_dump_compat
from dfm_rule_pipeline.taxonomy.schema_factory import normalize_envelope_payload
from dfm_rule_pipeline.taxonomy.validator import TaxonomyValidator


DEFAULT_SAMPLES_PATH = Path(r"C:\Users\patle\Downloads\HCL\DFXRuleSamples.md")
ENTRY_RE = re.compile(r"^\*\*(\d+)\. Rule Category:\*\*\s*(.*?)\s*$", re.MULTILINE)
KV_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_ ]*?)(\d*)\s*[:=]\s*(.*)$")
INLINE_KV_RE = re.compile(r"([A-Za-z][A-Za-z0-9_ ]*)\s*=\s*([^,]+)")


def clean_value(value: Any) -> str:
    text = str(value or "").strip()
    text = text.strip()
    text = text.strip('"')
    text = text.strip()
    if text in {'""""', '"""', '""'}:
        return ""
    return text


def placeholder_filter() -> Dict[str, Any]:
    return {"ExpName": "", "Operator": [""], "Value": [""]}


def placeholder_condition() -> Dict[str, Any]:
    return {"ExpName": "", "Operator": [[""]], "Value": [[[""]]]}


def placeholder_additional() -> Dict[str, Any]:
    return {"ExpName": ""}


def placeholder_user() -> Dict[str, Any]:
    return {"ParamName": "", "DisplayName": "", "Value": [""], "MinValue": "", "MaxValue": ""}


def parse_inline_kv(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for key, value in INLINE_KV_RE.findall(text):
        result[key.strip().replace(" ", "")] = clean_value(value)
    return result


def clean_format_line(line: str) -> str:
    stripped = line.strip()
    stripped = stripped.strip('"')
    stripped = stripped.strip()
    return stripped


def next_content_line(lines: List[str], start: int) -> str:
    for index in range(start, len(lines)):
        line = clean_format_line(lines[index])
        if line:
            return line
    return ""


def condition_from_line(line: str, next_line: str) -> Optional[Dict[str, str]]:
    if line.lower().startswith("constraint"):
        payload = line.split(":", 1)[1] if ":" in line else ""
        condition = parse_inline_kv(payload)
    elif next_line == "{":
        condition = parse_inline_kv(line)
    else:
        return None

    if {"ExpName", "Operator", "Value"}.issubset(condition):
        condition["Operator"] = normalize_operator(condition["Operator"])
        return condition
    return None


def parse_condition_tree(lines: List[str]) -> Tuple[List[Tuple[List[Dict[str, str]], Dict[str, str]]], List[str]]:
    branches: List[Tuple[List[Dict[str, str]], Dict[str, str]]] = []
    remaining: List[str] = []

    def parse_scope(index: int, inherited: List[Dict[str, str]]) -> int:
        leaf_lines: List[str] = []
        while index < len(lines):
            line = clean_format_line(lines[index])
            if not line:
                index += 1
                continue
            if line == "}":
                if inherited and leaf_lines:
                    validation = parse_simple_kv_lines(leaf_lines)
                    if validation.get("ExpName"):
                        branches.append((inherited, validation))
                elif not inherited:
                    remaining.extend(leaf_lines)
                return index + 1
            if line == "{":
                index += 1
                continue

            next_line = next_content_line(lines, index + 1)
            condition = condition_from_line(line, next_line)
            if condition:
                index += 1
                if next_content_line(lines, index) == "{":
                    while index < len(lines) and clean_format_line(lines[index]) != "{":
                        index += 1
                    index += 1
                index = parse_scope(index, inherited + [condition])
                continue

            leaf_lines.append(lines[index])
            index += 1

        if inherited and leaf_lines:
            validation = parse_simple_kv_lines(leaf_lines)
            if validation.get("ExpName"):
                branches.append((inherited, validation))
        elif not inherited:
            remaining.extend(leaf_lines)
        return index

    parse_scope(0, [])
    return branches, remaining


def choose_operator_group(branch_ops: List[List[str]]) -> List[str]:
    candidates = [ops for ops in branch_ops if any(ops)]
    if not candidates:
        return [""]
    return max(candidates, key=len)


def parse_condition_blocks(lines: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    branches, remaining = parse_condition_tree(lines)
    if not branches:
        return [], [], remaining

    condition_names: List[str] = []
    for branch_conditions, _ in branches:
        for condition in branch_conditions:
            exp_name = condition.get("ExpName", "")
            if exp_name and exp_name not in condition_names:
                condition_names.append(exp_name)

    conditions: List[Dict[str, Any]] = []
    for exp_name in condition_names:
        branch_ops: List[List[str]] = []
        branch_values: List[List[str]] = []
        for branch_conditions, _ in branches:
            matching = [condition for condition in branch_conditions if condition.get("ExpName") == exp_name]
            ops = [condition.get("Operator", "") for condition in matching]
            values = [condition.get("Value", "") for condition in matching]
            branch_ops.append(ops)
            branch_values.append(values)

        operator_group = choose_operator_group(branch_ops)
        width = len(operator_group)
        aligned_values = []
        for values in branch_values:
            padded = values[:width] + [""] * max(0, width - len(values))
            aligned_values.append([padded])
        conditions.append({"ExpName": exp_name, "Operator": [operator_group], "Value": aligned_values})

    validation_groups: Dict[Tuple[str, str], List[str]] = {}
    for _, validation in branches:
        exp_name = validation.get("ExpName", "")
        operator = normalize_operator(validation.get("Operator", ""))
        value = validation.get("Recom") or validation.get("Value") or ""
        validation_groups.setdefault((exp_name, operator), []).append(value)

    validations = [
        {
            "ExpName": exp_name,
            "Operator": [[operator]],
            "Value": [[[value]] for value in values],
            "AllowedParams": [""],
        }
        for (exp_name, operator), values in validation_groups.items()
        if exp_name
    ]
    return conditions, validations, remaining


def parse_simple_kv_lines(lines: Iterable[str]) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for raw_line in lines:
        line = clean_format_line(raw_line)
        if not line or line in {"{", "}"}:
            continue
        match = KV_RE.match(line)
        if not match:
            continue
        key = f"{match.group(1).strip().replace(' ', '')}{match.group(2)}"
        parsed[key] = clean_value(match.group(3))
    return parsed


def normalize_operator(operator: str) -> str:
    op = clean_value(operator)
    lowered = op.lower()
    if lowered in {"in", "any", "one of", "from list"}:
        return "ANY"
    return op


def add_validation(records: List[Dict[str, str]], exp_name: str, operator: str, value: str) -> None:
    if not exp_name:
        return
    records.append(
        {
            "ExpName": exp_name,
            "Operator": [[normalize_operator(operator)]],
            "Value": [[[value]]],
            "AllowedParams": [""],
        }
    )


def parse_validation_records(lines: Iterable[str]) -> List[Dict[str, Any]]:
    records: List[Dict[str, str]] = []
    by_suffix: Dict[str, Dict[str, str]] = {}
    current_suffix: Optional[str] = None
    auto_suffix = 0

    for raw_line in lines:
        line = clean_format_line(raw_line)
        match = KV_RE.match(line)
        if not match:
            continue
        raw_key = match.group(1).strip().replace(" ", "")
        suffix = match.group(2)
        value = clean_value(match.group(3))

        if raw_key == "ExpName":
            if not suffix:
                auto_suffix += 1
                suffix = f"auto{auto_suffix}"
            current_suffix = suffix
            by_suffix.setdefault(suffix, {})["ExpName"] = value
        elif raw_key in {"Operator", "Recom", "Value"}:
            target_suffix = suffix or current_suffix or "auto1"
            by_suffix.setdefault(target_suffix, {})[raw_key] = value

    for suffix in sorted(by_suffix, key=lambda item: (not item.startswith("auto"), item)):
        item = by_suffix[suffix]
        add_validation(records, item.get("ExpName", ""), item.get("Operator", ""), item.get("Recom") or item.get("Value", ""))
    return records


def extract_rule_text(segment: str) -> str:
    match = re.search(r"\*\*Rule Text:\*\*\s*(.*?)\n\*\*DFM Format:\*\*", segment, re.DOTALL)
    if not match:
        return ""
    return clean_value(" ".join(match.group(1).split()))


def extract_format_lines(segment: str) -> List[str]:
    marker = "**DFM Format:**"
    if marker not in segment:
        return []
    format_text = segment.split(marker, 1)[1]
    return [line for line in format_text.splitlines() if clean_format_line(line)]


def rule_type_from_fields(fields: Dict[str, str]) -> str:
    feature_fields = [fields.get("Feature1", ""), fields.get("Feature2", ""), fields.get("Object1", ""), fields.get("Object2", "")]
    return "Feature" if any(clean_value(value) for value in feature_fields) else "Module"


def parse_entry(entry_id: int, source_category: str, segment: str) -> Dict[str, Any]:
    rule_text = extract_rule_text(segment)
    format_lines = extract_format_lines(segment)
    condition_params, condition_validations, remaining_lines = parse_condition_blocks(format_lines)
    fields = parse_simple_kv_lines(remaining_lines)
    validations = condition_validations or parse_validation_records(remaining_lines)
    domain = normalize_domain_name(fields.get("RuleCategory") or source_category)
    rule = {
        "Name": fields.get("Name", f"Rule {entry_id}"),
        "RuleCategory": domain,
        "Results": "Validation",
        "RuleType": rule_type_from_fields(fields),
        "Feature1": clean_value(fields.get("Feature1", "")),
        "Feature2": clean_value(fields.get("Feature2", "")),
        "Object1": clean_value(fields.get("Object1", "")),
        "Object2": clean_value(fields.get("Object2", "")),
        "Constraints": {
            "FilterParamList": [placeholder_filter()],
            "ConditionParamList": condition_params or [placeholder_condition()],
            "ValidationParamList": validations or [{"ExpName": "", "Operator": [[""]], "Value": [[[""]]], "AllowedParams": [""]}],
            "AdditionalParamList": [placeholder_additional()],
            "UserParamList": [placeholder_user()],
        },
    }
    return {
        "id": entry_id,
        "source_category": source_category,
        "rule_text": rule_text,
        "legacy_rule": rule,
    }


def extract_samples(samples_path: Path) -> List[Dict[str, Any]]:
    text = samples_path.read_text(encoding="utf-8", errors="ignore")
    matches = list(ENTRY_RE.finditer(text))
    samples: List[Dict[str, Any]] = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        segment = text[match.start() : end]
        samples.append(parse_entry(int(match.group(1)), match.group(2).strip(), segment))
    return samples


def validate_sample(sample: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rule = sample["legacy_rule"]
    bucket = classify_bucket(sample.get("rule_text", ""))
    normalized = normalize_envelope_payload(rule, fallback_domain=rule.get("RuleCategory", ""), fallback_bucket=bucket)
    canonical = canonicalize_envelope_payload(normalized, sample.get("rule_text", ""))
    _, errors = TaxonomyValidator().validate(canonical)
    return [model_dump_compat(error) for error in errors], canonical


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("samples_path", nargs="?", default=str(DEFAULT_SAMPLES_PATH))
    parser.add_argument("--show", type=int, default=25)
    parser.add_argument("--output-json", default="", help="Optional path to save canonical v3 outputs for all samples.")
    args = parser.parse_args()

    samples = extract_samples(Path(args.samples_path))
    failures = []
    outputs = []
    domains = Counter()
    buckets = Counter()
    for sample in samples:
        domains[sample["legacy_rule"].get("RuleCategory", "")] += 1
        buckets[classify_bucket(sample.get("rule_text", ""))] += 1
        errors, canonical = validate_sample(sample)
        outputs.append(
            {
                "id": sample["id"],
                "rule_text": sample.get("rule_text", ""),
                "source_category": sample.get("source_category", ""),
                "domain": canonical.get("domain", ""),
                "bucket": canonical.get("bucket", ""),
                "taxonomy_rules": canonical.get("taxonomy_rules", []),
                "validation_errors": errors,
            }
        )
        if errors:
            failures.append(
                {
                    "id": sample["id"],
                    "rule_text": sample.get("rule_text", ""),
                    "domain": sample["legacy_rule"].get("RuleCategory", ""),
                    "bucket": canonical.get("bucket", ""),
                    "errors": errors,
                    "canonical_rule": (canonical.get("taxonomy_rules") or [{}])[0],
                }
            )

    print(
        json.dumps(
            {
                "samples": len(samples),
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

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(outputs, indent=2), encoding="utf-8")
        print(json.dumps({"output_json": str(output_path), "records": len(outputs)}, indent=2))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
