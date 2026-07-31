"""
Dynamic Selective Prompt Builder for DFM Taxonomy V3.

Injects ONLY the features and attributes of the schema that match keywords
in the rule text, and ONLY the context definitions and examples relevant
to the classified bucket type. Cuts tokens down significantly.
"""
from __future__ import annotations

import logging
from typing import Dict, List

from dfm_rule_pipeline.taxonomy.bucket_registry import BUCKET_REGISTRY
from dfm_rule_pipeline.taxonomy.schema_registry import SchemaRegistry

logger = logging.getLogger("taxonomy.prompt_context")

SYSTEM_EXTRACTOR_INSTRUCTIONS = """You are an expert CAD/DFM engineering rule formalization model.
Your task is to take a natural-language DFM rule and map its components to the provided domain schema and bucket.
Output a FLAT JSON matching the following schema. Never invent feature names or attributes that are not in the schema.

FLAT EXTRACTION TARGET SCHEMA (JSON format only):
{
  "domain": "Canonical domain name",
  "bucket": "Classified bucket type",
  "name": "Concise semantic name summarizing the rule",
  "rule_type": "Feature" or "Module",
  "feature1": "The main feature class being checked (e.g. SimpleHole, Bend, pocket, Distance)",
  "feature2": "Secondary feature class, or empty",
  "object1": "For Distance features, the first entity name. Otherwise empty.",
  "object2": "For Distance features, the second entity name. Otherwise empty.",
  "validations": [
    {
      "exp_name": "Variable path (e.g. Pocket.SideFaceAngle or Hole.Diameter)",
      "operators": ["Comparison operator, e.g. >=, <=, =, ANY"],
      "values": ["Numeric string, RGB value, or formula e.g. 4.5*SheetMetal.Thickness"]
    }
  ],
  "conditions": [
    {
      "exp_name": "Dotted path of the branching parameter (e.g. Hole.IsBlind or Pin.TotalHeight)",
      "operators": ["Comparison operators, e.g. = for boolean/category, or >=, <= for range"],
      "branches": [["Yes"], ["No"]]
    }
  ],
  "filters": [
    {
      "exp_name": "Applicability filter variable (e.g. Fastener.FirstEngagedComp.Material)",
      "operator": "=",
      "value": "Steel"
    }
  ],
  "additional": ["Report-only ExpName string, e.g. Hole.DiameterAtBot"],
  "allowed_params": ["Schema variables referenced in the validations value formula"]
}

STRICT COMPLIANCE RULES:
1. Object Names: Map to the exact schema object name provided in the SCHEMA.
2. Attributes: Map to the exact attributes in the SCHEMA.
3. Boolean Fields: Check attributes ending in '.Is...'. Use ONLY 'Yes' or 'No' values.
4. Values: Strip all unit words (mm, degrees, times, etc.).
5. Slash Ratio Notation vs Algebraic Math:
   - Use Slash Ratio Notation (e.g. `Hole.TotalDepth/Hole.DiameterAtTop` with value `["2.0"]`) ONLY when the rule text explicitly uses the word "ratio" or "aspect ratio" (e.g. "ratio of depth to diameter").
   - Use Algebraic Math (e.g. `exp_name: "Pocket.Depth"`, `operators: ["<="]`, `values: ["3*Pocket.MinBotRadius"]`, `allowed_params: ["Pocket.MinBotRadius"]`) when a rule compares an attribute against N times another variable (e.g. "depth must not exceed 3 times internal corner radius" or "min width at least 0.8 times sheet thickness"). Do NOT output slash notation unless the word "ratio" is explicitly present.
6. Range Operator & Range Values (Conditions AND Validations): For ANY range expression like 'between X and Y', 'X to Y', 'from X to Y', or 'X - Y', ALWAYS use TWO operators `[">=", "<="]` and provide BOTH numerical boundary values `["X", "Y"]`. This applies equally to conditions and validations. Example: "diagonal length 0.0 to 25.4" -> operators: [">=", "<="], values/branch: ["0.0", "25.4"]. NEVER use a single operator like ["<="] with only the upper bound. NEVER omit the lower bound of a range.
7. Set Membership: For list-based rules, use operator ['ANY'] and values [item1, item2].
8. RuleType: Use 'Module' when the rule targets model-level / module-level objects (PartBody, PartFace, PartEdge, ModuleParams, SheetMetal, etc.). Use 'Feature' when the rule targets geometry features (Hole, Bend, Pocket, etc.).
9. Feature1/Feature2: When rule_type is 'Module', set feature1 and feature2 to empty strings "". When rule_type is 'Feature', set feature1 to the primary geometry feature name.
10. Algebraic Formulas: Use algebraic math (e.g. '4.5*SheetMetal.Thickness') ONLY when comparing a single attribute against a formula of another variable. Put referenced variables in 'allowed_params'. Do NOT write ratios as algebraic math.
11. Multi-Branch & Multi-Condition Rules: For rules specifying different validation target values across multiple condition intervals (e.g., '0.0508 for 0.0 to 25.4, 0.1016 for 25.4 to 152.4, and 0.1524 for 152.4 to 2540.0'):
    - In `conditions`: Include the condition parameter (e.g. `PartBody.DiagonalLength`) with operators `[">=", "<="]` and put each interval as a separate branch in `branches` with BOTH lower and upper bounds (e.g., `branches: [["0.0", "25.4"], ["25.4", "152.4"], ["152.4", "2540.0"]]`). CRITICAL: Every branch MUST contain exactly 2 values — the lower bound AND the upper bound. Never omit the lower bound.
    - In `validations`: Include a SINGLE validation item where the `values` array contains one target value corresponding to each condition branch (e.g., `values: ["0.0508", "0.1016", "0.1524"]`). Do NOT create separate validation items for each branch.
12. Schema Path Accuracy (MANDATORY): Every `exp_name` MUST use the full dotted `Object.Attribute` path. NEVER output a bare attribute name without its object prefix. Examples: `PartBody.DiagonalLength`, `PartBody.LineProfileTolerance`, `PMI.ProfileOfSurface`, `Hole.PositionTolerance`. If you are unsure which object owns the attribute, use `PartBody` for module-level rules or the feature name (e.g. `Hole`, `Bend`) for feature-level rules.
13. Additional Field Strictness: `additional` MUST contain ONLY valid schema ExpName paths (e.g. `Hole.DiameterAtBot`). NEVER output raw rule text, equations, formulas, or assignments inside `additional`. All conditions MUST be extracted into `conditions` and all target values into `validations`.
14. Attribute Ownership & Disambiguation (MANDATORY): Always match the attribute to the EXACT Feature in the SCHEMA that owns it. Do NOT map attributes to a feature that does not list them in the SCHEMA. Examples:
    - `EntryAngle` and `ExitAngle` belong ONLY to `Hole` (`Hole.EntryAngle`, `Hole.ExitAngle`). NEVER map them to `HoleSegment` or `TaperAngle`.
    - `TaperAngle` belongs to `HoleSegment` (`HoleSegment.TaperAngle`).
    - `TotalDepth` belongs to `Hole` (`Hole.TotalDepth`).
    - `TipAngle` belongs to `Hole` (`Hole.TipAngle`).
"""


