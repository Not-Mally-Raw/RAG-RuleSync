import json
from typing import Dict

from dfm_rule_pipeline.schema.features import features_dict

from .bucket_registry import BUCKETS
from .domain_normalizer import schema_domain_key
from .knowledge import (
    DOMAIN_PROFILES,
    DOMAIN_SCHEMA_EXTENSIONS,
    PROMPT_EXAMPLES,
    STRUCTURAL_TYPE_TO_BUCKET,
    THICKNESS_VARIABLE_BY_DOMAIN,
)
from .schema_factory import final_schema_skeleton


def domain_schema_context(domain: str) -> str:
    schema_key = schema_domain_key(domain)
    base = features_dict.get(schema_key, "")
    extensions = DOMAIN_SCHEMA_EXTENSIONS.get(domain, {})
    if not extensions:
        return base
    extension_lines = ["", "Taxonomy schema extensions:"]
    for obj, attrs in extensions.items():
        extension_lines.append(f"Object: {obj}")
        extension_lines.append(f"Attributes: {', '.join(attrs)}")
    return base + "\n" + "\n".join(extension_lines)


def bucket_context(bucket: str) -> Dict[str, str]:
    return BUCKETS.get(bucket, {})


def taxonomy_guidance_context(domain: str, bucket: str) -> str:
    profile = DOMAIN_PROFILES.get(domain, {})
    guidance = {
        "domain_signals": {
            "primary": profile.get("primary", [])[:12],
            "secondary": profile.get("secondary", [])[:8],
        },
        "domain_thickness_variable": THICKNESS_VARIABLE_BY_DOMAIN.get(domain, ""),
        "structural_type_map": STRUCTURAL_TYPE_TO_BUCKET,
        "selected_bucket": bucket,
        "bucket_rule_type": "Module" if bucket == "ModuleValidation" else "Feature or Module depending on expression scope",
    }
    return json.dumps(guidance, indent=2)


def examples_context(domain: str, bucket: str) -> str:
    selected = [
        example
        for example in PROMPT_EXAMPLES
        if example["bucket"] == bucket or example["domain"] == domain
    ]
    if not selected:
        selected = [
            example
            for example in PROMPT_EXAMPLES
            if example["bucket"] in {"FeatureSimpleValidation", "FeatureAllowedParamExpression", "FilteredValidation"}
        ]
    same_bucket = [example for example in selected if example["bucket"] == bucket]
    same_domain = [example for example in selected if example["domain"] == domain and example not in same_bucket]
    examples = same_bucket[:3] + same_domain[:3]
    if len(examples) < 4:
        examples.extend(example for example in PROMPT_EXAMPLES if example not in examples)
    return json.dumps(examples[:6], indent=2)


def build_taxonomy_prompt(rule_text: str, domain: str, bucket: str) -> str:
    skeleton = json.dumps(final_schema_skeleton(), indent=2)
    bucket_info = json.dumps(bucket_context(bucket), indent=2)
    taxonomy_guidance = taxonomy_guidance_context(domain, bucket)
    examples = examples_context(domain, bucket)
    schema_context = domain_schema_context(domain)

    return f"""You convert one DFM rule into the Taxonomy V3 JSON schema.

Return JSON only. The first character must be {{ and the last character must be }}.
Do not use markdown, prose, apologies, analysis, or code fences.
Do not emit legacy flat fields such as Recom, ExpName1, Operator1, Value1, Operator2, Value2, or scalar between/in.

Expected top-level envelope:
{{
  "domain": "{domain}",
  "bucket": "{bucket}",
  "taxonomy_rules": []
}}

Rule text:
{rule_text}

Detected domain:
{domain}

Detected structural bucket:
{bucket}

Bucket guidance:
{bucket_info}

Compact taxonomy guidance:
{taxonomy_guidance}

Final rule skeleton. Every emitted taxonomy rule must contain these keys and unused lists must contain placeholder objects:
{skeleton}

Domain feature schema:
{schema_context}

Compact examples:
{examples}

Important mapping rules:
- Top-level taxonomy rule RuleType must be only "Feature" or "Module"; never put bucket IDs such as DistanceRule in RuleType.
- Results must be exactly "Validation". Never put equations, pass/fail labels, reasoning, or validation expressions in Results.
- Use RuleType "Module" for PartBody, PartFace, Turn.Body, Mill.Machinability, PrintSize, or other module-level expressions with no feature instance.
- JSON numbers must be emitted as strings in Value arrays, for example "4.5" not 4.5.
- Put applicability filters in FilterParamList.
- Put if/when branch variables in ConditionParamList.
- Put pass/fail checks in ValidationParamList.
- Put report-only fields in AdditionalParamList.
- Range rules use Operator [[">", "<"]] or inclusive variants with Value [[["lower", "upper"]]].
- Set membership rules use Operator [["ANY"]] with Value [[["A"], ["B"]]].
- If a validation value contains a schema reference formula, include that reference in AllowedParams.
- Distance rules must set Feature1 to "Distance" and fill Object1 and Object2.
- Module rules must set RuleType to "Module" and leave Feature1, Feature2, Object1, and Object2 empty.
- Multiple checks on the same feature belong as multiple ValidationParamList entries, not numbered fields.
- Split independent rules into multiple taxonomy_rules objects.
- Compact examples show shape only; never copy example objects, features, values, names, or paths unless they are present in the rule text or domain schema.
- Ground Object1, Object2, Feature1, and formula references in the source text. For example, do not use Bridge when the rule says slot/cutout/opening.
- For "directly proportional to A, B, C" without a stated coefficient, use a symbolic coefficient in UserParamList, such as ProportionalityConstant, instead of inventing a numeric constant.
"""


