import os
from pathlib import Path

import pytest

from scripts.audit_taxonomy_examples import DEFAULT_TAXONOMY_PATH, extract_examples, validate_example


def _taxonomy_path() -> Path:
    return Path(os.environ.get("TAXONOMY_MD_PATH", str(DEFAULT_TAXONOMY_PATH)))


def test_taxonomy_markdown_has_golden_example_coverage():
    taxonomy_path = _taxonomy_path()
    if not taxonomy_path.exists():
        pytest.skip(f"taxonomy markdown not found: {taxonomy_path}")

    examples, parse_failures = extract_examples(taxonomy_path)

    assert not parse_failures
    # The full numbered corpus lives in DFXRuleSamples.md and is covered by
    # test_dfx_rule_samples_contains_all_89_rules. The taxonomy markdown keeps
    # selected worked final-schema JSON examples.
    assert len(examples) >= 28


def test_taxonomy_markdown_golden_examples_validate():
    taxonomy_path = _taxonomy_path()
    if not taxonomy_path.exists():
        pytest.skip(f"taxonomy markdown not found: {taxonomy_path}")

    examples, _ = extract_examples(taxonomy_path)
    failures = []
    for block_index, rule in examples:
        errors, canonical = validate_example(block_index, rule)
        if errors:
            failures.append(
                {
                    "block": block_index,
                    "name": rule.get("Name", ""),
                    "domain": rule.get("RuleCategory", ""),
                    "bucket": canonical.get("bucket", ""),
                    "errors": errors,
                }
            )

    assert not failures, failures[:20]
