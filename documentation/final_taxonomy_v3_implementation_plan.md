# Final Taxonomy V3 Implementation Plan

Created: 2026-07-15

## 1. Purpose

This plan consolidates the three teammate plans:

- `PLAN.md`
- `PLAN (1).md`
- `AST-redesign-plan.md`

The final implementation must add a new taxonomy-based formalization path that converts extracted DFM rule text into the final nested `format1 (1).json` schema.

Important vocabulary:

- Domain means manufacturing category, such as `SheetMetal`, `Drilling`, `Assembly`, `Injection Molding`, or `Tubing`.
- Bucket means structural/formalization type, such as simple validation, range rule, filter rule, distance rule, conditional rule, module rule, or nested condition rule.

The existing legacy `/process-rules` endpoint must remain unchanged.

## 2. Source Precedence

Use the sources in this order:

1. Latest taxonomy Markdown is authoritative for rule meaning, domain/category rules, bucket semantics, and final schema guidance.
2. Bucket-list Excel defines bucket families, keywords, and how each bucket maps into the schema fields.
3. DFX rule samples provide examples and prompt grounding.
4. Existing repo code is implementation context only, not a source of truth for the new output schema.

Runtime must not depend on files in `Downloads`. Required taxonomy knowledge should be distilled into repo-native config, prompts, and tests.

## 3. Common Decisions Kept From All Plans

The overlapping decisions from the three plans are:

- Add a new endpoint: `POST /process-rules-taxonomy`.
- Keep existing `/process-rules` behavior intact.
- Return one grouped response per input rule.
- Use the final nested `format1 (1).json` schema.
- Treat bucket classification as a first-class processing step.
- Use LLM-first generation for the nested taxonomy JSON.
- Validate deterministically after LLM generation.
- Attempt one LLM repair pass if validation fails.
- Reject legacy flat-only fields such as `Recom`, `ExpName1`, `Operator1`, and scalar `between` or `in`.
- Preserve multi-expression rules in one rule object when constraints share the same feature/object context.

## 4. Useful Unique Ideas Borrowed

From `AST-redesign-plan.md`, include:

- Pydantic models mirroring `format1 (1).json`.
- Deterministic array-shape validation for nested operator/value lists.
- Condition branch alignment checks.
- Attribute-level `ExpName` validation, not only root-object validation.
- AST support for ranges and set membership as validation helpers.
- Clear separation of applicability, condition, validation, additional, and user parameters.

From the other two plans, include:

- Repo-native taxonomy package under `dfm_rule_pipeline/taxonomy/`.
- New grouped API response shape.
- Bucket-to-schema mapping as the central implementation model.
- One-shot repair loop with validation errors supplied back to the LLM.

Do not adopt these parts as mandatory for v1:

- Replacing the whole current legacy pipeline.
- Reading external Excel/Markdown files at runtime.
- Fully replacing FAISS/cosine candidate extraction.
- Supporting new external domains such as `Cabling` or `VaccumInfusion` unless their schemas are added to repo config.

## 5. New Public API

Add `POST /process-rules-taxonomy`.

Request:

```json
{
  "rules": [
    {
      "rule_text": "Distance between bridges should be at least 4.5 times sheet thickness",
      "rule_type": "optional domain override"
    }
  ]
}
```

Response:

```json
[
  {
    "rule_text": "Distance between bridges should be at least 4.5 times sheet thickness",
    "status": "Success",
    "decision_code": "formalized",
    "domain": "SheetMetal",
    "bucket": "DistanceRule",
    "taxonomy_rules": [
      {
        "Name": "Bridge Spacing",
        "RuleCategory": "SheetMetal",
        "Results": "Validation",
        "RuleType": "Feature",
        "Feature1": "Distance",
        "Feature2": "",
        "Object1": "Bridge",
        "Object2": "Bridge",
        "Constraints": {
          "FilterParamList": [
            {
              "ExpName": "",
              "Operator": [""],
              "Value": [""]
            }
          ],
          "ConditionParamList": [
            {
              "ExpName": "",
              "Operator": [[""]],
              "Value": [[[""]]]
            }
          ],
          "ValidationParamList": [
            {
              "ExpName": "Distance.MinValue/SheetMetal.Thickness",
              "Operator": [[">="]],
              "Value": [[["4.5"]]],
              "AllowedParams": [""]
            }
          ],
          "AdditionalParamList": [
            {
              "ExpName": ""
            }
          ],
          "UserParamList": [
            {
              "ParamName": "",
              "DisplayName": "",
              "Value": [""],
              "MinValue": "",
              "MaxValue": ""
            }
          ]
        }
      }
    ],
    "validation_errors": []
  }
]
```

