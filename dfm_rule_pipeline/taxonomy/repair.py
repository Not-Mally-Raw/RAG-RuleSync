"""
Targeted LLM Repair Module for DFM Taxonomy V3.

Analyzes validator error codes and compiles specific instructions for the
LLM to self-correct its flat extraction output.
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional, TYPE_CHECKING

from dfm_rule_pipeline.taxonomy.models import ExtractionResult, ValidationErrorDetail
from dfm_rule_pipeline.taxonomy.schema_registry import SchemaRegistry

if TYPE_CHECKING:
    from dfm_rule_pipeline.llm.client import LLMClient

logger = logging.getLogger("taxonomy.repair")

ERROR_REPAIR_TEMPLATES = {
    "schema_root_failed": (
        "In the ExpName variable path '{value}', the object '{root}' does not exist in domain '{domain}'. "
        "Valid features/objects you can use are: {options}. Choose the closest semantic match."
    ),
    "schema_attribute_failed": (
        "In the ExpName variable path '{value}', the attribute '{attr}' does not exist for object '{root}' in domain '{domain}'. "
        "Valid attributes for '{root}' are: {options}. Choose the correct attribute."
    ),
    "boolean_value_invalid": (
        "Boolean parameters (ending with .Is...) must use ONLY 'Yes' or 'No' as values. "
        "You outputted '{value}'. Change it to 'Yes' or 'No'."
    ),
    "allowed_params_missing": (
        "The validation value formula '{value}' references variable '{ref}', but '{ref}' was not listed in 'allowed_params'. "
        "Ensure '{ref}' is added to the 'allowed_params' array."
    ),
    "branch_alignment_failed": (
        "The condition has {cond_branches} branches, but validations has {val_branches} value groups. "
        "Ensure the validations list contains exactly one value group per condition branch."
    ),
    "unit_in_value": (
        "The value '{value}' contains explicit unit words (degrees, mm, etc.). "
        "Strip all unit words and return only the numeric part or mathematical formula, e.g. '13.0' or '4.5*SheetMetal.Thickness'."
    ),
    "distance_object_missing": (
        "Feature1 is 'Distance', but object1 or object2 is empty. For distance rules, "
        "you must identify the two physical features between which distance is measured."
    ),
    "module_feature_conflict": (
        "rule_type is 'Module' but feature or object fields are populated. "
        "For module-level rules, Feature1, Feature2, Object1, and Object2 must be empty strings."
    ),
    "unsupported_operator": (
        "The operator '{value}' is not supported. Use only standard operators: >=, <=, >, <, =, ANY."
    )
}


class TaxonomyRepair:
    """
    Orchestrates targeted self-repair loops for rule extraction failures.
    """

    def __init__(self, llm_client: LLMClient, schema_registry: SchemaRegistry):
        self._llm = llm_client
        self._registry = schema_registry

    def repair(
        self,
        rule_text: str,
        invalid_extraction: ExtractionResult,
        errors: List[ValidationErrorDetail],
        domain: str,
    ) -> Optional[ExtractionResult]:
        """
        Formulates a repair prompt with targeted instructions per error code
        and runs a single self-repair iteration.
        """
        logger.info(f"Triggering repair loop for rule. Errors: {[e.code for e in errors]}")
        
        # 1. Compile instructions for each validation error
        instructions = []
        for err in errors:
            instr = self._compile_instruction(err, domain)
            if instr:
                instructions.append(f"- ERROR CODE [{err.code}]: {instr}")
        
        if not instructions:
            logger.warning("No compileable error instructions found for repair")
            return None
        
        # 2. Serialize current invalid extraction
        invalid_json_str = invalid_extraction.model_dump_json(indent=2)
        
        # 3. Assemble repair prompt
        repair_prompt = f"""You previously extracted structured parameters from the following rule, but validation failed due to schema errors.

RULE TEXT:
"{rule_text}"

YOUR PREVIOUS INVALID EXTRACTION:
```json
{invalid_json_str}
```

REQUIRED CORRECTIONS:
{chr(10).join(instructions)}

Output a corrected FLAT JSON matching the ExtractionResult schema. Ensure all rules from the schema registry are strictly followed.
Return JSON ONLY. No explanations, no markdown blocks.
"""
        
        # 4. Invoke LLM for repair
        try:
            raw_response = self._llm.call(repair_prompt, json_mode=True)
            if not raw_response:
                return None
            
            cleaned = raw_response.strip()
            # Validate repaired JSON
            repaired_extraction = ExtractionResult.model_validate_json(cleaned)
            return repaired_extraction
        except Exception as e:
            logger.error(f"Repair attempt failed: {e}")
            return None

    def _compile_instruction(self, err: ValidationErrorDetail, domain: str) -> Optional[str]:
        """Maps an error code to a template and populates it with registry hints."""
        code = err.code
        if code not in ERROR_REPAIR_TEMPLATES:
            return err.message  # fallback to the original error message if no template
            
        template = ERROR_REPAIR_TEMPLATES[code]
        
        try:
            if code == "schema_root_failed":
                # E.g. "Pocket.SideFaceAngle" -> root="Pocket"
                path_val = err.message.split("'")[1] if "'" in err.message else ""
                root = path_val.split(".")[0] if "." in path_val else path_val
                valid_objs = sorted(self._registry.get_all_objects(domain))
                return template.format(value=path_val, root=root, domain=domain, options=str(valid_objs))
                
            elif code == "schema_attribute_failed":
                # E.g. "Attribute 'Weight' does not exist for 'Hole'..."
                path_val = err.message.split("'")[1] if "'" in err.message else ""
                root = path_val.split(".")[0] if "." in path_val else ""
                attr = path_val.split(".")[1] if "." in path_val else path_val
                valid_attrs = sorted(self._registry.get_attributes_for_object(domain, root) or [])
                return template.format(value=path_val, attr=attr, root=root, domain=domain, options=str(valid_attrs))
                
            elif code == "boolean_value_invalid":
                val = err.message.split("'")[1] if "'" in err.message else "True"
                return template.format(value=val)
                
            elif code == "allowed_params_missing":
                val = err.message.split("'")[1] if "'" in err.message else ""
                ref = err.message.split("'")[3] if len(err.message.split("'")) > 3 else ""
                return template.format(value=val, ref=ref)
                
            elif code == "unit_in_value":
                val = err.message.split("'")[1] if "'" in err.message else ""
                return template.format(value=val)
                
            elif code == "unsupported_operator":
                val = err.message.split("'")[1] if "'" in err.message else ""
                return template.format(value=val)
                
            # Dynamic template with no fields
            return template
            
        except Exception as ex:
            logger.warning(f"Failed to populate template for {code}: {ex}")
            return err.message
