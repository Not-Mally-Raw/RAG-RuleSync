from dfm_rule_pipeline.taxonomy.schema_factory import normalize_envelope_payload
from dfm_rule_pipeline.taxonomy.validator import TaxonomyValidator
from dfm_rule_pipeline.taxonomy.grounding import validate_grounding


def _validate(raw_payload, domain="SheetMetal", bucket="DistanceRule"):
    payload = normalize_envelope_payload(raw_payload, fallback_domain=domain, fallback_bucket=bucket)
    return TaxonomyValidator().validate(payload)


def test_validator_accepts_bridge_distance_rule():
    envelope, errors = _validate(
        {
            "domain": "SheetMetal",
            "bucket": "DistanceRule",
            "taxonomy_rules": [
                {
                    "Name": "Bridge Spacing",
                    "RuleCategory": "SheetMetal",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "Distance",
                    "Object1": "Bridge",
                    "Object2": "Bridge",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Distance.MinValue/SheetMetal.Thickness",
                                "Operator": [[">="]],
                                "Value": [[["4.5"]]],
                                "AllowedParams": [""],
                            }
                        ]
                    },
                }
            ],
        }
    )

    assert envelope is not None
    assert errors == []


def test_validator_coerces_numeric_validation_values_to_strings():
    envelope, errors = _validate(
        {
            "domain": "SheetMetal",
            "bucket": "DistanceRule",
            "taxonomy_rules": [
                {
                    "Name": "Bridge Spacing",
                    "RuleCategory": "SheetMetal",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "Distance",
                    "Object1": "Bridge",
                    "Object2": "Bridge",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Distance.MinValue/SheetMetal.Thickness",
                                "Operator": [[">="]],
                                "Value": [[[4.5]]],
                                "AllowedParams": [""],
                            }
                        ]
                    },
                }
            ],
        }
    )

    assert errors == []
    assert envelope.taxonomy_rules[0].Constraints.ValidationParamList[0].Value == [[["4.5"]]]


def test_validator_rejects_legacy_flat_fields():
    _, errors = _validate(
        {
            "domain": "SheetMetal",
            "bucket": "DistanceRule",
            "taxonomy_rules": [
                {
                    "Name": "Bad legacy",
                    "RuleCategory": "SheetMetal",
                    "RuleType": "Feature",
                    "Feature1": "Distance",
                    "Object1": "Bridge",
                    "Object2": "Bridge",
                    "Recom": "Distance.MinValue >= 4.5",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Distance.MinValue",
                                "Operator": [[">="]],
                                "Value": [[["4.5"]]],
                                "AllowedParams": [""],
                            }
                        ]
                    },
                }
            ],
        }
    )

    assert "legacy_field_detected" in {error.code for error in errors}


def test_validator_rejects_invalid_schema_attribute_for_domain():
    _, errors = _validate(
        {
            "domain": "Drilling",
            "bucket": "FeatureSimpleValidation",
            "taxonomy_rules": [
                {
                    "Name": "Molded hole depth ratio",
                    "RuleCategory": "Drilling",
                    "RuleType": "Feature",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
                                "Operator": [[">="]],
                                "Value": [[["2.0"]]],
                                "AllowedParams": [""],
                            }
                        ]
                    },
                }
            ],
        },
        domain="Drilling",
        bucket="FeatureSimpleValidation",
    )

    assert "schema_attribute_failed" in {error.code for error in errors}


def test_validator_rejects_condition_branch_mismatch():
    _, errors = _validate(
        {
            "domain": "Injection Molding",
            "bucket": "ConditionalValidation",
            "taxonomy_rules": [
                {
                    "Name": "Blind and through depth",
                    "RuleCategory": "Injection Molding",
                    "RuleType": "Feature",
                    "Constraints": {
                        "ConditionParamList": [
                            {
                                "ExpName": "Hole.IsBlind",
                                "Operator": [["="]],
                                "Value": [[["Yes"]], [["No"]]],
                            }
                        ],
                        "ValidationParamList": [
                            {
                                "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
                                "Operator": [["="]],
                                "Value": [[["2.0"]]],
                                "AllowedParams": [""],
                            }
                        ],
                    },
                }
            ],
        },
        domain="Injection Molding",
        bucket="ConditionalValidation",
    )

    assert "branch_alignment_failed" in {error.code for error in errors}