Status values:

- `Success`: at least one taxonomy rule passed validation.
- `Review Needed`: LLM failed, validation failed after repair, or schema paths could not be resolved.

Decision codes:

- `formalized`
- `validation_failed`
- `llm_failed`
- `repair_failed`
- `unsupported_bucket`
- `schema_path_failed`

## 6. Target Schema Contract

Every emitted taxonomy rule must follow this structure exactly:

```json
{
  "Name": "",
  "RuleCategory": "",
  "Results": "",
  "RuleType": "",
  "Feature1": "",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [""],
        "Value": [""]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [[""]],
        "Value": [[[""]]]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "",
        "Operator": [[""]],
        "Value": [[[""]]],
        "AllowedParams": [""]
      }
    ],
    "AdditionalParamList": [
      {
        "ExpName": ""
      }
    ],
    "UserParamList": [
      {
        "ParamName": "",
        "DisplayName": "",
        "Value": [""],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

Rules:

- All top-level keys are required.
- `Results` should normally be `Validation`.
- Empty or unused lists must contain the placeholder object shown above.
- Values should be strings, including numeric values, unless the final consuming schema later requires typed values.

## 7. Bucket Taxonomy

Implement these structural buckets.

| Bucket ID | Meaning | Main Schema Placement |
| --- | --- | --- |
| `FeatureSimpleValidation` | One feature, one pass/fail expression | `ValidationParamList` |
| `FeatureRangeValidation` | One feature with lower/upper range | `ValidationParamList.Operator = [[">", "<"]]` |
| `FeatureSetMembership` | One field must be one of allowed values | `ValidationParamList.Operator = [["ANY"]]` |
| `FeatureBooleanValidation` | Yes/no or true/false state | `ValidationParamList` |
| `FeatureTypedValueValidation` | Material, color, type, name, string, thread class | `ValidationParamList` |
| `FeatureAllowedParamExpression` | Validation value references another parameter | `ValidationParamList.AllowedParams` |
| `FilteredValidation` | Fixed applicability plus validation | `FilterParamList` and `ValidationParamList` |
| `ConditionalValidation` | If/then branching | `ConditionParamList` and branch-aligned `ValidationParamList.Value` |
| `AdditionalInfoValidation` | Validation plus report-only fields | `AdditionalParamList` |
| `DistanceRule` | Distance between two objects | `Feature1 = "Distance"`, `Object1`, `Object2` |
| `ModuleValidation` | Module/global rule with no feature instance | `RuleType = "Module"` |
| `MultiExpressionValidation` | Multiple checks on same feature/context | Multiple `ValidationParamList` entries |
| `NestedConditionalValidation` | Multiple condition dimensions or branch tables | Multiple aligned `ConditionParamList` entries |
| `MultiRuleDivergence` | One input contains independent rules | Return multiple objects inside `taxonomy_rules` |

## 8. Bucket Classification Flow

For each input `rule_text`:

1. Normalize text.
2. Detect domain.
   - Use explicit `rule_type` if provided and valid.
   - Otherwise classify from text using taxonomy domain rules.
   - Normalize aliases to latest taxonomy category strings.
   - Route Mill hole/drill rules to `Drilling`.
3. Detect candidate bucket.
   - Search for structural cues: distance, between/range, one-of/list, if/for/when branches, material filters, additional/report-only phrases, module-level terms, multiple constraints joined by `and`.
   - LLM may classify bucket, but validator must enforce bucket-schema consistency.
4. Build prompt context.
   - Include final schema skeleton.
   - Include bucket-specific schema rules.
   - Include domain feature schema.
   - Include 2 to 4 compact examples matching the bucket.
5. Ask LLM to emit JSON only.
   - Expected top-level: `bucket`, `domain`, `taxonomy_rules`.
6. Parse and validate.
7. If invalid, repair once.
8. Return grouped result.

## 9. Bucket-to-Schema Mapping Rules

### Simple validation

Example: `Pocket.SideFaceAngle >= 13.0`

- `FilterParamList`: placeholder
- `ConditionParamList`: placeholder
- `ValidationParamList`: one object
- `AdditionalParamList`: placeholder
- `UserParamList`: placeholder

### Range validation

Example: `Spoon.Height between 0.5 and 1.2`

- Do not emit scalar `between`.
- Emit:

```json
"Operator": [[">", "<"]],
"Value": [[["0.5", "1.2"]]]
```

### Set membership

Example: material is one of Steel, Aluminium.

- Do not emit scalar `in`.
- Emit:

```json
"Operator": [["ANY"]],
"Value": [[["Steel"], ["Aluminium"]]]
```

### Distance rule

Example: distance between hole and part edge.

- `RuleType = "Feature"`
- `Feature1 = "Distance"`
- `Object1 = "SimpleHole"` or mapped feature
- `Object2 = "PartEdge"`
- `ValidationParamList.ExpName = "Distance.MinValue"` or normalized ratio expression

### Module rule

Example: part material, print size, turn body ratio, machinability.

- `RuleType = "Module"`
- `Feature1`, `Feature2`, `Object1`, `Object2` usually empty
- Use module/global `ExpName` path in `ValidationParamList`

### Filter rule

Example: washer is present for fasteners engaging steel.

- Fixed applicability goes in `FilterParamList`.
- Actual pass/fail check goes in `ValidationParamList`.

### Conditional rule

Example: blind holes use value 2.0 and through holes use 4.0.

- Branch variable goes in `ConditionParamList`.
- `ValidationParamList.Value` must have the same branch count.

Example branch alignment:

```json
"ConditionParamList": [
  {
    "ExpName": "Hole.IsBlind",
    "Operator": [["="]],
    "Value": [[["Yes"]], [["No"]]]
  }
],
"ValidationParamList": [
  {
    "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
    "Operator": [["="]],
    "Value": [[["2.0"]], [["4.0"]]],
    "AllowedParams": [""]
  }
]
```

### Additional info rule

Example: also check/report bottom diameter.

- Report-only fields go to `AdditionalParamList`.
- They must not be treated as pass/fail validation unless the text gives an operator and value.

### Multi-expression rule

Example: card guide length and opening angle.

- Use one taxonomy rule object.
- Add multiple entries to `ValidationParamList`.

### Nested or multi-condition rule

Example: position tolerance based on diagonal length and hole diameter.

- Use multiple `ConditionParamList` entries.
- Their branch indexes must align with validation values.
- Validator must reject mismatched branch counts.

## 10. Proposed Package Design

Create:

```text
dfm_rule_pipeline/
  taxonomy/
    __init__.py
    models.py
    schema_factory.py
    domain_normalizer.py
    bucket_registry.py
    prompt_context.py
    llm_formalizer.py
    validator.py
    repair.py
    service.py
