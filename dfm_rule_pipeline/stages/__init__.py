"""
DFM Rule Pipeline - Version 2 (Legacy / Compatibility Formalization Stages)

This subpackage contains the classic 4-stage rule formalization pipeline:
- Stage 1: Intent extraction (extract_intent)
- Stage 2: Category & domain resolution (resolve_rule_category_and_domain)
- Stage 2b: Geometry resolution (resolve_geometry)
- Stage 2c: Tolerance resolution (resolve_tolerance)
- Stage 3: Attribute formalization (formalize_attribute_rule, formalize_rule)
- Stage 4: Self-validation (self_validate)

These stages are preserved for backward compatibility and power the
`/process-rules` endpoint in app.py.

For the latest V3 taxonomy formalization (format1.json BucketList), see
`dfm_rule_pipeline.taxonomy`.
"""
from dfm_rule_pipeline.stages.stage1_intent_extraction import extract_intent
from dfm_rule_pipeline.stages.stage2_rule_resolution import resolve_rule_category_and_domain
from dfm_rule_pipeline.stages.stage2b_geometry_resolution import resolve_geometry
from dfm_rule_pipeline.stages.stage2c_tolerance_spec import resolve_tolerance
from dfm_rule_pipeline.stages.stage3_attribute_formalization import formalize_attribute_rule
from dfm_rule_pipeline.stages.stage3_formalization import formalize_rule
from dfm_rule_pipeline.stages.stage4_self_validation import self_validate

__all__ = [
    "extract_intent",
    "resolve_rule_category_and_domain",
    "resolve_geometry",
    "resolve_tolerance",
    "formalize_attribute_rule",
    "formalize_rule",
    "self_validate",
]
