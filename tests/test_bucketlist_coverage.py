import json
import pytest
from dfm_rule_pipeline.taxonomy.service import TaxonomyFormalizationService
from dfm_rule_pipeline.taxonomy.models import RuleInput, TaxonomyResponse
from dfm_rule_pipeline.taxonomy.assembler import TaxonomyAssembler
from dfm_rule_pipeline.taxonomy.validator import TaxonomyValidator
from dfm_rule_pipeline.taxonomy.schema_registry import SchemaRegistry
from dfm_rule_pipeline.taxonomy.models import ExtractionResult, FlatValidation, FlatCondition, FlatFilter

# 15 Edge Cases from Section 24 of bucketlist_extraction_edge_cases.md

class MockLLMClient:
    def __init__(self):
        # Maps rule text keywords to the expected intermediate ExtractionResult
        self.mock_responses = {
            "side face angle of the pocket": ExtractionResult(
                domain="Milling",
                bucket="SimpleValidation",
                name="Pocket Face Angle",
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
            ),
            "spoon feature the minimum height": ExtractionResult(
                domain="SheetMetal",
                bucket="RangeValidation",
                name="Spoon Height Range",
                rule_type="Feature",
                feature1="Spoon",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="Spoon.Height", operators=[">", "<"], values=["0.5", "1.2"])
                ],
                conditions=[],
                filters=[],
                additional=[],
                allowed_params=[]
            ),
            "partbody material should be from": ExtractionResult(
                domain="General",
                bucket="SetMembership",
                name="PartBody Material Set",
                rule_type="Module",
                feature1="",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="PartBody.Material", operators=["ANY"], values=["Steel", "Aluminium"])
                ],
                conditions=[],
                filters=[],
                additional=[],
                allowed_params=[]
            ),
            "fasteners engaging with specific": ExtractionResult(
                domain="Assembly",
                bucket="HierarchicalParamValidation",
                name="Fastener Material Hierarchical",
                rule_type="Feature",
                feature1="Fastener",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="Fastener.FirstEngagedComp.Material", operators=["="], values=["Steel"])
                ],
                conditions=[],
                filters=[],
                additional=[],
                allowed_params=[]
            ),
            "ensure partface colour is blue": ExtractionResult(
                domain="Drilling",
                bucket="TypedValueValidation",
                name="Part Face Color RGB",
                rule_type="Feature",
                feature1="PartFace",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="PartFace.Color", operators=["="], values=["0,0,255"])
                ],
                conditions=[],
                filters=[],
                additional=[],
                allowed_params=[]
            ),
            "hole's thread type is unf": ExtractionResult(
                domain="Drilling",
                bucket="TypedValueValidation",
                name="Hole Thread Type Class",
                rule_type="Feature",
                feature1="Hole",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="Hole.ThreadType", operators=["="], values=["UNF"])
                ],
                conditions=[],
                filters=[],
                additional=[],
                allowed_params=[]
            ),
            "check if the holes are blind": ExtractionResult(
                domain="Drilling",
                bucket="BooleanValidation",
                name="Hole Is Blind Check",
                rule_type="Feature",
                feature1="Hole",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="Hole.IsBlind", operators=["="], values=["Yes"])
                ],
                conditions=[],
                filters=[],
                additional=[],
                allowed_params=[]
            ),
            "component's name is xyz": ExtractionResult(
                domain="Assembly",
                bucket="TypedValueValidation",
                name="Component Name Check",
                rule_type="Feature",
                feature1="Component",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="Component.Name", operators=["="], values=["xyz"])
                ],
                conditions=[],
                filters=[],
                additional=[],
                allowed_params=[]
            ),
            "minimum width should be at least 0.8 times": ExtractionResult(
                domain="SheetMetal",
                bucket="AllowedParamValidation",
                name="Spoon Width Formula",
                rule_type="Feature",
                feature1="Spoon",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="Spoon.Width", operators=[">="], values=["0.8*SheetMetal.Thickness"])
                ],
                conditions=[],
                filters=[],
                additional=[],
                allowed_params=["SheetMetal.Thickness"]
            ),
            "washer is present for fasteners engaging with": ExtractionResult(
                domain="Assembly",
                bucket="FilteredValidation",
                name="Fastener Washer Filter",
                rule_type="Feature",
                feature1="Fastener",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="Fastener.IsWasherPresent", operators=["="], values=["Yes"])
                ],
                conditions=[],
                filters=[
                    FlatFilter(exp_name="Fastener.FirstEngagedComp.Material", operator="=", value="Steel")
                ],
                additional=[],
                allowed_params=[]
            ),
            "depth to diameter ratio should be 2.0 for blind holes and 4.0": ExtractionResult(
                domain="Drilling",
                bucket="ConditionalValidation",
                name="Hole Ratio Conditional",
                rule_type="Feature",
                feature1="Hole",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="Hole.TotalDepth/Hole.Diameter", operators=["="], values=["2.0", "4.0"])
                ],
                conditions=[
                    FlatCondition(exp_name="Hole.IsBlind", operators=["="], branches=[["Yes"], ["No"]])
                ],
                filters=[],
                additional=[],
                allowed_params=[]
            ),
            "diameter at bottom additionally": ExtractionResult(
                domain="Drilling",
                bucket="AdditionalInfoValidation",
                name="Hole Additional Check",
                rule_type="Feature",
                feature1="Hole",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="Hole.Diameter", operators=[">="], values=["3.0"])
                ],
                conditions=[],
                filters=[],
                additional=["Hole.TotalDepth"],
                allowed_params=[]
            ),
            "distance between bridges should be at least 4.5": ExtractionResult(
                domain="SheetMetal",
                bucket="DistanceRule",
                name="Bridge Distance Clearance",
                rule_type="Feature",
                feature1="Distance",
                feature2="",
                object1="Bridge",
                object2="Bridge",
                validations=[
                    FlatValidation(exp_name="Distance.MinValue", operators=[">="], values=["4.5*SheetMetal.Thickness"])
                ],
                conditions=[],
                filters=[],
                additional=[],
                allowed_params=["SheetMetal.Thickness"]
            ),
            "ratio of length to minimum outer diameter does not exceed 8.0": ExtractionResult(
                domain="Turning",
                bucket="ModuleValidation",
                name="Body Aspect Ratio",
                rule_type="Module",
                feature1="",
                feature2="",
                object1="",
                object2="",
                validations=[
                    FlatValidation(exp_name="Body.Length/Body.MinOuterDiameter", operators=["<="], values=["8.0"])
                ],
                conditions=[],
                filters=[],
                additional=[],
                allowed_params=[]
            )
        }

    def call(self, prompt: str, json_mode: bool = False) -> str:
        prompt_lower = prompt.lower()
        for keyword, result in self.mock_responses.items():
            if keyword in prompt_lower:
                return result.model_dump_json()
        
        default_res = ExtractionResult(
            domain="General",
            bucket="SimpleValidation",
            name="Default Mock Rule",
            rule_type="Feature",
            feature1="PartEdge",
            feature2="",
            object1="",
            object2="",
            validations=[
                FlatValidation(exp_name="PartEdge.IsSharp", operators=["="], values=["No"])
            ],
            conditions=[],
            filters=[],
            additional=[],
            allowed_params=[]
        )
        return default_res.model_dump_json()