```

Responsibilities:

- `models.py`: Pydantic models matching final schema.
- `schema_factory.py`: placeholder object builders and default skeleton.
- `domain_normalizer.py`: alias normalization and latest `RuleCategory` strings.
- `bucket_registry.py`: bucket IDs, descriptions, cues, and schema placement rules.
- `prompt_context.py`: compact examples distilled from taxonomy, Excel, and DFX samples.
- `llm_formalizer.py`: first LLM JSON generation call.
- `validator.py`: deterministic schema, shape, branch alignment, operator, and `ExpName` validation.
- `repair.py`: one-shot LLM repair call.
- `service.py`: public function used by FastAPI endpoint.

## 11. Pydantic Model Requirements

Model the schema directly:

```python
class FilterParam(BaseModel):
    ExpName: str
    Operator: list[str]
    Value: list[str]

class ConditionParam(BaseModel):
    ExpName: str
    Operator: list[list[str]]
    Value: list[list[list[str]]]

class ValidationParam(BaseModel):
    ExpName: str
    Operator: list[list[str]]
    Value: list[list[list[str]]]
    AllowedParams: list[str]

class AdditionalParam(BaseModel):
    ExpName: str

class UserParam(BaseModel):
    ParamName: str
    DisplayName: str
    Value: list[str]
    MinValue: str
    MaxValue: str
