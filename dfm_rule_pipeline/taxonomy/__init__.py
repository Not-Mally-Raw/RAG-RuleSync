"""
DFM Taxonomy V3 DFM Rule Formalization Pipeline Package.

Exposes models, validators, assemblers, classifiers, and the orchestrator service.
"""
from __future__ import annotations

from dfm_rule_pipeline.taxonomy.assembler import TaxonomyAssembler
from dfm_rule_pipeline.taxonomy.bucket_classifier import BucketClassifier, ClassificationResult
from dfm_rule_pipeline.taxonomy.bucket_registry import BUCKET_REGISTRY, BucketDefinition, get_bucket, list_buckets
from dfm_rule_pipeline.taxonomy.domain_normalizer import normalize_domain, is_valid_domain, list_domains
from dfm_rule_pipeline.taxonomy.models import (
    ExtractionResult,
    FlatValidation,
    FlatCondition,
    FlatFilter,
    TaxonomyRule,
    Constraints,
    FilterParam,
    ConditionParam,
    ValidationParam,
    AdditionalParam,
    UserParam,
    TaxonomyResponse,
    ValidationErrorDetail,
    RuleInput,
)
from dfm_rule_pipeline.taxonomy.schema_registry import SchemaRegistry
from dfm_rule_pipeline.taxonomy.service import TaxonomyFormalizationService
from dfm_rule_pipeline.taxonomy.validator import TaxonomyValidator

__all__ = [
    "TaxonomyFormalizationService",
    "SchemaRegistry",
    "TaxonomyAssembler",
    "TaxonomyValidator",
    "BucketClassifier",
    "ClassificationResult",
    "ExtractionResult",
    "FlatValidation",
    "FlatCondition",
    "FlatFilter",
    "TaxonomyRule",
    "Constraints",
    "FilterParam",
    "ConditionParam",
    "ValidationParam",
    "AdditionalParam",
    "UserParam",
    "TaxonomyResponse",
    "ValidationErrorDetail",
    "RuleInput",
    "BUCKET_REGISTRY",
    "BucketDefinition",
    "get_bucket",
    "list_buckets",
    "normalize_domain",
    "is_valid_domain",
    "list_domains",
]
