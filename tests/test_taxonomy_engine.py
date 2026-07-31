import json
from pathlib import Path
import pytest

from dfm_rule_pipeline.taxonomy.schema_registry import SchemaRegistry
from dfm_rule_pipeline.taxonomy.bucket_classifier import BucketClassifier
from dfm_rule_pipeline.taxonomy.assembler import TaxonomyAssembler
from dfm_rule_pipeline.taxonomy.validator import TaxonomyValidator
from dfm_rule_pipeline.taxonomy.models import (
    ExtractionResult, FlatValidation, FlatCondition, FlatFilter, TaxonomyRule
)

@pytest.fixture
def registry():
    # Load from package registry config
    return SchemaRegistry()

@pytest.fixture
def assembler():
    return TaxonomyAssembler()

@pytest.fixture
def validator():
    return TaxonomyValidator()

def test_registry_loading(registry):
    assert registry.is_valid_domain("SheetMetal")
    assert registry.is_valid_domain("Drilling")
    assert not registry.is_valid_domain("Cabling")
    
    # Test normalization
    assert registry.get_canonical_domain("sheet metal") == "SheetMetal"
    assert registry.get_canonical_domain("casting") == "Die Casting"

def test_classifier_domain_scoring(registry):
    classifier = BucketClassifier(registry, embedder=None)
    
    # Keyword matches
    res1 = classifier.classify("Distance between bridge elements should be checked")
    assert res1.domain == "SheetMetal"
    
    res2 = classifier.classify("Pocket side face angle should be at least 13 degrees")
    assert res2.domain == "Milling"
    
    # Override tags
    res3 = classifier.classify("Hole diameter check", explicit_domain="Injection Molding")
    assert res3.domain == "Injection Molding"

def test_registry_validation(registry):
    # Valid direct path
    errs = registry.validate_exp_name("SheetMetal", "Bend.MinRadius")
    assert len(errs) == 0

    # Invalid root
    errs = registry.validate_exp_name("SheetMetal", "InvalidFeature.MinRadius")
    assert len(errs) > 0
    assert "InvalidFeature" in errs[0]

    # Invalid attribute (auto_register=False to avoid polluting the on-disk schema)
    errs = registry.validate_exp_name("SheetMetal", "Bend.InvalidAttribute", auto_register=False)
    assert len(errs) > 0
    assert "InvalidAttribute" in errs[0]

    # Ratio path
    errs = registry.validate_exp_name("Drilling", "Hole.TotalDepth/Hole.Diameter")
    assert len(errs) == 0

def test_registry_formula_validation(registry):
    errs = registry.validate_formula_refs("SheetMetal", "4.5*SheetMetal.Thickness")
    assert len(errs) == 0

    errs = registry.validate_formula_refs("SheetMetal", "4.5*InvalidObject.Thickness")
    assert len(errs) > 0

def test_assembler_simple_validation(assembler):
    flat = ExtractionResult(
        domain="SheetMetal",
        bucket="SimpleValidation",
        name="Side Face Angle",
        rule_type="Feature",
        feature1="Pocket",
        feature2="",
        object1="",
        object2="",
        validations=[
            FlatValidation(exp_name="Pocket.SideFaceAngle", operators=[">="], values=["13.0"])
        ],
        conditions=[],
        filters=[],
        additional=[],
        allowed_params=[]
    )
    rule = assembler.assemble(flat)
    assert rule.Name == "Side Face Angle"
    assert rule.Constraints.ValidationParamList[0].ExpName == "Pocket.SideFaceAngle"
    assert rule.Constraints.ValidationParamList[0].Operator == [[">="]]
    assert rule.Constraints.ValidationParamList[0].Value == [[["13.0"]]]

