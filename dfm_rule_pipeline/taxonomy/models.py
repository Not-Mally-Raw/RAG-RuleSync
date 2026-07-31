from __future__ import annotations

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# 1. Intermediate Format Models (flat, what LLM returns)
# -----------------------------------------------------------------------------

class FlatValidation(BaseModel):
    """
    Represents a flat validation rule.
    """
    exp_name: str = ""  # e.g. "Pocket.SideFaceAngle"
    operators: list[str] = Field(default_factory=list)  # e.g. [">="] or [">", "<"] for range
    values: list[str] = Field(default_factory=list)  # e.g. ["13.0"] or ["0.5", "1.2"] for range


class FlatCondition(BaseModel):
    """
    Represents a flat condition rule.
    """
    exp_name: str = ""  # e.g. "Hole.IsBlind"
    operators: list[str] = Field(default_factory=list)  # e.g. ["="]
    branches: list[list[str]] = Field(default_factory=list)  # e.g. [["Yes"], ["No"]] — one inner list per branch


class FlatFilter(BaseModel):
    """
    Represents a flat filter rule.
    """
    exp_name: str = ""  # e.g. "Fastener.FirstEngagedComp.Material"
    operator: str = ""  # e.g. "="
    value: str = ""  # e.g. "Steel"


class ExtractionResult(BaseModel):
    """
    Represents the intermediate extraction result from the LLM.
    """
    domain: str = "General"
    bucket: str = "SimpleValidation"
    name: str = "Unnamed Rule"
    rule_type: str = "Feature"  # "Feature" or "Module"
    feature1: str = ""
    feature2: str = ""
    object1: str = ""
    object2: str = ""
    validations: list[FlatValidation] = Field(default_factory=list)
    conditions: list[FlatCondition] = Field(default_factory=list)
    filters: list[FlatFilter] = Field(default_factory=list)
    additional: list[str] = Field(default_factory=list)  # list of ExpName strings
    allowed_params: list[str] = Field(default_factory=list)  # list of schema path strings


# -----------------------------------------------------------------------------
# 2. Final Taxonomy Schema Models (deeply nested output)
# -----------------------------------------------------------------------------

class FilterParam(BaseModel):
    """
    Taxonomy filter parameter.
    """
    ExpName: str = ""
    Operator: list[str] = Field(default_factory=lambda: [""])
    Value: list[str] = Field(default_factory=lambda: [""])

    @classmethod
    def placeholder(cls) -> FilterParam:
        return cls()


class ConditionParam(BaseModel):
    """
    Taxonomy condition parameter.
    """
    ExpName: str = ""
    Operator: list[list[str]] = Field(default_factory=lambda: [[""]])
    Value: list[list[list[str]]] = Field(default_factory=lambda: [[[""]]])

    @classmethod
    def placeholder(cls) -> ConditionParam:
        return cls()


class ValidationParam(BaseModel):
    """
    Taxonomy validation parameter.
    """
    ExpName: str = ""
    Operator: list[list[str]] = Field(default_factory=lambda: [[""]])
    Value: list[list[list[str]]] = Field(default_factory=lambda: [[[""]]])
    AllowedParams: list[str] = Field(default_factory=lambda: [""])

    @classmethod
    def placeholder(cls) -> ValidationParam:
        return cls()


class AdditionalParam(BaseModel):
    """
    Taxonomy additional parameter.
    """
    ExpName: str = ""

    @classmethod
    def placeholder(cls) -> AdditionalParam:
        return cls()


class UserParam(BaseModel):
    """
    Taxonomy user parameter.
    """
    ParamName: str = ""
    DisplayName: str = ""
    Value: list[str] = Field(default_factory=lambda: [""])
    MinValue: str = ""
    MaxValue: str = ""

    @classmethod
    def placeholder(cls) -> UserParam:
        return cls()


class Constraints(BaseModel):
    """
    Taxonomy constraints encapsulating parameters.
    """
    FilterParamList: list[FilterParam]
    ConditionParamList: list[ConditionParam]
    ValidationParamList: list[ValidationParam]
    AdditionalParamList: list[AdditionalParam]
    UserParamList: list[UserParam]

    @classmethod
    def empty(cls) -> Constraints:
        return cls(
            FilterParamList=[FilterParam.placeholder()],
            ConditionParamList=[ConditionParam.placeholder()],
            ValidationParamList=[ValidationParam.placeholder()],
            AdditionalParamList=[AdditionalParam.placeholder()],
            UserParamList=[UserParam.placeholder()]
        )


class TaxonomyRule(BaseModel):
    """
    Taxonomy rule matching the format1 JSON schema.
    """
    Name: str
    RuleCategory: str
    Results: str = "Validation"
    RuleType: str  # "Feature" or "Module"
    Feature1: str = ""
    Feature2: str = ""
    Object1: str = ""
    Object2: str = ""
    Constraints: Constraints


# -----------------------------------------------------------------------------
# 3. API Response Models
# -----------------------------------------------------------------------------

class ValidationErrorDetail(BaseModel):
    """
    Details about a validation error.
    """
    code: str  # error code like "schema_root_failed"
    message: str
    location: str  # JSON path like "taxonomy_rules[0].Constraints.ValidationParamList[0].ExpName"
    suggestion: str = ""


class RuleInput(BaseModel):
    """
    Input model for a rule.
    """
    rule_text: str
    rule_type: str | None = None  # optional domain override


class TaxonomyResponse(BaseModel):
    """
    Response model for the taxonomy API.
    """
    rule_text: str
    status: str  # "Success" or "Review Needed"
    decision_code: str  # "formalized", "validation_failed", "llm_failed", "repair_failed", etc.
    domain: str
    bucket: str
    taxonomy_rules: list[TaxonomyRule]
    validation_errors: list[ValidationErrorDetail]
