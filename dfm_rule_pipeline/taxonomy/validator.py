"""
Deterministic DFM Rule Validator for DFM Taxonomy V3.

Implements all 17 schema-driven validation checks, validating assembled
TaxonomyRule instances against domain features, allowed values,
array dimensions, and formula dependencies.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from dfm_rule_pipeline.taxonomy.models import (
    TaxonomyRule,
    ValidationErrorDetail,
    FilterParam,
    ConditionParam,
    ValidationParam,
)
from dfm_rule_pipeline.taxonomy.schema_registry import SchemaRegistry, extract_schema_refs

logger = logging.getLogger("taxonomy.validator")

# Supported operators list
ALLOWED_OPERATORS = {">=", "<=", ">", "<", "=", "ANY"}
# Unwanted unit patterns in numeric values
UNIT_PATTERN = re.compile(r"(?i)\b(deg|degree|degrees|mm|millimeter|millimeters|inch|inches|in|m|rad|radian|radians|times)\b")


class TaxonomyValidator:
    """
    Validates assembled TaxonomyRule objects against the SchemaRegistry.
    
    Returns a list of ValidationErrorDetail containing error codes and suggestions.
    """

    def validate(
        self,
        rule: TaxonomyRule,
        domain: str,
        schema_registry: Optional[SchemaRegistry] = None,
        auto_register: bool = True,
    ) -> List[ValidationErrorDetail]:
        errors: List[ValidationErrorDetail] = []

        # Check 1: All 5 constraint lists must be present
        if not hasattr(rule, "Constraints") or rule.Constraints is None:
            errors.append(
                ValidationErrorDetail(
                    code="missing_constraint_list",
                    message="Constraints object is missing in taxonomy rule.",
                    location="Constraints",
                    suggestion="Ensure Constraints is constructed and non-null.",
                )
            )
            return errors

        c = rule.Constraints
        lists = {
            "FilterParamList": getattr(c, "FilterParamList", None),
            "ConditionParamList": getattr(c, "ConditionParamList", None),
            "ValidationParamList": getattr(c, "ValidationParamList", None),
            "AdditionalParamList": getattr(c, "AdditionalParamList", None),
            "UserParamList": getattr(c, "UserParamList", None),
        }

        for list_name, val in lists.items():
            if val is None or not isinstance(val, list) or len(val) == 0:
                errors.append(
                    ValidationErrorDetail(
                        code="missing_constraint_list",
                        message=f"Constraint list '{list_name}' is missing or empty.",
                        location=f"Constraints.{list_name}",
                        suggestion=f"Provide a list with at least a placeholder parameter for {list_name}.",
                    )
                )

        # Skip remaining validations if base structure has failed completely
        if errors:
            return errors

        # Validate FilterParamList shape and values
        for idx, filter_param in enumerate(c.FilterParamList):
            self._validate_filter(filter_param, idx, errors, domain, schema_registry)

        # Validate ConditionParamList shape and values
        for idx, condition_param in enumerate(c.ConditionParamList):
            self._validate_condition(condition_param, idx, errors, domain, schema_registry)

        # Validate ValidationParamList shape, values, ranges, allowed parameters
        for idx, val_param in enumerate(c.ValidationParamList):
            self._validate_validation(val_param, idx, errors, domain, schema_registry, auto_register=auto_register)

        # Validate AdditionalParamList
        for idx, add_param in enumerate(c.AdditionalParamList):
            self._validate_additional(add_param, idx, errors, domain, schema_registry)

        # Validate Rule-Level and Feature constraints
        self._validate_rule_logic(rule, errors, domain, schema_registry)

        # Validate Condition-Validation Branch Alignment
        self._validate_branch_alignment(c, errors)

        return errors

    # ------------------------------------------------------------------
    # Parameter-level validation functions
    # ------------------------------------------------------------------

    def _validate_filter(
        self,
        param: FilterParam,
        idx: int,
        errors: List[ValidationErrorDetail],
        domain: str,
        schema_registry: Optional[SchemaRegistry],
    ) -> None:
        path = f"Constraints.FilterParamList[{idx}]"
        # If placeholder, skip
        if not param.ExpName:
            return

        # Check: Filter shape must be flat (1D lists)
        if not isinstance(param.Operator, list) or (param.Operator and isinstance(param.Operator[0], list)):
            errors.append(
                ValidationErrorDetail(
                    code="filter_shape_invalid",
                    message="FilterParamList Operator must be a 1D list (e.g. ['=']).",
                    location=f"{path}.Operator",
                    suggestion="Flattem the operator list in the assembler.",
                )
            )

        if not isinstance(param.Value, list) or (param.Value and isinstance(param.Value[0], list)):
            errors.append(
                ValidationErrorDetail(
                    code="filter_value_shape_invalid",
                    message="FilterParamList Value must be a 1D list (e.g. ['Steel']).",
                    location=f"{path}.Value",
                    suggestion="Flatten the value list in the assembler.",
                )
            )

        # Operator check
        for op in param.Operator:
            if op and op not in ALLOWED_OPERATORS:
                errors.append(
                    ValidationErrorDetail(
                        code="unsupported_operator",
                        message=f"Operator '{op}' is not supported. Allowed: {ALLOWED_OPERATORS}",
                        location=f"{path}.Operator",
                        suggestion="Map comparison words to standard operators like >=, <=, =, ANY.",
                    )
                )

        # Schema check
        if schema_registry:
            schema_errs = schema_registry.validate_exp_name(domain, param.ExpName)
            for err in schema_errs:
                errors.append(
                    ValidationErrorDetail(
                        code="schema_root_failed" if "Object" in err else "schema_attribute_failed",
                        message=err,
                        location=f"{path}.ExpName",
                        suggestion="Map ExpName to actual features and attributes defined in schema_registry.json.",
                    )
                )

    def _validate_condition(
        self,
        param: ConditionParam,
        idx: int,
        errors: List[ValidationErrorDetail],
        domain: str,
        schema_registry: Optional[SchemaRegistry],
    ) -> None:
        path = f"Constraints.ConditionParamList[{idx}]"
        if not param.ExpName:
            return

        # Check: Condition Operator must be list[list[str]] (2D)
        if not isinstance(param.Operator, list) or (param.Operator and not isinstance(param.Operator[0], list)):
            errors.append(
                ValidationErrorDetail(
                    code="condition_shape_invalid",
                    message="ConditionParamList Operator must be a 2D list (e.g. [['=']]).",
                    location=f"{path}.Operator",
                    suggestion="Nest the condition operator list (e.g. list[list[str]]).",
                )
            )

        # Check: Condition Value must be list[list[list[str]]] (3D)
        if not self._is_3d_list(param.Value):
            errors.append(
                ValidationErrorDetail(
                    code="condition_value_shape_invalid",
                    message="ConditionParamList Value must be a 3D list (e.g. [[['Yes']], [['No']]]).",
                    location=f"{path}.Value",
                    suggestion="Nest the condition branches to triple-nested array shape.",
                )
            )

        # Operator check
        if isinstance(param.Operator, list):
            for inner in param.Operator:
                if isinstance(inner, list):
                    for op in inner:
                        if op and op not in ALLOWED_OPERATORS:
                            errors.append(
                                ValidationErrorDetail(
                                    code="unsupported_operator",
                                    message=f"Operator '{op}' is not supported.",
                                    location=f"{path}.Operator",
                                    suggestion="Normalize operator to standard symbol.",
                                )
                            )

        # Value checks: check for Yes/No on boolean conditions
        if ".Is" in param.ExpName:
            for branch in param.Value:
                for leaf_list in branch:
                    for val in leaf_list:
                        if val not in ("Yes", "No", ""):
                            errors.append(
                                ValidationErrorDetail(
                                    code="boolean_value_invalid",
                                    message=f"Boolean value '{val}' in condition is invalid. Use 'Yes' or 'No'.",
                                    location=f"{path}.Value",
                                    suggestion="Map true/false/1/0 string values to canonical 'Yes' or 'No'.",
                                )
                            )

        # Schema check
        if schema_registry:
            schema_errs = schema_registry.validate_exp_name(domain, param.ExpName)
            for err in schema_errs:
                errors.append(
                    ValidationErrorDetail(
                        code="schema_root_failed" if "Object" in err else "schema_attribute_failed",
                        message=err,
                        location=f"{path}.ExpName",
                        suggestion="Check spelling or domain features in registry.",
                    )
                )

    def _validate_validation(
        self,
        param: ValidationParam,
        idx: int,
        errors: List[ValidationErrorDetail],
        domain: str,
        schema_registry: Optional[SchemaRegistry],
        auto_register: bool = True,
    ) -> None:
        path = f"Constraints.ValidationParamList[{idx}]"
        if not param.ExpName:
            return

        # Check: Validation Operator must be list[list[str]] (2D)
        if not isinstance(param.Operator, list) or (param.Operator and not isinstance(param.Operator[0], list)):
            errors.append(
                ValidationErrorDetail(
                    code="validation_shape_invalid",
                    message="ValidationParamList Operator must be a 2D list (e.g. [['>=']]).",
                    location=f"{path}.Operator",
                    suggestion="Nest the validation operator list (e.g. list[list[str]]).",
                )
            )

        # Check: Validation Value must be list[list[list[str]]] (3D)
        if not self._is_3d_list(param.Value):
            errors.append(
                ValidationErrorDetail(
                    code="validation_value_shape_invalid",
                    message="ValidationParamList Value must be a 3D list (e.g. [[['4.5*SheetMetal.Thickness']]]).",
                    location=f"{path}.Value",
                    suggestion="Ensure validation value list matches triple-nested shape.",
                )
            )

        # Operator validation
        if isinstance(param.Operator, list):
            for inner in param.Operator:
                if isinstance(inner, list):
                    # Check range operator shape
                    if len(inner) == 2:
                        # Must have 2 value bounds
                        for val_branch in param.Value:
                            for bounds in val_branch:
                                if len(bounds) != 2:
                                    errors.append(
                                        ValidationErrorDetail(
                                            code="range_shape_invalid",
                                            message="Range operators require exactly 2 value bounds.",
                                            location=f"{path}.Value",
                                            suggestion="Provide exactly 2 range bounds matching [op1, op2].",
                                        )
                                    )
                    for op in inner:
                        if op and op not in ALLOWED_OPERATORS:
                            errors.append(
                                ValidationErrorDetail(
                                    code="unsupported_operator",
                                    message=f"Operator '{op}' is not supported.",
                                    location=f"{path}.Operator",
                                    suggestion="Normalize operator to standard symbol.",
                                )
                            )
                        if op == "ANY":
                            # Set membership check
                            # Value must be encoded as individual nested lists: [[['v1'], ['v2']]]
                            # E.g. len(val_branch) == count of choices, and each inner has len 1
                            for val_branch in param.Value:
                                for choice in val_branch:
                                    if len(choice) != 1:
                                        errors.append(
                                            ValidationErrorDetail(
                                                code="any_shape_invalid",
                                                message="Set membership ANY values must be split into single-element nested arrays.",
                                                location=f"{path}.Value",
                                                suggestion="Format set options as list of separate lists: [[['Steel'], ['Aluminium']]].",
                                            )
                                        )

        # Check units in value strings
        for val_branch in param.Value:
            for bounds in val_branch:
                for val in bounds:
                    if UNIT_PATTERN.search(val):
                        errors.append(
                            ValidationErrorDetail(
                                code="unit_in_value",
                                message=f"Value expression '{val}' contains explicit unit words.",
                                location=f"{path}.Value",
                                suggestion="Strip unit words (like degrees, mm, mm) from the raw values.",
                            )
                        )

        # Formula AllowedParams check
        if schema_registry:
            # Validate ExpName
            schema_errs = schema_registry.validate_exp_name(domain, param.ExpName, auto_register=auto_register)
            for err in schema_errs:
                if err.startswith("NEW_ATTRIBUTE_REGISTERED:"):
                    code = "new_attribute_registered"
                    msg = err.replace("NEW_ATTRIBUTE_REGISTERED: ", "")
                    sug = "Review Needed: Automatically registered new attribute into schema registry."
                else:
                    code = "schema_root_failed" if "Object" in err else "schema_attribute_failed"
                    msg = err
                    sug = "Check domain schema in registry."
                errors.append(
                    ValidationErrorDetail(
                        code=code,
                        message=msg,
                        location=f"{path}.ExpName",
                        suggestion=sug,
                    )
                )

            # Check that formula references are defined in AllowedParams
            allowed_set = set(param.AllowedParams)
            for val_branch in param.Value:
                for bounds in val_branch:
                    for val in bounds:
                        refs = extract_schema_refs(val)
                        for ref in refs:
                            if ref not in allowed_set:
                                errors.append(
                                    ValidationErrorDetail(
                                        code="allowed_params_missing",
                                        message=f"Formula reference '{ref}' in value expression '{val}' must be listed in AllowedParams.",
                                        location=f"{path}.AllowedParams",
                                        suggestion=f"Add '{ref}' to the AllowedParams list.",
                                    )
                                )
                            # Also validate that the ref path itself is schema-correct
                            ref_errs = schema_registry.validate_exp_name(domain, ref, auto_register=auto_register)
                            for r_err in ref_errs:
                                if r_err.startswith("NEW_ATTRIBUTE_REGISTERED:"):
                                    r_code = "new_attribute_registered"
                                    r_msg = r_err.replace("NEW_ATTRIBUTE_REGISTERED: ", "")
                                    r_sug = "Review Needed: Automatically registered new attribute into schema registry."
                                else:
                                    r_code = "schema_root_failed" if "Object" in r_err else "schema_attribute_failed"
                                    r_msg = f"Formula reference error: {r_err}"
                                    r_sug = "Ensure referenced variables in formulas are valid schema paths."
                                errors.append(
                                    ValidationErrorDetail(
                                        code=r_code,
                                        message=r_msg,
                                        location=f"{path}.Value",
                                        suggestion=r_sug,
                                    )
                                )

    def _validate_additional(
        self,
        param: AdditionalParam,
        idx: int,
        errors: List[ValidationErrorDetail],
        domain: str,
        schema_registry: Optional[SchemaRegistry],
    ) -> None:
        path = f"Constraints.AdditionalParamList[{idx}]"
        if not param.ExpName:
            return

        if schema_registry:
            schema_errs = schema_registry.validate_exp_name(domain, param.ExpName)
            for err in schema_errs:
                errors.append(
                    ValidationErrorDetail(
                        code="schema_root_failed" if "Object" in err else "schema_attribute_failed",
                        message=err,
                        location=f"{path}.ExpName",
                        suggestion="Check registry features.",
                    )
                )

    # ------------------------------------------------------------------
    # Rule-level logical validations
    # ------------------------------------------------------------------

    def _validate_rule_logic(
        self,
        rule: TaxonomyRule,
        errors: List[ValidationErrorDetail],
        domain: str,
        schema_registry: Optional[SchemaRegistry],
    ) -> None:
        # Distance rules must have Object1 and Object2 populated
        if rule.Feature1 == "Distance":
            if not rule.Object1 or not rule.Object2:
                errors.append(
                    ValidationErrorDetail(
                        code="distance_object_missing",
                        message="Rule specifies Feature1='Distance' but Object1 or Object2 is empty.",
                        location="Object1",
                        suggestion="Identify the two features/entities between which distance is being measured.",
                    )
                )

        # Module rules should not have Feature1/2 or Object1/2 populated
        if rule.RuleType == "Module":
            if rule.Feature1 or rule.Feature2 or rule.Object1 or rule.Object2:
                errors.append(
                    ValidationErrorDetail(
                        code="module_feature_conflict",
                        message="RuleType is 'Module' but feature/object entity fields are populated.",
                        location="Feature1",
                        suggestion="Clear Feature1, Feature2, Object1, and Object2 fields for module-level rules.",
                    )
                )

        # Validate root feature exists in domain
        if schema_registry and rule.RuleType == "Feature" and rule.Feature1:
            # Special case: Distance feature doesn't have to be explicitly in domain schema features
            # as it is a common cross-domain spatial feature.
            if rule.Feature1 != "Distance":
                features = schema_registry.get_features(domain)
                if rule.Feature1 not in features:
                    errors.append(
                        ValidationErrorDetail(
                            code="schema_root_failed",
                            message=f"Primary Feature1 '{rule.Feature1}' is not defined in domain '{domain}'.",
                            location="Feature1",
                            suggestion=f"Use one of the canonical features: {sorted(features.keys())}",
                        )
                    )

    def _validate_branch_alignment(
        self,
        constraints: Constraints,
        errors: List[ValidationErrorDetail],
    ) -> None:
        # Skip if either list is placeholder only
        cond_p = constraints.ConditionParamList[0]
        val_p = constraints.ValidationParamList[0]

        if not cond_p.ExpName or not val_p.ExpName:
            return

        cond_branch_count = len(cond_p.Value)
        val_val_count = len(val_p.Value)

        if cond_branch_count != val_val_count:
            errors.append(
                ValidationErrorDetail(
                    code="branch_alignment_failed",
                    message=(
                        f"Conditional branch alignment failed. Condition has {cond_branch_count} branches "
                        f"but Validation has {val_val_count} values."
                    ),
                    location="Constraints.ValidationParamList[0].Value",
                    suggestion="Align the array lengths so there is exactly one validation value per condition branch.",
                )
            )

    # Helper
    def _is_3d_list(self, val) -> bool:
        """Confirm if array is triple-nested (list of list of list of string)."""
        if not isinstance(val, list):
            return False
        if not val:
            return True  # empty list matches shape trivially
        first = val[0]
        if not isinstance(first, list):
            return False
        if not first:
            return True
        second = first[0]
        if not isinstance(second, list):
            return False
        return True
