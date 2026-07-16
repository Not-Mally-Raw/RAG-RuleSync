"""Taxonomy v3 formalization package.

This package is intentionally additive. It supports the new
``/process-rules-taxonomy`` API path without changing the legacy
``/process-rules`` pipeline.
"""

from .service import TaxonomyFormalizationService

__all__ = ["TaxonomyFormalizationService"]
