"""
Deterministic Schema Assembler for DFM Taxonomy V3.

Transforms flat LLM extraction results into deeply nested
TaxonomyRule objects matching the format1 JSON schema.

The LLM only produces flat lists — this module handles ALL nesting:
- FilterParamList:     Operator list[str],           Value list[str]
- ConditionParamList:  Operator list[list[str]],      Value list[list[list[str]]]
- ValidationParamList: Operator list[list[str]],      Value list[list[list[str]]]
"""
from __future__ import annotations

import logging
import re
from typing import List, Set

from dfm_rule_pipeline.taxonomy.models import (
    ExtractionResult,
    FlatValidation,
    FlatCondition,
    FlatFilter,
    TaxonomyRule,
    Constraints,
    FilterParam,
    ConditionParam,
    ValidationParam,
    AdditionalParam,
    UserParam,
)

logger = logging.getLogger("taxonomy.assembler")

# Regex to extract schema path references from formula values
_SCHEMA_REF_RE = re.compile(r'([A-Z][a-zA-Z]+(?:\.[A-Z][a-zA-Z]+)+)')


class TaxonomyAssembler:
    """
    Assembles flat ExtractionResult into nested TaxonomyRule.
    
    This is a pure deterministic transformation — no LLM calls.
    """

    def assemble(self, extraction: ExtractionResult, schema_registry=None) -> TaxonomyRule:
        """
        Transform a flat extraction into a fully nested TaxonomyRule.
        
        Args:
            extraction: The flat intermediate result from the LLM.
            schema_registry: Optional SchemaRegistry for attribute ownership reconciliation.
            
        Returns:
            A nested TaxonomyRule ready for validation and API response.
        """
        # 0a. Reconcile feature and attribute ownership against SchemaRegistry
        if schema_registry:
            self._reconcile_attribute_ownership(extraction, schema_registry)

        # 0b. Auto-prefix bare exp_names that are missing Object prefix
        self._auto_prefix_exp_names(extraction)

        # 1. Build each constraint list
        validation_list = self._build_validations(extraction)
        condition_list = self._build_conditions(extraction)
        filter_list = self._build_filters(extraction)
        additional_list = self._build_additional(extraction)
        user_list = [UserParam.placeholder()]

        # 2. Handle branch alignment for conditional rules
        if condition_list and validation_list:
            validation_list = self._align_branches(
                condition_list, validation_list, extraction
            )

        # 3. Fill placeholders for empty lists
        if not validation_list:
            validation_list = [ValidationParam.placeholder()]
        if not condition_list:
            condition_list = [ConditionParam.placeholder()]
        if not filter_list:
            filter_list = [FilterParam.placeholder()]
        if not additional_list:
            additional_list = [AdditionalParam.placeholder()]

        # 4. Assemble top-level rule
        return TaxonomyRule(
            Name=extraction.name or "Unnamed Rule",
            RuleCategory=extraction.domain,
            Results="Validation",
            RuleType=extraction.rule_type,
            Feature1=extraction.feature1,
            Feature2=extraction.feature2,
            Object1=extraction.object1,
            Object2=extraction.object2,
            Constraints=Constraints(
                FilterParamList=filter_list,
                ConditionParamList=condition_list,
                ValidationParamList=validation_list,
                AdditionalParamList=additional_list,
                UserParamList=user_list,
            ),
        )

    # ------------------------------------------------------------------
    # Validation assembly
    # ------------------------------------------------------------------

    def _build_validations(self, extraction: ExtractionResult) -> List[ValidationParam]:
        """Build nested ValidationParamList from flat validations."""
        result = []
        
        for flat in extraction.validations:
            operators = flat.operators
            values = flat.values
            
            # Determine nesting pattern based on operator type
            if len(operators) == 1 and operators[0].upper() == "ANY":
                # Set membership: each value in its own inner list
                nested_op = [["ANY"]]
                nested_val = [[[v] for v in values]]
            elif len(operators) == 2:
                # Range: two operators, two values paired
                nested_op = [[operators[0], operators[1]]]
                nested_val = [[[values[0], values[1]]]] if len(values) >= 2 else [[[v for v in values]]]
            else:
                # Simple: single operator, single value
                nested_op = [[op] for op in operators] if operators else [[""]]
                if len(operators) == 1 and len(values) == 1:
                    nested_op = [[operators[0]]]
                    nested_val = [[[values[0]]]]
                else:
                    nested_val = [[[v] for v in values]] if values else [[[""]]]
            
            # Build AllowedParams
            allowed = self._collect_allowed_params(values, extraction.allowed_params)
            
            result.append(ValidationParam(
                ExpName=flat.exp_name,
                Operator=nested_op,
                Value=nested_val,
                AllowedParams=allowed if allowed else [""],
            ))
        
        return result

    # ------------------------------------------------------------------
    # Condition assembly
    # ------------------------------------------------------------------

    def _build_conditions(self, extraction: ExtractionResult) -> List[ConditionParam]:
        """Build nested ConditionParamList from flat conditions."""
        result = []
        
        for flat in extraction.conditions:
            # Detect range conditions: exactly 2 comparison operators form a range pair
            is_range = (
                len(flat.operators) == 2
                and all(op in {">", "<", ">=", "<="} for op in flat.operators)
            )

            if is_range:
                # Range condition: group the two operators as a single paired list
                # [">=" , "<="] -> [[">=" , "<="]]
                nested_op = [[flat.operators[0], flat.operators[1]]]
                # Each branch keeps its range bounds together as one inner list
                # [["0.0", "25.4"], ["25.4", "152.4"]] -> [[["0.0", "25.4"]], [["25.4", "152.4"]]]
                nested_val = [[[v for v in branch]] for branch in flat.branches]
            else:
                # Non-range (boolean, equality, set): wrap each operator individually
                nested_op = [[op] for op in flat.operators] if flat.operators else [[""]]
                # Each value in a branch gets its own inner list
                # [["Yes"], ["No"]] -> [[["Yes"]], [["No"]]]
                nested_val = [[[v] for v in branch] for branch in flat.branches]
            
            if not nested_val:
                nested_val = [[[""]]]
            
            result.append(ConditionParam(
                ExpName=flat.exp_name,
                Operator=nested_op,
                Value=nested_val,
            ))
        
        return result

    # ------------------------------------------------------------------
    # Filter assembly
    # ------------------------------------------------------------------

    def _build_filters(self, extraction: ExtractionResult) -> List[FilterParam]:
        """Build flat FilterParamList from flat filters."""
        result = []
        
        for flat in extraction.filters:
            # Filters stay FLAT — no double/triple nesting
            result.append(FilterParam(
                ExpName=flat.exp_name,
                Operator=[flat.operator] if flat.operator else [""],
                Value=[flat.value] if flat.value else [""],
            ))
        
        return result

    # ------------------------------------------------------------------
    # Additional assembly
    # ------------------------------------------------------------------

    def _build_additional(self, extraction: ExtractionResult) -> List[AdditionalParam]:
        """Build AdditionalParamList from additional ExpName strings."""
        result = []
        
        for exp_name in extraction.additional:
            if exp_name and exp_name.strip():
                clean = exp_name.strip()
                # Ignore raw sentence/equation dumps (containing '=', ' for ', or spaces)
                if "=" in clean or " for " in clean.lower() or " " in clean:
                    logger.warning(f"Discarding invalid raw text dump in additional: '{clean}'")
                    continue
                result.append(AdditionalParam(ExpName=clean))
        
        return result

    # ------------------------------------------------------------------
    # Branch alignment
    # ------------------------------------------------------------------

    def _align_branches(
        self,
        conditions: List[ConditionParam],
        validations: List[ValidationParam],
        extraction: ExtractionResult,
    ) -> List[ValidationParam]:
        """
        Ensure validation Value arrays are aligned with condition branches.
        
        If conditions have N branches, each validation should have N value groups.
        """
        if not conditions:
            return validations
        
        # Count branches from the first condition
        branch_count = len(conditions[0].Value)
        if branch_count <= 1:
            return validations
        
        aligned = []
        for val_param in validations:
            current_val_count = len(val_param.Value)
            
            if current_val_count == branch_count:
                # Already aligned
                aligned.append(val_param)
            elif current_val_count == 1:
                # Single value list in a single validation param
                inner_val_count = len(val_param.Value[0])
                if inner_val_count == branch_count:
                    # Flat extraction provided exactly one value per branch inside a single list:
                    # e.g., [[["2.0"], ["4.0"]]] -> split into [[["2.0"]], [["4.0"]]]
                    split_value = [[val_param.Value[0][i]] for i in range(branch_count)]
                    aligned.append(ValidationParam(
                        ExpName=val_param.ExpName,
                        Operator=val_param.Operator,
                        Value=split_value,
                        AllowedParams=val_param.AllowedParams,
                    ))
                else:
                    # Single value — replicate for each branch (e.g. same validation value applies to all branches)
                    aligned.append(ValidationParam(
                        ExpName=val_param.ExpName,
                        Operator=val_param.Operator,
                        Value=val_param.Value * branch_count,
                        AllowedParams=val_param.AllowedParams,
                    ))
            else:
                # Mismatch — keep as-is for validator to catch
                logger.warning(
                    f"Branch alignment mismatch: {branch_count} condition branches "
                    f"but {current_val_count} validation value groups for {val_param.ExpName}"
                )
                aligned.append(val_param)
        
        return aligned

    # ------------------------------------------------------------------
    # AllowedParams detection
    # ------------------------------------------------------------------

    def _collect_allowed_params(
        self,
        values: List[str],
        explicit_params: List[str],
    ) -> List[str]:
        """
        Auto-detect formula references in values and merge with explicit params.
        
        E.g., value "4.5*SheetMetal.Thickness" -> extracts "SheetMetal.Thickness"
        """
        refs: Set[str] = set()
        
        # Auto-detect from values
        for val in values:
            found = _SCHEMA_REF_RE.findall(val)
            refs.update(found)
        
        # Merge with explicitly provided params
        for param in explicit_params:
            if param and param.strip():
                refs.add(param.strip())
        
        return sorted(refs) if refs else []

    # ------------------------------------------------------------------
    # Dynamic Attribute & Feature Ownership Reconciliation
    # ------------------------------------------------------------------

    def _reconcile_attribute_ownership(self, extraction: ExtractionResult, registry) -> None:
        """
        Dynamically reconcile ExpName paths and Feature1 based on schema attribute ownership.
        
        If an exp_name refers to an attribute (e.g. EntryAngle, ExitAngle, TipAngle) that belongs
        uniquely to a specific Feature in that domain (e.g. Hole), we reconcile:
        - exp_name: Hole.EntryAngle
        - feature1: Hole
        """
        domain = extraction.domain
        if not domain:
            return

        features = registry.get_features(domain)
        if not features:
            return

        # Map attribute_name -> list of owning feature_names
        attr_to_owners = {}
        for feat_name, attrs in features.items():
            if feat_name in {"PartBody", "PartFace", "PartEdge", "PMI", "Thread"}:
                continue
            for attr in attrs:
                attr_to_owners.setdefault(attr, []).append(feat_name)

        def fix_path(path: str) -> tuple[str, str | None]:
            if not path or not path.strip():
                return path, None
            
            # Handle ratio paths (A/B)
            if "/" in path:
                parts = path.split("/")
                fixed_parts = []
                best_owner = None
                for p in parts:
                    fp, o = fix_path(p.strip())
                    fixed_parts.append(fp)
                    if o:
                        best_owner = o
                return "/".join(fixed_parts), best_owner

            parts = path.split(".", 1)
            attr = parts[1] if len(parts) > 1 else parts[0]

            owners = attr_to_owners.get(attr, [])
            if len(owners) == 1:
                right_owner = owners[0]
                new_path = f"{right_owner}.{attr}"
                return new_path, right_owner
            return path, None

        for v in extraction.validations:
            new_path, right_owner = fix_path(v.exp_name)
            v.exp_name = new_path
            if right_owner and extraction.rule_type == "Feature":
                extraction.feature1 = right_owner

        for c in extraction.conditions:
            new_path, right_owner = fix_path(c.exp_name)
            c.exp_name = new_path
            if right_owner and extraction.rule_type == "Feature" and not extraction.feature1:
                extraction.feature1 = right_owner

    # ------------------------------------------------------------------
    # Auto-prefix bare ExpName paths
    # ------------------------------------------------------------------

    def _auto_prefix_exp_names(self, extraction: ExtractionResult) -> None:
        """
        Auto-prefix bare attribute names (no dot) with the correct object.
        
        This is a generalizable defensive fix for when the LLM omits the
        Object prefix from an exp_name.  Rules:
        - If rule_type == 'Feature' and feature1 is set  -> prefix with feature1
        - If rule_type == 'Module'                        -> prefix with 'PartBody'
        - Ratio paths (containing '/') are handled per-segment
        - Already-prefixed paths (containing '.') are left untouched
        """
        prefix = self._infer_prefix(extraction)
        if not prefix:
            return

        for v in extraction.validations:
            v.exp_name = self._prefix_path(v.exp_name, prefix)
        for c in extraction.conditions:
            c.exp_name = self._prefix_path(c.exp_name, prefix)
        for f in extraction.filters:
            f.exp_name = self._prefix_path(f.exp_name, prefix)
        extraction.additional = [
            self._prefix_path(a, prefix) for a in extraction.additional
        ]

    @staticmethod
    def _infer_prefix(extraction: ExtractionResult) -> str:
        """Determine the default Object prefix from rule context."""
        if extraction.rule_type == "Feature" and extraction.feature1:
            return extraction.feature1
        if extraction.rule_type == "Module":
            return "PartBody"
        return ""

    @staticmethod
    def _prefix_path(exp_name: str, prefix: str) -> str:
        """Prefix a single exp_name if it is a bare attribute (no dot)."""
        if not exp_name or not exp_name.strip():
            return exp_name

        # Handle ratio paths (A/B) — prefix each segment independently
        if "/" in exp_name:
            segments = exp_name.split("/")
            prefixed = [
                TaxonomyAssembler._prefix_path(seg.strip(), prefix)
                for seg in segments
            ]
            return "/".join(prefixed)

        # Already has a dot — leave it alone
        if "." in exp_name:
            return exp_name

        # Bare attribute — apply prefix
        logger.info(f"Auto-prefixed bare ExpName '{exp_name}' -> '{prefix}.{exp_name}'")
        return f"{prefix}.{exp_name}"
