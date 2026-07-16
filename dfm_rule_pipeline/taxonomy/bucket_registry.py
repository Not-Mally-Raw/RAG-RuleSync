import re
from typing import Dict, List

from .knowledge import STRUCTURAL_TYPE_TO_BUCKET


BUCKETS: Dict[str, Dict[str, str]] = {
    "FeatureSimpleValidation": {
        "meaning": "One feature and one pass/fail expression.",
        "placement": "ValidationParamList",
    },
    "FeatureRangeValidation": {
        "meaning": "One feature with lower and upper bounds.",
        "placement": "ValidationParamList.Operator = [[range ops]]",
    },
    "FeatureSetMembership": {
        "meaning": "One field must be one of a set of allowed values.",
        "placement": "ValidationParamList.Operator = [[ANY]]",
    },
    "FeatureBooleanValidation": {
        "meaning": "Yes/no or true/false state.",
        "placement": "ValidationParamList",
    },
    "FeatureTypedValueValidation": {
        "meaning": "Material, color, type, name, size, or string validation.",
        "placement": "ValidationParamList",
    },
    "FeatureAllowedParamExpression": {
        "meaning": "Validation value references another schema parameter.",
        "placement": "ValidationParamList.AllowedParams",
    },
    "FilteredValidation": {
        "meaning": "Applicability filter plus validation.",
        "placement": "FilterParamList and ValidationParamList",
    },
    "ConditionalValidation": {
        "meaning": "If/then branch table.",
        "placement": "ConditionParamList and branch-aligned ValidationParamList",
    },
    "AdditionalInfoValidation": {
        "meaning": "Validation plus report-only fields.",
        "placement": "AdditionalParamList",
    },
    "DistanceRule": {
        "meaning": "Distance between two objects.",
        "placement": "Feature1 = Distance, Object1, Object2",
    },
    "ModuleValidation": {
        "meaning": "Module or global rule with no feature instance.",
        "placement": "RuleType = Module",
    },
    "MultiExpressionValidation": {
        "meaning": "Multiple checks on the same feature or context.",
        "placement": "Multiple ValidationParamList entries",
    },
    "NestedConditionalValidation": {
        "meaning": "Multiple condition dimensions or branch tables.",
        "placement": "Multiple aligned ConditionParamList entries",
    },
    "MultiRuleDivergence": {
        "meaning": "One input contains independent rules.",
        "placement": "Multiple taxonomy_rules objects",
    },
}


TAXONOMY_STRUCTURAL_TYPES = STRUCTURAL_TYPE_TO_BUCKET


def bucket_ids() -> List[str]:
    return list(BUCKETS)


def is_supported_bucket(value: str) -> bool:
    return value in BUCKETS


def classify_bucket(rule_text: str) -> str:
    text = f" {rule_text.lower()} "

    if re.search(r"\bdistance\b", text) and re.search(r"\b(between|from|to|apart|spacing)\b", text):
        return "DistanceRule"

    if re.search(r"\b(additionally|also check|also report|report-only|record)\b", text):
        return "AdditionalInfoValidation"

    if re.search(r"\b(default|otherwise|respectively)\b", text) and len(re.findall(r"\bbetween\b|\bfrom\b.+?\bto\b", text)) >= 2:
        return "NestedConditionalValidation"

    if re.search(r"\bcheck if\b", text):
        if re.search(r"\b(material(?!\s+thickness)|colour|color|type|name|thread class|thread type|thread size|size)\b", text):
            return "FeatureTypedValueValidation"
        if re.search(r"\b(true|false|yes|no|present|absent|blind|threaded|flat bottom)\b", text):
            return "FeatureBooleanValidation"

    if re.search(r"\b(if|when|based on|depending on|otherwise|respectively)\b", text):
        if text.count(" if ") > 1 or re.search(r"\b(and|or)\b.*\b(if|when|based on)\b", text):
            return "NestedConditionalValidation"
        return "ConditionalValidation"

    if re.search(r"\bfor\b.+\bwith\b.+\bbetween\b.+\bshould\b.+\bbetween\b", text):
        return "ConditionalValidation"

    if re.search(r"\b(module|partbody|part body|turned parts?|print size|machinability)\b", text) and re.search(
        r"\b(ratio|material|colour|color|type|name|size|should|must|ensure|check|not exceed|exceed)\b",
        text,
    ):
        return "ModuleValidation"

    measured_terms = re.findall(
        r"\b(diameter|radius|height|length|width|depth|opening|thickness|angle|clearance|distance)\b",
        text,
    )
    comparison_terms = re.findall(
        r"\b(minimum|maximum|equal|greater|less|at least|not less|not more|should|shall|must)\b",
        text,
    )
    if len(set(measured_terms)) >= 2 and len(comparison_terms) >= 2 and re.search(r"[,;]|\bwith\b|\band\b", text):
        return "MultiExpressionValidation"

    if re.search(r"\b(entry and exit|minimum and maximum|min and max|min/max)\b", text):
        return "MultiExpressionValidation"

    if re.search(r"\bbetween\b.+\band\b", text) or re.search(r"\bfrom\b.+\bto\b", text):
        return "FeatureRangeValidation"

    if re.search(r"\b(one of|any of|in the list|from the list|following list|recommended sizes|allowed values)\b", text):
        return "FeatureSetMembership"

    if re.search(r"\b(for|where|with)\b.+\b(shall|should|must|needs to|has to)\b", text) or re.search(
        r"\bfor\b.+\b(engaging with|with specific|with steel|with an outer diameter|whose|having)\b",
        text,
    ):
        return "FilteredValidation"

    if re.search(r"\b(true|false|yes|no|present|absent|blind|threaded|flat bottom)\b", text):
        return "FeatureBooleanValidation"

    if re.search(r"\b(material(?!\s+thickness)|colour|color|type|name|thread class|thread type|thread size|size)\b", text):
        return "FeatureTypedValueValidation"

    if re.search(r"\b(times|ratio|multiple of|nominal thickness|sheet thickness|machinability|print size|part body)\b", text):
        if re.search(r"\b(part body|print size|machinability|material|turned parts?|outer diameter|min(?:imum)? outer diameter)\b", text):
            return "ModuleValidation"
        return "FeatureAllowedParamExpression"

    if text.count(" and ") >= 2 or re.search(r"\b(both|as well as)\b", text):
        return "MultiExpressionValidation"

    return "FeatureSimpleValidation"
