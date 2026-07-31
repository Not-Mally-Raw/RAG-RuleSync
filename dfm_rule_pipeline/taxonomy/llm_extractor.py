"""
LLM Extractor for DFM Taxonomy V3.

Sends the dynamically built prompt to the LLM client, receives
the flat intermediate JSON, and validates it against Pydantic models.
"""
from __future__ import annotations

import json
import logging
from typing import Optional, TYPE_CHECKING

from dfm_rule_pipeline.taxonomy.models import ExtractionResult

if TYPE_CHECKING:
    from dfm_rule_pipeline.llm.client import LLMClient

logger = logging.getLogger("taxonomy.llm_extractor")


class LLMExtractor:
    """
    Handles calling the LLM client to perform flat extraction of DFM rules.
    """

    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def extract(self, prompt: str) -> Optional[ExtractionResult]:
        """
        Calls the LLM client using JSON mode and validates the response schema.
        
        Returns the parsed ExtractionResult model, or None if extraction failed.
        """
        try:
            # Groq call with JSON mode enabled
            raw_response = self._llm.call(prompt, json_mode=True)
            if not raw_response:
                logger.error("LLM returned empty response")
                return None
            
            # Parse raw response
            cleaned_response = raw_response.strip()
            
            # Pydantic validation
            try:
                extraction = ExtractionResult.model_validate_json(cleaned_response)
                return extraction
            except Exception as pe:
                logger.error(f"Pydantic validation failed for extraction: {pe}\nRaw output: {cleaned_response}")
                # Try soft parsing keys before giving up completely
                data = json.loads(cleaned_response)
                # Map potential simple lists/strings to correct structure
                extraction = self._soft_parse_recovery(data)
                return extraction

        except Exception as e:
            logger.error(f"LLM extraction request failed: {e}", exc_info=True)
            return None

    def _soft_parse_recovery(self, data: dict) -> Optional[ExtractionResult]:
        """Recovers from minor LLM key layout mismatches."""
        try:
            # Coerce validations
            validations = []
            for v in data.get("validations", []):
                if isinstance(v, dict):
                    # Ensure operator and values are lists
                    ops = v.get("operators", [])
                    if isinstance(ops, str):
                        ops = [ops]
                    vals = v.get("values", [])
                    if isinstance(vals, (str, int, float)):
                        vals = [str(vals)]
                    elif isinstance(vals, list):
                        vals = [str(item) for item in vals]
                    validations.append({
                        "exp_name": v.get("exp_name", ""),
                        "operators": ops,
                        "values": vals
                    })
            
            # Coerce conditions
            conditions = []
            for c in data.get("conditions", []):
                if isinstance(c, dict):
                    ops = c.get("operators", [])
                    if isinstance(ops, str):
                        ops = [ops]
                    branches = c.get("branches", [])
                    # Wrap single dimension branches into 2D list of list[str]
                    if isinstance(branches, list):
                        wrapped_branches = []
                        for b in branches:
                            if isinstance(b, list):
                                wrapped_branches.append([str(item) for item in b])
                            else:
                                wrapped_branches.append([str(b)])
                        branches = wrapped_branches
                    conditions.append({
                        "exp_name": c.get("exp_name", ""),
                        "operators": ops,
                        "branches": branches
                    })
            
            # Coerce filters
            filters = []
            for f in data.get("filters", []):
                if isinstance(f, dict):
                    filters.append({
                        "exp_name": f.get("exp_name", ""),
                        "operator": str(f.get("operator", "")),
                        "value": str(f.get("value", ""))
                    })

            recovered_data = {
                "domain": data.get("domain", "General"),
                "bucket": data.get("bucket", "SimpleValidation"),
                "name": data.get("name", "Unnamed Rule"),
                "rule_type": data.get("rule_type", "Feature"),
                "feature1": data.get("feature1", ""),
                "feature2": data.get("feature2", ""),
                "object1": data.get("object1", ""),
                "object2": data.get("object2", ""),
                "validations": validations,
                "conditions": conditions,
                "filters": filters,
                "additional": data.get("additional", []),
                "allowed_params": data.get("allowed_params", [])
            }
            return ExtractionResult.model_validate(recovered_data)
        except Exception as e:
            logger.error(f"Soft recovery failed: {e}")
            return None