```

Add top-level `TaxonomyRule` and grouped API response models.

## 12. Validation Requirements

The validator must check:

- JSON parse succeeded.
- Pydantic model parse succeeded.
- Required placeholder objects exist for unused lists.
- No legacy flat-only fields appear.
- Operator shapes are exact:
  - Filter: `list[str]`
  - Condition: `list[list[str]]`
  - Validation: `list[list[str]]`
- Value shapes are exact:
  - Filter: `list[str]`
  - Condition: `list[list[list[str]]]`
  - Validation: `list[list[list[str]]]`
- Range operators have two bounds.
- `ANY` values are encoded as one item per allowed value.
- Condition branch counts align with validation value branch counts.
- `ExpName` root object exists in the domain schema.
- `ExpName` attribute exists for the root object.
- Arithmetic expressions only reference allowed schema paths.
- `AllowedParams` includes referenced external parameters when validation values contain formulas.
- Distance rules include `Object1` and `Object2`.
- Module rules do not invent feature/object fields.

## 13. AST System Guidelines

The AST system is an internal compiler and validation layer. The final user-facing output is always the nested taxonomy JSON schema, not AST JSON.

The AST should help the system answer these questions:

- Is the expression syntactically valid?
- Which schema paths does the expression reference?
- Are all referenced objects and attributes valid for the detected domain?
- Does the expression use only supported operators?
- Does the expression map cleanly into `ValidationParamList`, `ConditionParamList`, `FilterParamList`, or `AllowedParams`?
- Are condition branches aligned with validation values?

### 13.1 AST Responsibilities

Use AST for:

- Parsing validation expressions such as `Distance.MinValue/SheetMetal.Thickness >= 4.5`.
- Parsing arithmetic values such as `2.0*SheetMetalForm.NominalThickness`.
- Validating range expressions mapped from `between`.
- Validating set membership expressions mapped from `ANY`.
- Extracting schema references from formulas.
- Checking branch alignment for conditional rules.
- Producing precise validation errors for LLM repair prompts.

Do not use AST for:

- Final output serialization.
- Replacing the final taxonomy schema.
- Deciding manufacturing domain by itself.
- Hallucinating missing schema attributes.
- Silently fixing invalid LLM output without recording validation errors.

### 13.2 Required AST Node Types

The current AST engine is too small for taxonomy v3. Add or support these node concepts:

```python
class SchemaRef:
    path: str
    root: str
    attribute: str

class Literal:
    value: str

class BinaryMathOp:
    operator: str  # +, -, *, /
    left: ASTNode
    right: ASTNode

class ComparisonOp:
    operator: str  # =, ==, !=, >, >=, <, <=
    left: ASTNode
    right: ASTNode

class BetweenOp:
    subject: ASTNode
    lower: ASTNode
    upper: ASTNode
    lower_operator: str  # usually > or >=
    upper_operator: str  # usually < or <=

class InSetOp:
    subject: ASTNode
    values: list[Literal]

class ConditionBranch:
    conditions: list[ComparisonOp | BetweenOp | InSetOp]
    validations: list[ComparisonOp | BetweenOp | InSetOp]
