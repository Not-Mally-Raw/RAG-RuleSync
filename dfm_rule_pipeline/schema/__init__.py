"""
DFM Schema Definitions

Provides CAD domain definitions, feature schemas, and tolerance specifications
used for grounding LLM prompts in manufacturing domain constraints.
"""
from dfm_rule_pipeline.schema.feature_schema import features_dict, load_feature_schema
from dfm_rule_pipeline.schema.domain_definitions import DOMAIN_DEFINITIONS
from dfm_rule_pipeline.schema.tolerance_schema import TOLERANCE_TYPES, GDT_KEYWORDS

__all__ = [
    "features_dict",
    "load_feature_schema",
    "DOMAIN_DEFINITIONS",
    "TOLERANCE_TYPES",
    "GDT_KEYWORDS",
]
