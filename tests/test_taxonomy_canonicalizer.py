from dfm_rule_pipeline.taxonomy.bucket_registry import classify_bucket
from dfm_rule_pipeline.taxonomy.canonicalizer import canonicalize_envelope_payload
from dfm_rule_pipeline.taxonomy.schema_factory import normalize_envelope_payload
from dfm_rule_pipeline.taxonomy.validator import TaxonomyValidator


def _canonicalize(rule_text, payload, domain, bucket):
    normalized = normalize_envelope_payload(payload, fallback_domain=domain, fallback_bucket=bucket)
    canonical = canonicalize_envelope_payload(normalized, rule_text)
    envelope, errors = TaxonomyValidator().validate(canonical)
    assert errors == []
    assert envelope is not None
    return envelope.taxonomy_rules[0]


def test_sheetmetal_forming_distance_ratio_uses_canonical_formula_placement():
    rule = _canonicalize(
        "generic rule text is not used by canonicalizer",
        {
            "domain": "Sheetmetal Forming",
            "bucket": "DistanceRule",
            "taxonomy_rules": [
                {
                    "Name": "LLM supplied name",
                    "RuleCategory": "Sheetmetal Forming",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "Distance",
                    "Object1": "SimpleHole",
                    "Object2": "SMFace",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Distance.MinValue/ModuleParams.NormalThickness",
                                "Operator": [[">="]],
                                "Value": [[["2.0"]]],
                                "AllowedParams": ["ModuleParams.NormalThickness"],
                            }
                        ]
                    },
                }
            ],
        },
        "Sheetmetal Forming",
        "DistanceRule",
    )

    validation = rule.Constraints.ValidationParamList[0]
    assert rule.Name == "LLM supplied name"
    assert rule.Object1 == "SimpleHole"
    assert rule.Object2 == "Part Edge"
    assert validation.ExpName == "Distance.MinValue"
    assert validation.Value == [[["2.0*SheetMetalForm.NominalThickness"]]]
    assert validation.AllowedParams == ["SheetMetalForm.NominalThickness"]


def test_turning_length_to_min_outer_diameter_alias_becomes_module_expression():
    rule = _canonicalize(
        "generic rule text is not used by canonicalizer",
        {
            "domain": "Turning",
            "bucket": "FeatureAllowedParamExpression",
            "taxonomy_rules": [
                {
                    "Name": "Length to MinOuterDiameter Ratio",
                    "RuleCategory": "Turning",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "Body",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "LengthToMinOuterDiameterRatio",
                                "Operator": [["<="]],
                                "Value": [[["8.0"]]],
                                "AllowedParams": ["Body.Length / Body.MinOuterDiameter"],
                            }
                        ]
                    },
                }
            ],
        },
        "Turning",
        "FeatureAllowedParamExpression",
    )

    validation = rule.Constraints.ValidationParamList[0]
    assert rule.Name == "Length to MinOuterDiameter Ratio"
    assert rule.RuleType == "Module"
    assert rule.Feature1 == ""
    assert validation.ExpName == "Turn.Body.Length/Turn.Body.MinOuterDiameter"
    assert validation.Value == [[["8.0"]]]
    assert validation.AllowedParams == [""]
    assert classify_bucket("Ensure that the ratio of the length to the minimum outer diameter of turned parts does not exceed 8.0.") == "ModuleValidation"


def test_sheetmetal_material_alias_becomes_module_partbody_material():
    rule = _canonicalize(
        "generic rule text is not used by canonicalizer",
        {
            "domain": "SheetMetal",
            "bucket": "FeatureSetMembership",
            "taxonomy_rules": [
                {
                    "Name": "Partbody material must be Steel or Aluminium",
                    "RuleCategory": "SheetMetal",
                    "Results": "Validation",
                    "RuleType": "Module",
                    "Constraints": {
                        "FilterParamList": [
                            {"ExpName": "ModuleParams.IsSheetMetalPart", "Operator": ["="], "Value": ["true"]}
                        ],
                        "ValidationParamList": [
                            {
                                "ExpName": "Material",
                                "Operator": [["ANY"]],
                                "Value": [[["Steel"], ["Aluminium"]]],
                                "AllowedParams": [""],
                            }
                        ],
                    },
                }
            ],
        },
        "SheetMetal",
        "FeatureSetMembership",
    )

    validation = rule.Constraints.ValidationParamList[0]
    assert rule.Name == "Partbody material must be Steel or Aluminium"
    assert rule.RuleType == "Module"
    assert rule.Constraints.FilterParamList[0].ExpName == ""
    assert validation.ExpName == "PartBody.Material"
    assert validation.Operator == [["ANY"]]
    assert validation.Value == [[["Steel"], ["Aluminium"]]]
    assert validation.AllowedParams == [""]