def test_assembler_range_validation(assembler):
    flat = ExtractionResult(
        domain="SheetMetal",
        bucket="RangeValidation",
        name="Spoon Height Limit",
        rule_type="Feature",
        feature1="Spoon",
        feature2="",
        object1="",
        object2="",
        validations=[
            FlatValidation(exp_name="Spoon.Height", operators=[">=", "<="], values=["0.5", "1.2"])
        ],
        conditions=[],
        filters=[],
        additional=[],
        allowed_params=[]
    )
    rule = assembler.assemble(flat)
    assert rule.Constraints.ValidationParamList[0].Operator == [[">=", "<="]]
    assert rule.Constraints.ValidationParamList[0].Value == [[["0.5", "1.2"]]]

def test_assembler_conditional_branching(assembler):
    flat = ExtractionResult(
        domain="Drilling",
        bucket="ConditionalValidation",
        name="Aspect Ratio",
        rule_type="Feature",
        feature1="Hole",
        feature2="",
        object1="",
        object2="",
        validations=[
            FlatValidation(
                exp_name="Hole.TotalDepth/Hole.Diameter",
                operators=["="],
                values=["2.0", "4.0"]
            )
        ],
        conditions=[
            FlatCondition(
                exp_name="Hole.IsBlind",
                operators=["="],
                branches=[["Yes"], ["No"]]
            )
        ],
        filters=[],
        additional=[],
        allowed_params=[]
    )
    rule = assembler.assemble(flat)
    
    # Assert branch alignment (values replicated or mapped to branch count)
    assert len(rule.Constraints.ConditionParamList[0].Value) == 2
    assert len(rule.Constraints.ValidationParamList[0].Value) == 2
    assert rule.Constraints.ValidationParamList[0].Value == [[["2.0"]], [["4.0"]]]

def test_validator_success(validator, registry):
    # Build valid rule
    rule = TaxonomyRule(
        Name="Test Angle",
        RuleCategory="SheetMetal",
        Results="Validation",
        RuleType="Feature",
        Feature1="Bend",
        Feature2="",
        Object1="",
        Object2="",
        Constraints=TaxonomyRule.__pydantic_validator__.validate_assignment(
            TaxonomyRule.model_construct(), "Constraints", 
            dict(
                FilterParamList=[dict(ExpName="", Operator=[""], Value=[""])],
                ConditionParamList=[dict(ExpName="", Operator=[[""]], Value=[[[""]]])],
                ValidationParamList=[dict(
                    ExpName="Bend.Angle",
                    Operator=[[">="]],
                    Value=[[["13.0"]]],
                    AllowedParams=[""]
                )],
                AdditionalParamList=[dict(ExpName="")],
                UserParamList=[dict(ParamName="", DisplayName="", Value=[""], MinValue="", MaxValue="")]
            )
        ).Constraints
    )
    errs = validator.validate(rule, "SheetMetal", registry)
    assert len(errs) == 0

def test_validator_failures(validator, registry):
    # Rule with invalid ExpName and invalid boolean yes/no
    rule = TaxonomyRule(
        Name="Test Fail",
        RuleCategory="Drilling",
        Results="Validation",
        RuleType="Feature",
        Feature1="Hole",
        Feature2="",
        Object1="",
        Object2="",
        Constraints=TaxonomyRule.__pydantic_validator__.validate_assignment(
            TaxonomyRule.model_construct(), "Constraints", 
            dict(
                FilterParamList=[dict(ExpName="", Operator=[""], Value=[""])],
                ConditionParamList=[dict(
                    ExpName="Hole.IsBlind",
                    Operator=[["="]],
                    Value=[[["True"]]]  # Should be 'Yes' or 'No'
                )],
                ValidationParamList=[dict(
                    ExpName="Hole.InvalidAttr", # Invalid attribute
                    Operator=[[">="]],
                    Value=[[["13.0"]]],
                    AllowedParams=[""]
                )],
                AdditionalParamList=[dict(ExpName="")],
                UserParamList=[dict(ParamName="", DisplayName="", Value=[""], MinValue="", MaxValue="")]
            )
        ).Constraints
    )
    errs = validator.validate(rule, "Drilling", registry, auto_register=False)
    codes = {e.code for e in errs}
    assert "schema_attribute_failed" in codes
    assert "boolean_value_invalid" in codes