def build_repair_prompt(rule_text: str, invalid_json: object, errors: object, domain: str, bucket: str) -> str:
    skeleton = json.dumps(final_schema_skeleton(), indent=2)
    invalid_payload = json.dumps(invalid_json, indent=2)
    validation_errors = json.dumps(errors, indent=2)
    schema_context = domain_schema_context(domain)
    taxonomy_guidance = taxonomy_guidance_context(domain, bucket)

    return f"""Repair the Taxonomy V3 JSON for this DFM rule.

Return corrected JSON only. Do not use markdown. Preserve the intended rule meaning.

Rule text:
{rule_text}

Detected domain:
{domain}

Detected bucket:
{bucket}

Invalid JSON:
{invalid_payload}

Validation errors:
{validation_errors}

Required skeleton:
{skeleton}

Domain feature schema:
{schema_context}

Compact taxonomy guidance:
{taxonomy_guidance}

Repair rules:
- Return JSON only. The first character must be {{ and the last character must be }}.
- If the invalid JSON is plain text or contains no JSON, ignore it and generate a fresh valid envelope.
- Remove legacy flat fields such as Recom, ExpName1, Operator1, Value1, Operator2, and Value2.
- Top-level taxonomy rule RuleType must be only "Feature" or "Module"; never put bucket IDs such as DistanceRule in RuleType.
- Results must be exactly "Validation"; move equations to ValidationParamList.
- JSON numbers must be emitted as strings in Value arrays, for example "4.5" not 4.5.
- Use exact nested Operator and Value shapes from the skeleton.
- Keep condition branch counts aligned with validation value branches.
- Use valid schema paths only.
- Include AllowedParams for formula references inside validation values.
- If an object or formula reference is not grounded in the source text, replace it with the object actually named in the rule or a valid taxonomy alias.
"""


def build_json_recovery_prompt(rule_text: str, raw_response: str, errors: object, domain: str, bucket: str) -> str:
    skeleton = json.dumps(final_schema_skeleton(), indent=2)
    validation_errors = json.dumps(errors, indent=2)
    schema_context = domain_schema_context(domain)
    taxonomy_guidance = taxonomy_guidance_context(domain, bucket)

    return f"""Your previous answer was not valid JSON. Generate a fresh Taxonomy V3 JSON object now.

Return JSON only. The first character must be {{ and the last character must be }}.
Do not use markdown, code fences, explanations, apologies, or comments.

Required envelope:
{{
  "domain": "{domain}",
  "bucket": "{bucket}",
  "taxonomy_rules": []
}}

Rule text:
{rule_text}

Previous invalid response:
{raw_response}

Validation errors:
{validation_errors}

Final rule skeleton:
{skeleton}

Domain feature schema:
{schema_context}

Compact taxonomy guidance:
{taxonomy_guidance}

Rules:
- Every taxonomy rule must use the skeleton keys exactly.
- RuleType must be only "Feature" or "Module".
- Results must be exactly "Validation".
- Bucket names such as "{bucket}" stay only in the envelope bucket field.
- Values must be strings, including numbers such as "4.5".
- Unused constraint lists must contain the placeholder object from the skeleton.
- Use only valid domain schema paths.
- Compact examples are pattern references only; do not copy their object names unless the rule text uses them.
"""
