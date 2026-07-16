from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - pydantic v1 compatibility
    ConfigDict = None


class StrictModel(BaseModel):
    if ConfigDict is not None:
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover - pydantic v1 compatibility
        class Config:
            extra = "forbid"


class FilterParam(StrictModel):
    ExpName: str = ""
    Operator: List[str] = Field(default_factory=lambda: [""])
    Value: List[str] = Field(default_factory=lambda: [""])


class ConditionParam(StrictModel):
    ExpName: str = ""
    Operator: List[List[str]] = Field(default_factory=lambda: [[""]])
    Value: List[List[List[str]]] = Field(default_factory=lambda: [[[""]]])


class ValidationParam(StrictModel):
    ExpName: str = ""
    Operator: List[List[str]] = Field(default_factory=lambda: [[""]])
    Value: List[List[List[str]]] = Field(default_factory=lambda: [[[""]]])
    AllowedParams: List[str] = Field(default_factory=lambda: [""])


class AdditionalParam(StrictModel):
    ExpName: str = ""


class UserParam(StrictModel):
    ParamName: str = ""
    DisplayName: str = ""
    Value: List[str] = Field(default_factory=lambda: [""])
    MinValue: str = ""
    MaxValue: str = ""


class ConstraintSet(StrictModel):
    FilterParamList: List[FilterParam] = Field(default_factory=lambda: [FilterParam()])
    ConditionParamList: List[ConditionParam] = Field(default_factory=lambda: [ConditionParam()])
    ValidationParamList: List[ValidationParam] = Field(default_factory=lambda: [ValidationParam()])
    AdditionalParamList: List[AdditionalParam] = Field(default_factory=lambda: [AdditionalParam()])
    UserParamList: List[UserParam] = Field(default_factory=lambda: [UserParam()])


class TaxonomyRule(StrictModel):
    Name: str = ""
    RuleCategory: str = ""
    Results: str = "Validation"
    RuleType: str = "Feature"
    Feature1: str = ""
    Feature2: str = ""
    Object1: str = ""
    Object2: str = ""
    Constraints: ConstraintSet = Field(default_factory=ConstraintSet)


class TaxonomyEnvelope(StrictModel):
    domain: str = ""
    bucket: str = ""
    taxonomy_rules: List[TaxonomyRule] = Field(default_factory=list)


class TaxonomyValidationError(StrictModel):
    code: str
    message: str
    location: str
    suggestion: str = ""


class TaxonomyResponseItem(StrictModel):
    rule_text: str
    status: str
    decision_code: str
    domain: str = ""
    bucket: str = ""
    taxonomy_rules: List[Dict[str, Any]] = Field(default_factory=list)
    validation_errors: List[Dict[str, Any]] = Field(default_factory=list)


def model_dump_compat(model: Any) -> Dict[str, Any]:
    """Return a dict for either pydantic v1 or v2 models."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def model_validate_compat(model_cls: Any, payload: Any) -> Any:
    """Validate data for either pydantic v1 or v2 models."""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(payload)
    return model_cls.parse_obj(payload)
