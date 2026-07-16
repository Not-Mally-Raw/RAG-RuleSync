"""Audit v3 JSON examples from the BucketList workbook."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_taxonomy_examples import infer_bucket, final_schema_rule
from dfm_rule_pipeline.taxonomy.canonicalizer import canonicalize_envelope_payload
from dfm_rule_pipeline.taxonomy.models import model_dump_compat
from dfm_rule_pipeline.taxonomy.schema_factory import normalize_envelope_payload
from dfm_rule_pipeline.taxonomy.validator import TaxonomyValidator


DEFAULT_WORKBOOK_PATH = Path(r"C:\Users\patle\Downloads\HCL\BucketList Examples (2) (1).xlsx")


def load_workbook_rows(workbook_path: Path) -> List[Dict[str, Any]]:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("pandas is required to read the BucketList workbook") from exc

    frame = pd.read_excel(workbook_path, sheet_name=0).fillna("")
    return frame.to_dict(orient="records")


def extract_examples(workbook_path: Path) -> Tuple[List[Tuple[int, str, str, Dict[str, Any]]], List[Tuple[int, str]]]:
    examples: List[Tuple[int, str, str, Dict[str, Any]]] = []
    parse_failures: List[Tuple[int, str]] = []
    for row_index, row in enumerate(load_workbook_rows(workbook_path), start=2):
        raw_json = str(row.get("Json Format", "") or "").strip()
        if not raw_json:
            continue
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            parse_failures.append((row_index, str(exc)))
            continue
        if final_schema_rule(payload):
            examples.append(
                (
                    row_index,
                    str(row.get("Buckets", "") or ""),
                    str(row.get("Rule Examples", "") or ""),
                    payload,
                )
            )
    return examples, parse_failures


def validate_example(row_index: int, bucket_label: str, rule_text: str, rule: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    domain = rule.get("RuleCategory", "")
    bucket = infer_bucket(rule)
    normalized = normalize_envelope_payload(rule, fallback_domain=domain, fallback_bucket=bucket)
    canonical = canonicalize_envelope_payload(normalized, rule_text or bucket_label)
    _, errors = TaxonomyValidator().validate(canonical)
    return [model_dump_compat(error) for error in errors], canonical


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook_path", nargs="?", default=str(DEFAULT_WORKBOOK_PATH))
    parser.add_argument("--show", type=int, default=25)
    args = parser.parse_args()

    examples, parse_failures = extract_examples(Path(args.workbook_path))
    failures = []
    for row_index, bucket_label, rule_text, rule in examples:
        errors, canonical = validate_example(row_index, bucket_label, rule_text, rule)
        if errors:
            failures.append(
                {
                    "row": row_index,
                    "bucket_label": bucket_label,
                    "rule_text": rule_text,
                    "domain": rule.get("RuleCategory", ""),
                    "bucket": canonical.get("bucket", ""),
                    "errors": errors,
                }
            )

    print(
        json.dumps(
            {
                "workbook_path": str(Path(args.workbook_path)),
                "examples": len(examples),
                "parse_failures": len(parse_failures),
                "validation_failures": len(failures),
            },
            indent=2,
        )
    )
    for failure in failures[: args.show]:
        print(json.dumps(failure, indent=2))
    return 1 if failures or parse_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
