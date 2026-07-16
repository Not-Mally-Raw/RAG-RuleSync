from dfm_rule_pipeline.taxonomy.bucket_registry import BUCKETS, classify_bucket
from dfm_rule_pipeline.taxonomy.domain_normalizer import domain_from_rule_text, normalize_domain_name, schema_domain_key
from dfm_rule_pipeline.taxonomy.prompt_context import build_taxonomy_prompt
from dfm_rule_pipeline.taxonomy.schema_factory import normalize_envelope_payload, normalize_rule_payload


def test_normalize_domain_aliases_to_latest_taxonomy_names():
    assert normalize_domain_name("Sheetmetal") == "SheetMetal"
    assert normalize_domain_name("Injection Moulding") == "Injection Molding"
    assert normalize_domain_name("SMForm") == "Sheetmetal Forming"
    assert schema_domain_key("SheetMetal") == "Sheetmetal"
    assert domain_from_rule_text("Sheet metal hole diameter should be at least 2 mm") == "SheetMetal"
    assert domain_from_rule_text("Milling drilled holes should avoid partial exits") == "Drilling"
    assert domain_from_rule_text("The minimum distance between two counterbores is eight times the material thickness.") == "Drilling"


def test_domain_detection_uses_taxonomy_disambiguation():
    assert domain_from_rule_text("The mold wall thickness for a casting should be at least 2.5 mm.") == "Die Casting"
    assert domain_from_rule_text("Draft angle for molded ribs should be at least 1 degree.") == "Injection Molding"
    assert domain_from_rule_text("The entry and exit angles for holes should be 0.0 degrees.") == "Drilling"
    assert domain_from_rule_text("Overlap length for tubes should be at least 12.0 units.") == "Tubing"
    assert domain_from_rule_text("Additive print size should not exceed the machine envelope.") == "Additive Manufacturing"
    assert domain_from_rule_text("Thread class should be 2A for external threads.") == "General"


def test_normalize_rule_payload_fills_required_placeholder_lists():
    rule = normalize_rule_payload(
        {
            "Name": "Bridge spacing",
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
        },
        domain="SheetMetal",
        bucket="DistanceRule",
    )

    assert rule["RuleCategory"] == "SheetMetal"
    assert rule["Results"] == "Validation"
    assert rule["RuleType"] == "Feature"
    assert rule["Constraints"]["FilterParamList"] == [{"ExpName": "", "Operator": [""], "Value": [""]}]
    assert rule["Constraints"]["ConditionParamList"] == [{"ExpName": "", "Operator": [[""]], "Value": [[[""]]]}]
    assert rule["Constraints"]["AdditionalParamList"] == [{"ExpName": ""}]
    assert rule["Constraints"]["UserParamList"] == [
        {"ParamName": "", "DisplayName": "", "Value": [""], "MinValue": "", "MaxValue": ""}
    ]


def test_normalize_rule_payload_converts_bucket_rule_type_to_feature():
    rule = normalize_rule_payload(
        {
            "Name": "Counterbore spacing",
            "RuleCategory": "SheetMetal",
            "RuleType": "DistanceRule",
            "Constraints": {
                "ValidationParamList": [
                    {
                        "ExpName": "Distance.MinValue/SheetMetal.Thickness",
                        "Operator": [[">="]],
                        "Value": [[[8]]],
                        "AllowedParams": [""],
                    }
                ]
            },
        },
        domain="SheetMetal",
        bucket="DistanceRule",
    )

    assert rule["RuleType"] == "Feature"
    assert rule["Constraints"]["ValidationParamList"][0]["Value"] == [[["8"]]]


def test_normalize_rule_payload_always_sets_result_to_validation():
    rule = normalize_rule_payload(
        {
            "Name": "Bend distance",
            "RuleCategory": "SheetMetal",
            "Results": "Distance.MinValue >= k * Slot.Length * SheetMetal.Thickness * Bend.MinRadius",
            "RuleType": "Feature",
            "Constraints": {
                "ValidationParamList": [
                    {
                        "ExpName": "Distance.MinValue",
                        "Operator": [[">="]],
                        "Value": [[["1.0"]]],
                        "AllowedParams": [""],
                    }
                ]
            },
        },
        domain="SheetMetal",
        bucket="DistanceRule",
    )

    assert rule["Results"] == "Validation"


def test_envelope_normalization_accepts_single_rule_payload():
    envelope = normalize_envelope_payload(
        {
            "Name": "Material",
            "Constraints": {
                "ValidationParamList": [
                    {
                        "ExpName": "PartBody.Material",
                        "Operator": [["ANY"]],
                        "Value": [[["Steel"], ["Aluminium"]]],
                        "AllowedParams": [""],
                    }
                ]
            },
        },
        fallback_domain="General",
        fallback_bucket="FeatureSetMembership",
    )

    assert envelope["domain"] == "General"
    assert envelope["bucket"] == "FeatureSetMembership"
    assert len(envelope["taxonomy_rules"]) == 1


def test_required_bucket_families_are_registered():
    expected = {
        "FeatureSimpleValidation",
        "FeatureRangeValidation",
        "FeatureSetMembership",
        "FeatureBooleanValidation",
        "FeatureTypedValueValidation",
        "FeatureAllowedParamExpression",
        "FilteredValidation",
        "ConditionalValidation",
        "AdditionalInfoValidation",
        "DistanceRule",
        "ModuleValidation",
        "MultiExpressionValidation",
        "NestedConditionalValidation",
        "MultiRuleDivergence",
    }
    assert expected.issubset(BUCKETS)
    assert classify_bucket("Distance between bridges should be at least 4.5 times sheet thickness") == "DistanceRule"
    assert (
        classify_bucket(
            "The minimum diameter of a teardrop hem is equal to the material thickness, "
            "with a return flange height equal to or greater than four times the material thickness, "
            "and a minimum opening of 1/4 of the material thickness."
        )
        == "MultiExpressionValidation"
    )


def test_bucket_classifier_covers_bucketlist_structural_families():
    assert classify_bucket("In sheetmetal module, the partbody material should be from the following list - Steel, Aluminium") == "ModuleValidation"
    assert classify_bucket("In drilling, check if the hole's thread type is UNF") == "FeatureTypedValueValidation"
    assert classify_bucket("In drilling, check if the holes are blind") == "FeatureBooleanValidation"
    assert classify_bucket("In an assembly, ensure washer is present for fasteners engaging with steel") == "FilteredValidation"
    assert (
        classify_bucket(
            "In Injection Molding part, Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes also check hole diameter at bottom additionally."
        )
        == "AdditionalInfoValidation"
    )
    assert classify_bucket("The entry and exit angles for holes should be 0.0 degrees for proper drilling") == "MultiExpressionValidation"


def test_prompt_contains_compact_taxonomy_and_bucketlist_guidance():
    prompt = build_taxonomy_prompt(
        "In drilling, check if the hole's thread type is UNF",
        "Drilling",
        "FeatureTypedValueValidation",
    )

    assert "Compact taxonomy guidance" in prompt
    assert "Hole.ThreadType = UNF" in prompt
    assert "RuleType must be only \"Feature\" or \"Module\"" in prompt
    assert "Multiple checks on the same feature belong as multiple ValidationParamList entries" in prompt