@pytest.fixture
def service():
    mock_llm = MockLLMClient()
    return TaxonomyFormalizationService(llm_client=mock_llm)

def test_case_1_numeric_validation(service):
    text = "The side face angle of the pocket should be at least 13.0 degrees"
    res = service.formalize_rule(RuleInput(rule_text=text))
    assert res.status == "Success"
    assert res.domain == "Milling"
    assert res.bucket == "SimpleValidation"
    
    rule = res.taxonomy_rules[0]
    assert rule.Feature1 == "Pocket"
    v_param = rule.Constraints.ValidationParamList[0]
    assert v_param.ExpName == "Pocket.SideFaceAngle"
    assert v_param.Operator == [[">="]]
    assert v_param.Value == [[["13.0"]]]

def test_case_2_range_validation(service):
    text = "For a spoon feature the minimum height should be between 0.5 and 1.2 times sheet thickness"
    res = service.formalize_rule(RuleInput(rule_text=text))
    assert res.status == "Success"
    assert res.bucket == "RangeValidation"
    
    rule = res.taxonomy_rules[0]
    v_param = rule.Constraints.ValidationParamList[0]
    assert v_param.ExpName == "Spoon.Height"
    assert v_param.Operator == [[">", "<"]]
    assert v_param.Value == [[["0.5", "1.2"]]]

def test_case_3_set_membership(service):
    text = "The partbody material should be from the following list - Steel, Aluminium"
    res = service.formalize_rule(RuleInput(rule_text=text))
    assert res.status == "Success"
    assert res.bucket == "SetMembership"
    
    rule = res.taxonomy_rules[0]
    assert rule.RuleType == "Module"
    v_param = rule.Constraints.ValidationParamList[0]
    assert v_param.ExpName == "PartBody.Material"
    assert v_param.Operator == [["ANY"]]
    assert v_param.Value == [[["Steel"], ["Aluminium"]]]