class PromptContextBuilder:
    """
    Constructs highly optimized selective prompts for DFM rule extraction.
    """

    def __init__(self, schema_registry: SchemaRegistry):
        self._registry = schema_registry

    def build_prompt(self, rule_text: str, domain: str, bucket: str) -> str:
        """
        Builds a custom prompt containing:
        1. General extractor instructions.
        2. Keyword-filtered schema context for the domain.
        3. Specific guidance and examples for the classified bucket.
        """
        # 1. Filter Schema
        filtered_schema = self._registry.filter_schema_for_rule(domain, rule_text)
        schema_block = self._registry.format_filtered_schema(filtered_schema)

        # 2. Get Bucket Context
        bucket_def = BUCKET_REGISTRY.get(bucket)
        if bucket_def:
            bucket_desc = f"Bucket ID: {bucket_def.bucket_id}\nDescription: {bucket_def.description}"
            # Select 1 example from exemplars as few-shot
            ex_sentence = bucket_def.exemplars[0] if bucket_def.exemplars else "None"
            bucket_context = f"{bucket_desc}\nExample of this bucket:\n  Rule: \"{ex_sentence}\""
        else:
            bucket_context = f"Bucket ID: {bucket}\nExtract the rule structure matching this bucket type."

        # 3. Assemble prompt
        prompt = f"""{SYSTEM_EXTRACTOR_INSTRUCTIONS}

----------------------------------------------------------------------
TARGET DOMAIN: {domain}
TARGET BUCKET: {bucket}

STRICT SCHEMA CONTEXT:
{schema_block}

BUCKET GUIDANCE:
{bucket_context}

----------------------------------------------------------------------
RULE TEXT TO PROCESS:
"{rule_text}"

Extract the parameters and output the FLAT JSON. Do NOT wrap the response in markdown code blocks (e.g. do NOT use ```json ... ```). Return ONLY the raw JSON string starting with {{ and ending with }}:
"""
        return prompt