def test_any_values_are_normalized_without_exact_rule_text_matching():
    rule = _canonicalize(
        "generic set-membership rule",
        {
            "domain": "General",
            "bucket": "FeatureSetMembership",
            "taxonomy_rules": [
                {
                    "Name": "Allowed materials",
                    "RuleCategory": "General",
                    "Results": "Validation",
                    "RuleType": "Module",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Material",
                                "Operator": [["in"]],
                                "Value": [[["Steel", "Aluminium"]]],
                                "AllowedParams": [""],
                            }
                        ]
                    },
                }
            ],
        },
        "General",
        "FeatureSetMembership",
    )

    validation = rule.Constraints.ValidationParamList[0]
    assert rule.RuleType == "Module"
    assert validation.ExpName == "PartBody.Material"
    assert validation.Operator == [["ANY"]]
    assert validation.Value == [[["Steel"], ["Aluminium"]]]


def test_formula_values_add_allowed_params_generically():
    rule = _canonicalize(
        "generic formula rule",
        {
            "domain": "SheetMetal",
            "bucket": "FeatureAllowedParamExpression",
            "taxonomy_rules": [
                {
                    "Name": "Spoon width",
                    "RuleCategory": "SheetMetal",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "Spoon",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Spoon.Width",
                                "Operator": [[">="]],
                                "Value": [[["0.8*ModuleParams.Thickness"]]],
                                "AllowedParams": [""],
                            }
                        ]
                    },
                }
            ],
        },
        "SheetMetal",
        "FeatureAllowedParamExpression",
    )

    validation = rule.Constraints.ValidationParamList[0]
    assert validation.ExpName == "Spoon.Width"
    assert validation.Value == [[["0.8*SheetMetal.Thickness"]]]
    assert validation.AllowedParams == ["SheetMetal.Thickness"]


def test_module_color_alias_uses_partface_color():
    rule = _canonicalize(
        "generic color rule",
        {
            "domain": "Drilling",
            "bucket": "ModuleValidation",
            "taxonomy_rules": [
                {
                    "Name": "Part color",
                    "RuleCategory": "Drilling",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "Hole",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Colour",
                                "Operator": [["="]],
                                "Value": [[["Blue"]]],
                                "AllowedParams": [""],
                            }
                        ]
                    },
                }
            ],
        },
        "Drilling",
        "ModuleValidation",
    )

    validation = rule.Constraints.ValidationParamList[0]
    assert rule.RuleType == "Module"
    assert rule.Feature1 == ""
    assert validation.ExpName == "PartFace.Color"


def test_user_param_symbol_alias_is_replaced_with_param_name():
    rule = _canonicalize(
        "generic proportional formula rule",
        {
            "domain": "SheetMetal",
            "bucket": "DistanceRule",
            "taxonomy_rules": [
                {
                    "Name": "Bend to slot distance",
                    "RuleCategory": "SheetMetal",
                    "Results": "Distance.MinValue >= k * Slot.Length * SheetMetal.Thickness * Bend.MinRadius",
                    "RuleType": "Feature",
                    "Feature1": "Distance",
                    "Object1": "Bend",
                    "Object2": "Slot",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Distance.MinValue",
                                "Operator": [[">="]],
                                "Value": [[["k*Slot.Length*SheetMetal.Thickness*Bend.MinRadius"]]],
                                "AllowedParams": ["Slot.Length", "SheetMetal.Thickness", "Bend.MinRadius"],
                            }
                        ],
                        "UserParamList": [
                            {
                                "ParamName": "ProportionalityConstant",
                                "DisplayName": "Proportionality Constant",
                                "Value": ["k"],
                                "MinValue": "0",
                                "MaxValue": "",
                            }
                        ],
                    },
                }
            ],
        },
        "SheetMetal",
        "DistanceRule",
    )

    validation = rule.Constraints.ValidationParamList[0]
    user_param = rule.Constraints.UserParamList[0]
    assert rule.Results == "Validation"
    assert validation.Value == [[["ProportionalityConstant*Slot.Length*SheetMetal.Thickness*Bend.MinRadius"]]]
    assert user_param.ParamName == "ProportionalityConstant"
    assert user_param.Value == [""]
