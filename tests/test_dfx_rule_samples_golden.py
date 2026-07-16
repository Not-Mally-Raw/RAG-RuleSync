import os
from pathlib import Path

import pytest

from scripts.audit_dfx_rule_samples import DEFAULT_SAMPLES_PATH, extract_samples, validate_sample


def _samples_path() -> Path:
    return Path(os.environ.get("DFX_RULE_SAMPLES_PATH", str(DEFAULT_SAMPLES_PATH)))


def test_dfx_rule_samples_contains_all_89_rules():
    samples_path = _samples_path()
    if not samples_path.exists():
        pytest.skip(f"DFX rule samples file not found: {samples_path}")

    samples = extract_samples(samples_path)

    assert [sample["id"] for sample in samples] == list(range(1, 90))


def test_dfx_rule_samples_validate_against_taxonomy_v3():
    samples_path = _samples_path()
    if not samples_path.exists():
        pytest.skip(f"DFX rule samples file not found: {samples_path}")

    failures = []
    for sample in extract_samples(samples_path):
        errors, canonical = validate_sample(sample)
        if errors:
            failures.append(
                {
                    "id": sample["id"],
                    "rule_text": sample["rule_text"],
                    "domain": sample["legacy_rule"].get("RuleCategory", ""),
                    "bucket": canonical.get("bucket", ""),
                    "errors": errors,
                }
            )

    assert not failures, failures[:20]
