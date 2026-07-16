import os
from pathlib import Path

import pytest

from scripts.audit_bucketlist_examples import DEFAULT_WORKBOOK_PATH, extract_examples, validate_example


def _workbook_path() -> Path:
    return Path(os.environ.get("BUCKETLIST_EXAMPLES_PATH", str(DEFAULT_WORKBOOK_PATH)))


def test_bucketlist_workbook_examples_validate_against_taxonomy_v3():
    workbook_path = _workbook_path()
    if not workbook_path.exists():
        pytest.skip(f"BucketList examples workbook not found: {workbook_path}")

    try:
        examples, parse_failures = extract_examples(workbook_path)
    except RuntimeError as exc:
        pytest.skip(str(exc))

    failures = []
    for row_index, bucket_label, rule_text, rule in examples:
        errors, canonical = validate_example(row_index, bucket_label, rule_text, rule)
        if errors:
            failures.append(
                {
                    "row": row_index,
                    "bucket_label": bucket_label,
                    "domain": rule.get("RuleCategory", ""),
                    "bucket": canonical.get("bucket", ""),
                    "errors": errors,
                }
            )

    assert not parse_failures
    assert len(examples) >= 15
    assert not failures, failures[:20]