```

Implementation can use Pydantic models or dataclasses, but validation errors must include node path and rule context.

### 13.3 Supported Operators

Validation operators:

- `=`
- `==`
- `!=`
- `>`
- `>=`
- `<`
- `<=`
- `ANY`

Arithmetic operators:

- `+`
- `-`
- `*`
- `/`

Range mapping:

- Natural language `between X and Y` becomes `BetweenOp`.
- Final schema representation becomes `Operator: [[">", "<"]]` or the inclusive variant when the text says inclusive.
- `Value` must be `[[["X", "Y"]]]`.

Set membership mapping:

- Natural language `in`, `one of`, `from the list`, or `conform to recommended sizes` becomes `InSetOp`.
- Final schema representation becomes `Operator: [["ANY"]]`.
- `Value` must be `[[["A"], ["B"], ["C"]]]`.

Boolean mapping:

- `true/false`, `yes/no`, `present/absent`, `is blind`, `is flat bottom` should map to explicit string values preferred by the taxonomy examples, usually `"Yes"` / `"No"` or `"True"` / `"False"` depending on the feature convention.
- The validator should allow both forms initially but normalize to the convention used by the bucket examples.

### 13.4 Schema Path Validation

Every `ExpName` and every formula reference must be validated against the feature schema for the detected domain.

Validation steps:

1. Extract every path-like reference from expressions.
   - Examples: `Hole.TotalDepth`, `SheetMetal.Thickness`, `Fastener.FirstEngagedComp.Material`.
2. Split each reference into root and attributes.
3. Validate root object exists in the domain schema.
4. Validate direct attribute exists on the root object.
5. For nested object references, validate the first object path and allow configured nested aliases.
6. If the same reference is a known module/global path, validate through the domain normalizer.
7. If a path cannot be validated, return `schema_path_failed`.

Examples:

- `CardGuide.OpeningAngle` is valid in `SheetMetal`.
- `Spoon.Height/SheetMetal.Thickness` is valid if both `Spoon.Height` and `SheetMetal.Thickness` are known.
- `Hole.TotalDepth/Hole.DiameterAtTop` is valid in `Injection Molding`.
- `Hole.TotalDepth/Hole.DiameterAtTop` should fail in `Drilling` if `DiameterAtTop` does not exist there.

### 13.5 Expression Reference Extraction

The AST validator must extract references from:

- `ExpName`
- `ValidationParamList.Value` when values contain formulas
- `ConditionParamList.ExpName`
- `FilterParamList.ExpName`
- `AdditionalParamList.ExpName`
- `AllowedParams`

For arithmetic values, references must be mirrored in `AllowedParams` unless the expression is already in `ExpName`.

Example:

```json
{
  "ExpName": "Distance.MinValue",
  "Operator": [[">="]],
  "Value": [[["2.0*SheetMetalForm.NominalThickness"]]],
  "AllowedParams": ["SheetMetalForm.NominalThickness"]
}
```

### 13.6 Branch Alignment Validation

Conditional rules are valid only when condition branches and validation branches align.

For each `ConditionParamList` entry:

- Count branch cases in `Value`.
- Ensure corresponding operator groups are present.
- Ensure every `ValidationParamList.Value` has the same branch count when the rule is conditional.

Example valid branch count:

```json
"ConditionParamList": [
  {
    "ExpName": "Hole.IsBlind",
    "Operator": [["="]],
    "Value": [[["Yes"]], [["No"]]]
  }
],
"ValidationParamList": [
  {
    "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
    "Operator": [["="]],
    "Value": [[["2.0"]], [["4.0"]]],
    "AllowedParams": [""]
  }
]
```

This has two condition branches and two validation branches, so it is valid.

Reject:

- three condition branches with two validation values
- condition branch values but placeholder validation values
- nested condition tables where one condition dimension has fewer branch cases than the others

### 13.7 Bucket-to-AST Mapping

The AST layer should interpret each bucket as follows:

| Bucket | AST expectation |
| --- | --- |
| `FeatureSimpleValidation` | one `ComparisonOp` |
| `FeatureRangeValidation` | one `BetweenOp` |
| `FeatureSetMembership` | one `InSetOp` |
| `FeatureBooleanValidation` | one equality `ComparisonOp` |
| `FeatureAllowedParamExpression` | one `ComparisonOp` with formula references |
| `FilteredValidation` | filter `ComparisonOp` plus validation `ComparisonOp` |
| `ConditionalValidation` | one or more `ConditionBranch` objects |
| `AdditionalInfoValidation` | validation AST plus report-only schema refs |
| `DistanceRule` | comparison over `Distance.MinValue` or ratio expression |
| `ModuleValidation` | comparison over module/global schema path |
| `MultiExpressionValidation` | list of comparison/range/set nodes under one rule |
| `NestedConditionalValidation` | branch table with multiple condition dimensions |

### 13.8 Parser Strategy

Implement the AST parser in layers:

1. Lightweight expression reference scanner.
2. Operator detector for comparison, range, and membership.
3. Arithmetic expression parser for formulas in `ExpName` or `Value`.
4. Branch table parser for `ConditionParamList` plus `ValidationParamList`.

For the first implementation, the parser can be conservative:

- accept common arithmetic and comparison patterns
- reject ambiguous expressions with a clear validation error
- rely on one-shot LLM repair for malformed structures

Avoid broad `eval` or execution of generated expressions.

### 13.9 AST Validation Errors

Validation errors should be structured and repair-friendly:

```json
{
  "code": "schema_path_failed",
  "message": "Attribute DiameterAtTop is not valid for Hole in Drilling",
  "location": "taxonomy_rules[0].Constraints.ValidationParamList[0].ExpName",
  "suggestion": "Use Hole.Diameter for Drilling or switch RuleCategory to Injection Molding if the rule is molded-hole specific"
}
```

Required error codes:

- `json_parse_failed`
- `model_parse_failed`
- `legacy_field_detected`
- `operator_shape_invalid`
- `value_shape_invalid`
- `unsupported_operator`
- `range_shape_invalid`
- `any_shape_invalid`
- `branch_alignment_failed`
- `schema_root_failed`
- `schema_attribute_failed`
- `allowed_params_missing`
- `distance_object_missing`
- `module_feature_conflict`

### 13.10 AST Implementation Priority

Implement AST support in this order:

1. Expression reference extraction.
2. Schema path validation.
3. Range and `ANY` validation.
4. Branch alignment validation.
5. Arithmetic expression validation.
6. Optional evaluator support.

Do not block the first taxonomy endpoint on a full runtime evaluator. The first version needs validation and repair support, not CAD execution.

## 14. Prompting Strategy

LLM-first prompt must include:

- Final schema skeleton.
- Domain and bucket definitions.
- Bucket-specific placement rules.
- Allowed domain schema paths.
- Explicit "do not emit legacy fields" instruction.
- Exact output envelope:

```json
{
  "domain": "",
  "bucket": "",
  "taxonomy_rules": []
}
```

Prompt must ask for JSON only, no markdown.

Repair prompt must include:

- Original rule text.
- Invalid JSON.
- Deterministic validation errors.
- Same schema skeleton.
- Instruction to return corrected JSON only.

## 15. Test Plan

### Unit tests

- Schema skeleton generation.
- Placeholder object generation.
- Domain alias normalization.
- Bucket registry coverage.
- Operator normalization.
- Pydantic model parsing.
- Legacy field rejection.
- Branch alignment validation.
- `ExpName` root and attribute validation.

### Golden examples

Use these cases:

- Bridge spacing distance rule.
- Card guide multi-expression rule.
- Spoon range rule.
- Material `ANY` rule.
- Color validation rule.
- Hole thread type rule.
- Hole blind boolean rule.
- Component name string rule.
- Spoon allowed-parameter expression.
- Washer filter rule.
- Blind/through hole conditional rule.
- Additional hole bottom diameter rule.
- Sheetmetal forming distance rule.
- Turning module ratio rule.
- Tube fixed outer diameter filter plus bend radius.
- Uniform wall min/max.
- Drilling entry and exit angles.
- Multi-condition hole position tolerance.

### API tests

- Single input returns one grouped response.
- One input with independent clauses returns multiple `taxonomy_rules`.
- Invalid LLM output triggers one repair.
- Invalid after repair returns `Review Needed`.
- Existing `/process-rules` response remains unchanged.

### Verification commands

```bash
python -m compileall -q app.py core_v2 dfm_rule_pipeline tests
python -m pytest tests/test_taxonomy_schema.py -q
python -m pytest tests/test_taxonomy_validator.py -q
python -m pytest tests/test_taxonomy_api.py -q
python -m pytest tests/test_candidate_assembler.py -q
```

Run frontend build only if frontend files are changed.

## 16. Implementation Milestones

### Milestone 1: Schema and configs

- Add taxonomy package.
- Add Pydantic models.
- Add schema factory.
- Add domain normalizer.
- Add bucket registry.
- Add compact examples.

### Milestone 2: LLM formalizer and validator

- Add taxonomy prompt builder.
- Add LLM-first formalizer.
- Add deterministic validator.
- Add one-shot repair loop.

### Milestone 3: API integration

- Add `POST /process-rules-taxonomy`.
- Return grouped response per input.
- Keep legacy endpoint untouched.

### Milestone 4: Test coverage

- Add unit tests.
- Add golden tests.
- Add API tests.
- Validate legacy compatibility.

### Milestone 5: Optional UI mode

- Add frontend compile mode for taxonomy v2 only after backend behavior is stable.

## 17. Acceptance Criteria

Implementation is complete when:

- The new endpoint emits valid `format1 (1).json` shaped rules.
- All required bucket families are covered.
- Legacy endpoint still works.
- Deterministic validator catches malformed nesting, legacy fields, invalid operators, and bad schema paths.
- One-shot repair is attempted and reported clearly.
- Multi-rule input returns grouped `taxonomy_rules`.
- Golden examples pass.
