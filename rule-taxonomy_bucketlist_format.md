# DFM Rule Taxonomy - BucketList Output Format

This taxonomy defines how DFM rules should be understood, classified, and emitted in the latest BucketList JSON output format. It is based on the `format1.json` schema and the BucketList example cases.

---

## 1. Purpose

A DFM rule is a manufacturing constraint that can be validated against a feature, object, part, module, or process parameter.

The latest output format is not the old flat `ExpName / Operator / Recom` format. The same rule logic now lives inside a nested `Constraints` object:

- `ValidationParamList` contains the actual pass/fail rule checks.
- `FilterParamList` limits which instances the rule applies to.
- `ConditionParamList` handles branch-specific thresholds.
- `AdditionalParamList` carries extra parameters to return/report.
- `UserParamList` carries user-configurable rule inputs.

---

## 2. Required Output Format

Every extracted rule must use this JSON structure:

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

All five constraint lists must be present. If a list is not applicable, keep the empty placeholder object.

---

## 3. Top-Level Fields

| Field | Meaning | Rule |
|:---|:---|:---|
| `Name` | Human-readable rule name | Derive from the rule intent. |
| `RuleCategory` | Manufacturing domain | Example: `Milling`, `Drilling`, `SheetMetal`, `Sheetmetal Forming`, `Assembly`, `Injection Molding`, `Turning`. |
| `Results` | Result behavior | Use `Validation` for pass/fail rules. |
| `RuleType` | Scope of rule | Use `Feature` for feature-instance checks; use `Module` for module/part/process-level checks. |
| `Feature1` | Primary feature or measurement type | Example: `Pocket`, `Hole`, `Fastener`, `Spoon`, `Distance`. Empty for module rules. |
| `Feature2` | Secondary feature type | Usually empty. |
| `Object1` | First measured object | Used mainly for distance/inter-object rules. |
| `Object2` | Second measured object | Used mainly for distance/inter-object rules. |
| `Constraints` | Rule logic container | Contains filter, condition, validation, additional, and user params. |

---

## 4. RuleType Logic

### Feature Rules

Use `RuleType = "Feature"` when the rule validates feature instances.

Examples:

- `Pocket.SideFaceAngle >= 13.0`
- `Hole.ThreadType = UNF`
- `Fastener.IsWasherPresent = Yes`
- `Distance.MinValue >= 2.0*SheetMetalForm.NominalThickness`

For feature rules:

- Populate `Feature1`.
- Keep `Object1` and `Object2` empty unless the feature is `Distance`.

### Module Rules

Use `RuleType = "Module"` when the rule validates part-level, module-level, process-level, or global values.

Examples:

- `PartBody.Material ANY Steel, Aluminium`
- `PartFace.Color = 0,0,255`
- `Turn.Body.Length/Turn.Body.MinOuterDiameter <= 8.0`

For module rules:

- Set `Feature1`, `Feature2`, `Object1`, and `Object2` to empty strings.

---

## 5. Constraint Lists

### 5.1 ValidationParamList

Use `ValidationParamList` for the actual rule checks.

Shape:

```json
{
  "ExpName": "Pocket.SideFaceAngle",
  "Operator": [[">="]],
  "Value": [[["13.0"]]],
  "AllowedParams": [""]
}
```

Use it for:

- Numeric bounds
- Ranges
- Equality checks
- Boolean `.Is` checks
- String and type checks
- Color checks
- Set membership
- Ratios
- Arithmetic expressions
- Hierarchical parameters

### 5.2 FilterParamList

Use `FilterParamList` when the rule applies only to a subset of instances, but the validation threshold does not branch.

Example:

```json
{
  "ExpName": "Fastener.FirstEngagedComp.Material",
  "Operator": ["="],
  "Value": ["Steel"]
}
```

Meaning: only fasteners whose first engaged component material is Steel are evaluated by the validation rule.

### 5.3 ConditionParamList

Use `ConditionParamList` when different conditions map to different validation values.

Example:

