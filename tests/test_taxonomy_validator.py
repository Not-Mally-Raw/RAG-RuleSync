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


def test_grounding_accepts_camelcase_teardrop_hem_alias():
    rule_text = (
        "The minimum diameter of a teardrop hem is equal to the material thickness, "
        "with a return flange height equal to or greater than four times the material thickness."
    )
    payload = normalize_envelope_payload(
        {
            "domain": "SheetMetal",
            "bucket": "MultiExpressionValidation",
            "taxonomy_rules": [
                {
                    "Name": "Teardrop hem parameters",
                    "RuleCategory": "SheetMetal",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "TearDropHem",
                    "Object1": "TearDropHem",
                    "Object2": "Flange",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "TearDropHem.Radius",
                                "Operator": [["="]],
                                "Value": [[["0.5*SheetMetal.Thickness"]]],
                                "AllowedParams": ["SheetMetal.Thickness"],
                            }
                        ]
                    },
                }
            ],
        },
        fallback_domain="SheetMetal",
        fallback_bucket="MultiExpressionValidation",
    )

    assert validate_grounding(rule_text, payload) == []


def test_grounding_allows_formula_root_from_structural_feature():
    payload = normalize_envelope_payload(
        {
            "domain": "SheetMetal",
            "bucket": "MultiExpressionValidation",
            "taxonomy_rules": [
                {
                    "Name": "Hem opening",
                    "RuleCategory": "SheetMetal",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "TearDropHem",
                    "Object1": "",
                    "Object2": "",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "TearDropHem.HemOpening",
                                "Operator": [[">="]],
                                "Value": [[["0.25*SheetMetal.Thickness"]]],
                                "AllowedParams": ["SheetMetal.Thickness"],
                            }
                        ]
                    },
                }
            ],
        },
        fallback_domain="SheetMetal",
        fallback_bucket="MultiExpressionValidation",
    )

    assert validate_grounding("The hem opening should be at least one quarter of material thickness.", payload) == []


def test_validator_accepts_branch_specific_condition_operator_table():
    payload = normalize_envelope_payload(
        {
            "domain": "Drilling",
            "bucket": "NestedConditionalValidation",
            "taxonomy_rules": [
                {
                    "Name": "Recommended Position Tolerance for Hole",
                    "RuleCategory": "Drilling",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "HoleSegment",
                    "Feature2": "",
                    "Object1": "",
                    "Object2": "",
                    "Constraints": {
                        "FilterParamList": [{"ExpName": "", "Operator": [""], "Value": [""]}],
                        "ConditionParamList": [
                            {
                                "ExpName": "PartBody.TightBoxDiagonalLength",
                                "Operator": [["="], [">", "<="]],
                                "Value": [[["Default"]], [["0.0", "25.4"]]],
                            },
                            {
                                "ExpName": "HoleSegment.Diameter",
                                "Operator": [[""], [">", "<="]],
                                "Value": [[[""]], [["5.05714", "7.54126"]]],
                            },
                        ],
                        "ValidationParamList": [
                            {
                                "ExpName": "HoleSegment.PositionTolerance",
                                "Operator": [["<="]],
                                "Value": [[["0.0254"]], [["0.0508"]]],
                                "AllowedParams": [""],
                            }
                        ],
                        "AdditionalParamList": [{"ExpName": ""}],
                        "UserParamList": [
                            {"ParamName": "", "DisplayName": "", "Value": [""], "MinValue": "", "MaxValue": ""}
                        ],
                    },
                }
            ],
        },
        fallback_domain="Drilling",
        fallback_bucket="NestedConditionalValidation",
    )

    envelope, errors = TaxonomyValidator().validate(payload)

    assert envelope is not None
    assert errors == []