def test_validator_requires_allowed_params_for_formula_values():
    _, errors = _validate(
        {
            "domain": "Sheetmetal Forming",
            "bucket": "DistanceRule",
            "taxonomy_rules": [
                {
                    "Name": "Forming spacing",
                    "RuleCategory": "Sheetmetal Forming",
                    "RuleType": "Feature",
                    "Feature1": "Distance",
                    "Object1": "SimpleHole",
                    "Object2": "Bend",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Distance.MinValue",
                                "Operator": [[">="]],
                                "Value": [[["2.0*SheetMetalForm.NominalThickness"]]],
                                "AllowedParams": [""],
                            }
                        ]
                    },
                }
            ],
        },
        domain="Sheetmetal Forming",
        bucket="DistanceRule",
    )

    assert "allowed_params_missing" in {error.code for error in errors}


def test_validator_accepts_partbody_nominal_thickness_module_expression():
    envelope, errors = _validate(
        {
            "domain": "Die Casting",
            "bucket": "ModuleValidation",
            "taxonomy_rules": [
                {
                    "Name": "Nominal thickness",
                    "RuleCategory": "Die Casting",
                    "RuleType": "Module",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "PartBody.NominalThickness",
                                "Operator": [[">="]],
                                "Value": [[["2.0"]]],
                                "AllowedParams": [""],
                            }
                        ]
                    },
                }
            ],
        },
        domain="Die Casting",
        bucket="ModuleValidation",
    )

    assert envelope is not None
    assert errors == []


def test_validator_rejects_expression_in_results_field_without_normalization():
    _, errors = TaxonomyValidator().validate(
        {
            "domain": "SheetMetal",
            "bucket": "DistanceRule",
            "taxonomy_rules": [
                {
                    "Name": "Bend distance",
                    "RuleCategory": "SheetMetal",
                    "Results": "Distance.MinValue >= k*Slot.Length",
                    "RuleType": "Feature",
                    "Feature1": "Distance",
                    "Object1": "Bend",
                    "Object2": "Slot",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Distance.MinValue",
                                "Operator": [[">="]],
                                "Value": [[["ProportionalityConstant*Slot.Length"]]],
                                "AllowedParams": ["Slot.Length"],
                            }
                        ]
                    },
                }
            ],
        }
    )

    assert "result_field_invalid" in {error.code for error in errors}


def test_validator_accepts_sheetmetal_slot_length_extension():
    envelope, errors = _validate(
        {
            "domain": "SheetMetal",
            "bucket": "DistanceRule",
            "taxonomy_rules": [
                {
                    "Name": "Bend to slot distance",
                    "RuleCategory": "SheetMetal",
                    "RuleType": "Feature",
                    "Feature1": "Distance",
                    "Object1": "Bend",
                    "Object2": "Slot",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Distance.MinValue",
                                "Operator": [[">="]],
                                "Value": [[["ProportionalityConstant*Slot.Length*SheetMetal.Thickness*Bend.MinRadius"]]],
                                "AllowedParams": ["Slot.Length", "SheetMetal.Thickness", "Bend.MinRadius"],
                            }
                        ],
                        "UserParamList": [
                            {
                                "ParamName": "ProportionalityConstant",
                                "DisplayName": "Proportionality Constant",
                                "Value": [""],
                                "MinValue": "",
                                "MaxValue": "",
                            }
                        ],
                    },
                }
            ],
        },
        domain="SheetMetal",
        bucket="DistanceRule",
    )

    assert envelope is not None
    assert errors == []


def test_grounding_rejects_copied_distance_object_not_in_rule_text():
    rule_text = (
        "The minimum distance from the inside surface of a bend to the edge of a slot is directly proportional "
        "to the length of the slot, material thickness, and radius of the bend."
    )
    payload = normalize_envelope_payload(
        {
            "domain": "SheetMetal",
            "bucket": "DistanceRule",
            "taxonomy_rules": [
                {
                    "Name": "Minimum distance from bend to slot edge",
                    "RuleCategory": "SheetMetal",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "Distance",
                    "Object1": "Bend",
                    "Object2": "Bridge",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Distance.MinValue",
                                "Operator": [[">="]],
                                "Value": [[["Bridge.Length * SheetMetal.Thickness * Bend.MinRadius"]]],
                                "AllowedParams": ["Bridge.Length", "SheetMetal.Thickness", "Bend.MinRadius"],
                            }
                        ]
                    },
                }
            ],
        },
        fallback_domain="SheetMetal",
        fallback_bucket="DistanceRule",
    )

    errors = validate_grounding(rule_text, payload)
    assert "object_grounding_failed" in {error.code for error in errors}
    assert any("Bridge" in error.message for error in errors)