```json
{
  "ExpName": "Hole.IsBlind",
  "Operator": [["="]],
  "Value": [
    [["Yes"]],
    [["No"]]
  ]
}
```

The corresponding validation must use the same branch order:

```json
{
  "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
  "Operator": [["="]],
  "Value": [
    [["2.0"]],
    [["4.0"]]
  ],
  "AllowedParams": [""]
}
```

Meaning:

- If `Hole.IsBlind = Yes`, validate ratio equals `2.0`.
- If `Hole.IsBlind = No`, validate ratio equals `4.0`.

### 5.4 AdditionalParamList

Use `AdditionalParamList` for parameters that should be returned or reported, but are not pass/fail validations.

Example:

```json
{
  "ExpName": "Hole.DiameterAtBot"
}
```

Do not place a parameter in `ValidationParamList` unless the source text gives an operator and value for it.

### 5.5 UserParamList

Use `UserParamList` only for configurable user inputs. If the rule does not require user input, keep the empty placeholder object.

---

## 6. Operators

Use the exact operator strings expected by the latest format.

| Rule Meaning | JSON Operator | JSON Value Pattern |
|:---|:---:|:---|
| At least / minimum / no less than | `>=` | `[[["13.0"]]]` |
| At most / maximum / not exceed | `<=` | `[[["8.0"]]]` |
| Strictly greater than | `>` | `[[["0.5"]]]` |
| Strictly less than | `<` | `[[["1.2"]]]` |
| Equal to / is / check if | `=` | `[[["UNF"]]]` |
| Any of / one of / from list | `ANY` | `[[["Steel"], ["Aluminium"]]]` |

Boolean values should use `Yes` and `No`, not `True` and `False`, when the target parameter is an `.Is...` parameter.

Examples:

- `Hole.IsBlind = Yes`
- `Fastener.IsWasherPresent = Yes`
- `Pocket.IsBotChamfered = No`

---

## 7. Rule Logic Types

### Type 1: Plain Single Validation Expression

One feature or module parameter has one validation expression.

Example:

```text
The side face angle of the pocket should be at least 13.0 degrees.
```

Output logic:

```json
"RuleType": "Feature",
"Feature1": "Pocket",
"ValidationParamList": [
  {
    "ExpName": "Pocket.SideFaceAngle",
    "Operator": [[">="]],
    "Value": [[["13.0"]]],
    "AllowedParams": [""]
  }
]
```

### Type 2: Range Validation

Use one validation entry with two operators and two values.

Example:

```text
Spoon minimum height should be between 0.5 and 1.2 times sheet thickness.
```

Output logic:

```json
{
  "ExpName": "Spoon.Height",
  "Operator": [[">", "<"]],
  "Value": [[["0.5", "1.2"]]],
  "AllowedParams": [""]
}
```

### Type 3: Set Membership

Use `ANY` when the parameter must match one of a list of allowed values.

Example:

```text
Partbody material should be from the following list - Steel, Aluminium.
```

Output logic:

```json
{
  "ExpName": "PartBody.Material",
  "Operator": [["ANY"]],
  "Value": [[["Steel"], ["Aluminium"]]],
  "AllowedParams": [""]
}
```

### Type 4: Hierarchical Parameter

Use dot-path access when a parameter belongs to a nested object.

Example:

```text
Ensure fasteners are engaged with specific materials.
```

Output logic:

```json
{
  "ExpName": "Fastener.FirstEngagedComp.Material",
  "Operator": [["="]],
  "Value": [[["Steel"]]],
  "AllowedParams": [""]
}
```

### Type 5: Color Parameter

Use the color value expected by the downstream system, such as RGB text.

Example:

```text
In drilling, ensure partface colour is blue.
```

Output logic:

```json
{
  "ExpName": "PartFace.Color",
  "Operator": [["="]],
  "Value": [[["0,0,255"]]],
  "AllowedParams": [""]
}
```

### Type 6: Type, String, and Name Parameters

String-like parameters use equality.