def test_unwrap_nested_envelope_payload():
    raw_payload = {
        "domain": "SheetMetal",
        "bucket": "MultiExpressionValidation",
        "taxonomy_rules": [
            {
                "domain": "SheetMetal",
                "bucket": "MultiExpressionValidation",
                "taxonomy_rules": [
                    {
                        "Name": "Dimple parameters",
                        "RuleCategory": "SheetMetal",
                        "Results": "Validation",
                        "RuleType": "Feature",
                        "Feature1": "Dimple",
                        "Constraints": {
                            "ValidationParamList": [
                                {
                                    "ExpName": "Dimple.DieInnerRadius",
                                    "Operator": [[">="]],
                                    "Value": [[["2.0"]]],
                                    "AllowedParams": [""],
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    payload = normalize_envelope_payload(raw_payload, fallback_domain="SheetMetal", fallback_bucket="MultiExpressionValidation")
    assert payload["domain"] == "SheetMetal"
    assert payload["bucket"] == "MultiExpressionValidation"
    assert len(payload["taxonomy_rules"]) == 1
    assert payload["taxonomy_rules"][0]["Feature1"] == "Dimple"


def test_grounding_allows_pmi_tolerance_attributes_without_text():
    rule_text = "Bends should be toleranced plus or minus one-half degree at a location adjacent to the bends."
    payload = normalize_envelope_payload(
        {
            "domain": "General",
            "bucket": "FeatureSimpleValidation",
            "taxonomy_rules": [
                {
                    "Name": "Bend tolerance",
                    "RuleCategory": "General",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "Bend",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                    "ExpName": "PMI.Angularity",
                                    "Operator": [["<="]],
                                    "Value": [[["0.5"]]],
                                    "AllowedParams": [""],
                            }
                        ]
                    }
                }
            ]
        },
        fallback_domain="General",
        fallback_bucket="FeatureSimpleValidation"
    )
    errors = validate_grounding(rule_text, payload)
    assert errors == []


def test_grounding_allows_curl_and_opening_aliases_for_hem():
    rule_text = "The minimum radius is two times the material thickness with an opening to a minimum of one material thickness."
    payload = normalize_envelope_payload(
        {
            "domain": "SheetMetal",
            "bucket": "MultiExpressionValidation",
            "taxonomy_rules": [
                {
                    "Name": "Curl radius and opening",
                    "RuleCategory": "SheetMetal",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "RolledHem",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "RolledHem.Radius",
                                "Operator": [[">="]],
                                "Value": [[["2.0*SheetMetal.Thickness"]]],
                                "AllowedParams": ["SheetMetal.Thickness"],
                            },
                            {
                                "ExpName": "RolledHem.HemOpening",
                                "Operator": [[">="]],
                                "Value": [[["1.0*SheetMetal.Thickness"]]],
                                "AllowedParams": ["SheetMetal.Thickness"],
                            }
                        ]
                    }
                }
            ]
        },
        fallback_domain="SheetMetal",
        fallback_bucket="MultiExpressionValidation"
    )
    errors = validate_grounding(rule_text, payload)
    assert errors == []


def test_grounding_allows_edge_alias_for_part_edge():
    rule_text = "The minimum distance a rib should be from an edge in a perpendicular plane is four times the material thickness plus the radius of the rib."
    payload = normalize_envelope_payload(
        {
            "domain": "Injection Molding",
            "bucket": "DistanceRule",
            "taxonomy_rules": [
                {
                    "Name": "Rib to edge distance",
                    "RuleCategory": "Injection Molding",
                    "Results": "Validation",
                    "RuleType": "Feature",
                    "Feature1": "Distance",
                    "Object1": "Rib",
                    "Object2": "Part Edge",
                    "Constraints": {
                        "ValidationParamList": [
                            {
                                "ExpName": "Distance.MinValue/InjectionMolding.NominalThickness",
                                "Operator": [[">="]],
                                "Value": [[["4.0*InjectionMolding.NominalThickness + Rib.RadiusAtBot"]]],
                                "AllowedParams": ["InjectionMolding.NominalThickness", "Rib.RadiusAtBot"],
                            }
                        ]
                    }
                }
            ]
        },
        fallback_domain="Injection Molding",
        fallback_bucket="DistanceRule"
    )
    errors = validate_grounding(rule_text, payload)
    assert errors == []