def test_case_4_hierarchical_parameter(service):
    text = "Ensure fasteners engaging with specific materials use correct thread"
    res = service.formalize_rule(RuleInput(rule_text=text, rule_type="Assembly"))
    assert res.status == "Success"
    rule = res.taxonomy_rules[0]
    assert rule.Constraints.ValidationParamList[0].ExpName == "Fastener.FirstEngagedComp.Material"

def test_case_5_color_parameter(service):
    text = "In drilling, ensure partface colour is blue"
    res = service.formalize_rule(RuleInput(rule_text=text))
    assert res.status == "Success"
    rule = res.taxonomy_rules[0]
    assert rule.Constraints.ValidationParamList[0].Value == [[["0,0,255"]]]

def test_case_6_string_value_and_type(service):
    text = "In drilling, check if the hole's thread type is UNF"
    res = service.formalize_rule(RuleInput(rule_text=text))
    assert res.status == "Success"
    rule = res.taxonomy_rules[0]
    assert rule.Constraints.ValidationParamList[0].ExpName == "Hole.ThreadType"
    assert rule.Constraints.ValidationParamList[0].Value == [[["UNF"]]]

def test_case_7_boolean_is_parameter(service):
    text = "In drilling, check if the holes are blind"
    res = service.formalize_rule(RuleInput(rule_text=text))
    assert res.status == "Success"
    rule = res.taxonomy_rules[0]
    assert rule.Constraints.ValidationParamList[0].ExpName == "Hole.IsBlind"
    assert rule.Constraints.ValidationParamList[0].Value == [[["Yes"]]]

def test_case_8_allowed_params_formula(service):
    text = "For a spoon feature, the minimum width should be at least 0.8 times sheet thickness"
    res = service.formalize_rule(RuleInput(rule_text=text))
    assert res.status == "Success"
    rule = res.taxonomy_rules[0]
    v_param = rule.Constraints.ValidationParamList[0]
    assert v_param.Value == [[["0.8*SheetMetal.Thickness"]]]
    assert "SheetMetal.Thickness" in v_param.AllowedParams

def test_case_9_filtered_validation(service):
    text = "Ensure washer is present for fasteners engaging with Steel"
    res = service.formalize_rule(RuleInput(rule_text=text))
    assert res.status == "Success"
    rule = res.taxonomy_rules[0]
    assert rule.Constraints.FilterParamList[0].ExpName == "Fastener.FirstEngagedComp.Material"
    assert rule.Constraints.FilterParamList[0].Value == ["Steel"]
    assert rule.Constraints.ValidationParamList[0].ExpName == "Fastener.IsWasherPresent"

def test_case_10_conditional_validation(service):
    text = "Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes"
    res = service.formalize_rule(RuleInput(rule_text=text))
    assert res.status == "Success"
    rule = res.taxonomy_rules[0]
    
    cond = rule.Constraints.ConditionParamList[0]
    assert cond.ExpName == "Hole.IsBlind"
    assert cond.Value == [[["Yes"]], [["No"]]]
    
    val = rule.Constraints.ValidationParamList[0]
    assert val.Value == [[["2.0"]], [["4.0"]]]

def test_case_11_additional_param(service):
    text = "Check hole diameter at bottom additionally"
    res = service.formalize_rule(RuleInput(rule_text=text, rule_type="Drilling"))
    assert res.status == "Success"
    rule = res.taxonomy_rules[0]
    assert rule.Constraints.AdditionalParamList[0].ExpName == "Hole.TotalDepth"

def test_case_12_distance_rule(service):
    text = "Distance between bridges should be at least 4.5 times sheet thickness"
    res = service.formalize_rule(RuleInput(rule_text=text))
    assert res.status == "Success"
    rule = res.taxonomy_rules[0]
    assert rule.Feature1 == "Distance"
    assert rule.Object1 == "Bridge"
    assert rule.Object2 == "Bridge"

def test_case_13_module_level_ratio(service):
    text = "Ensure the ratio of length to minimum outer diameter does not exceed 8.0"
    res = service.formalize_rule(RuleInput(rule_text=text, rule_type="Turning"))
    assert res.status == "Success"
    rule = res.taxonomy_rules[0]
    assert rule.RuleType == "Module"
    assert rule.Feature1 == ""
    assert rule.Constraints.ValidationParamList[0].ExpName == "Body.Length/Body.MinOuterDiameter"