Examples:

- `Hole.ThreadType = UNF`
- `Component.Name = xyz`

Output logic:

```json
{
  "ExpName": "Hole.ThreadType",
  "Operator": [["="]],
  "Value": [[["UNF"]]],
  "AllowedParams": [""]
}
```

### Type 7: Boolean `.Is` Parameter

Use `Yes` or `No`.

Example:

```text
Check if the holes are blind.
```

Output logic:

```json
{
  "ExpName": "Hole.IsBlind",
  "Operator": [["="]],
  "Value": [[["Yes"]]],
  "AllowedParams": [""]
}
```

### Type 8: Allowed Parameter Expression

When the value expression references another schema parameter, include that parameter in `AllowedParams`.

Example:

```text
Spoon minimum width should be at least 0.8 times sheet thickness.
```

Output logic:

```json
{
  "ExpName": "Spoon.Width",
  "Operator": [[">="]],
  "Value": [[["0.8*SheetMetal.Thickness"]]],
  "AllowedParams": ["SheetMetal.Thickness"]
}
```

### Type 9: Filter Plus Validation

Use `FilterParamList` for an applicability gate and `ValidationParamList` for the actual validation.

Example:

```text
Ensure washer is present for fasteners engaging with specific materials.
```

Output logic:

```json
"FilterParamList": [
  {
    "ExpName": "Fastener.FirstEngagedComp.Material",
    "Operator": ["="],
    "Value": ["Steel"]
  }
],
"ValidationParamList": [
  {
    "ExpName": "Fastener.IsWasherPresent",
    "Operator": [["="]],
    "Value": [[["Yes"]]],
    "AllowedParams": [""]
  }
]
```

### Type 10: Conditional Branching

Use `ConditionParamList` when different conditions map to different validation values.

Example:

```text
Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes.
```

Output logic:

```json
"ConditionParamList": [
  {
    "ExpName": "Hole.IsBlind",
    "Operator": [["="]],
    "Value": [
      [["Yes"]],
      [["No"]]
    ]
  }
],
"ValidationParamList": [
  {
    "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
    "Operator": [["="]],
    "Value": [
      [["2.0"]],
      [["4.0"]]
    ],
    "AllowedParams": [""]
  }
]
```

### Type 11: Additional Info Parameter

Use `AdditionalParamList` when the text asks to also check/report a parameter without a pass/fail bound.

Example:

```text
Also check hole diameter at bottom additionally for each instance.
```

Output logic:

```json
"AdditionalParamList": [
  {
    "ExpName": "Hole.DiameterAtBot"
  }
]
```

### Type 12: Distance Rule

Use `Feature1 = "Distance"` and populate `Object1` and `Object2`.

Example:

```text
Distance between hole and part edge should be at least 2.0 times sheet metal nominal thickness.
```

Output logic:

```json
{
  "RuleCategory": "Sheetmetal Forming",
  "RuleType": "Feature",
  "Feature1": "Distance",
  "Feature2": "",
  "Object1": "SimpleHole",
  "Object2": "Part Edge",
  "Constraints": {
    "ValidationParamList": [
      {
        "ExpName": "Distance.MinValue",
        "Operator": [[">="]],
        "Value": [[["2.0*SheetMetalForm.NominalThickness"]]],
        "AllowedParams": ["SheetMetalForm.NominalThickness"]
      }
    ]
  }
}
```

### Type 13: Module-Level Ratio

Use `RuleType = "Module"` for part/module-level expressions.

Example:

```text
The ratio of the length to the minimum outer diameter of turned parts does not exceed 8.0.
```

Output logic:

```json
{
  "RuleCategory": "Turning",
  "RuleType": "Module",
  "Feature1": "",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "ValidationParamList": [
      {
        "ExpName": "Turn.Body.Length/Turn.Body.MinOuterDiameter",
        "Operator": [["<="]],
        "Value": [[["8.0"]]],
        "AllowedParams": [""]
      }
    ]
  }
}
```

---

## 8. Feature and Object Rules

### Self-Feature Validation

If the rule checks an attribute of the feature itself:

- `Feature1` = feature name
- `Object1` = empty
- `Object2` = empty

Example:

- `Pocket.SideFaceAngle`
- `Hole.ThreadType`
- `Spoon.Width`

### Distance / Inter-Object Validation

If the rule checks distance between two entities:

- `Feature1 = "Distance"`
- `Object1` = first entity
- `Object2` = second entity
- `ValidationParamList[].ExpName = "Distance.MinValue"`

Example:

- `Object1 = "SimpleHole"`
- `Object2 = "Part Edge"`

### Module Validation

If the rule checks a part-level or module-level expression:

- `RuleType = "Module"`
- `Feature1 = ""`
- `Object1 = ""`
- `Object2 = ""`

Example:

- `PartBody.Material`
- `PartFace.Color`
- `Turn.Body.Length/Turn.Body.MinOuterDiameter`

---

## 9. Decision Guide

| Raw Rule Pattern | RuleType | Main List | Notes |
|:---|:---|:---|:---|
| One threshold on one feature attribute | `Feature` | `ValidationParamList` | Simple validation. |
| One threshold on module/part expression | `Module` | `ValidationParamList` | Keep feature/object fields empty. |
| Value must be within range | `Feature` or `Module` | `ValidationParamList` | Use two operators in one operator group. |
| Value must be one of a list | `Feature` or `Module` | `ValidationParamList` | Use `ANY`. |
| Boolean `.Is` state | `Feature` | `ValidationParamList` | Use `Yes` or `No`. |
| Applies only to selected instances | `Feature` | `FilterParamList` + `ValidationParamList` | Filter gates the validation. |
| Different thresholds for different cases | `Feature` | `ConditionParamList` + `ValidationParamList` | Branch orders must align. |
| Extra parameter to report | `Feature` or `Module` | `AdditionalParamList` | No pass/fail operator. |
| User-entered threshold | `Feature` or `Module` | `UserParamList` + `ValidationParamList` | Use only when configurable. |
| Distance between two objects | `Feature` | `ValidationParamList` | `Feature1 = Distance`; populate objects. |

---

## 10. Empty Placeholder Rules

When a constraint list is not used, keep the placeholder exactly in the latest format:

```json
"FilterParamList": [
  {
    "ExpName": "",
    "Operator": [""],
    "Value": [""]
  }
]
```

```json
"ConditionParamList": [
  {
    "ExpName": "",
    "Operator": [[""]],
    "Value": [[[""]]]
  }
]
```

```json
"ValidationParamList": [
  {
    "ExpName": "",
    "Operator": [[""]],
    "Value": [[[""]]],
    "AllowedParams": [""]
  }
]
```

```json
"AdditionalParamList": [
  {
    "ExpName": ""
  }
]
```

```json
"UserParamList": [
  {
    "ParamName": "",
    "DisplayName": "",
    "Value": [""],
    "MinValue": "",
    "MaxValue": ""
  }
]
```

---

## 11. Validation Checklist

Before accepting a generated rule:

1. Confirm the output is valid JSON.
2. Confirm all top-level fields are present.
3. Confirm `Constraints` contains all five required lists.
4. Confirm `RuleType` is `Feature` or `Module`.
5. Confirm module rules have empty feature/object fields.
6. Confirm feature rules have the correct `Feature1`.
7. Confirm distance rules use `Feature1 = "Distance"` and populate `Object1/Object2`.
8. Confirm every real validation has a non-empty `ExpName`, `Operator`, and `Value`.
9. Confirm filters are not confused with conditional branches.
10. Confirm conditional branch values align by position.
11. Confirm referenced variables inside value expressions appear in `AllowedParams`.
12. Confirm additional/report-only parameters are in `AdditionalParamList`, not `ValidationParamList`.
13. Confirm boolean `.Is` parameters use `Yes` or `No`.
14. Confirm set/list membership uses `ANY`.

