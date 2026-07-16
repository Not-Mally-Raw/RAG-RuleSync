# BucketList Rule Extraction Edge Cases

This document lists edge cases that can occur when extracting natural-language DFM rules into the latest BucketList JSON format.

---

## 1. Feature Rule vs Module Rule

Some rules mention part-level or module-level parameters, not feature instances.

Example:

```text
In sheetmetal module, the partbody material should be from the following list - Steel, Aluminium.
```

Expected:

```json
"RuleType": "Module",
"Feature1": "",
"Feature2": "",
"Object1": "",
"Object2": ""
```

Risk: the system may incorrectly set `RuleType = "Feature"` and `Feature1 = "PartBody"`.

---

## 2. Overfilled Object Fields

For normal feature attribute rules, `Object1` and `Object2` should usually be empty.

Example:

```text
The side face angle of the pocket should be at least 13.0 degrees.
```

Expected:

```json
"RuleType": "Feature",
"Feature1": "Pocket",
"Object1": "",
"Object2": ""
```

Risk: the system may duplicate the feature into `Object1`, such as `Object1 = "Pocket"`.

---

## 3. Distance Rules

Distance is a special feature type. The measured entities go into `Object1` and `Object2`.

Example:

```text
Distance between hole and part edge should be at least 2.0 times the sheet metal nominal thickness.
```

Expected:

```json
"RuleType": "Feature",
"Feature1": "Distance",
"Object1": "SimpleHole",
"Object2": "Part Edge"
```

Risk: the system may set `Feature1 = "Hole"` instead of `Feature1 = "Distance"`.

---

## 4. Range Rules

Rules using "between X and Y" require two operators and two values.

Example:

```text
For a spoon feature the minimum height should be between 0.5 and 1.2 times sheet thickness.
```

Expected:

```json
{
  "ExpName": "Spoon.Height",
  "Operator": [[">", "<"]],
  "Value": [[["0.5", "1.2"]]],
  "AllowedParams": [""]
}
```

Risk: the system may output a single `between` operator or capture only one bound.

---

## 5. Set Membership / ANY

Rules with a list of allowed values should use `ANY`.

Example:

```text
The partbody material should be from the following list - Steel, Aluminium.
```

Expected:

```json
{
  "ExpName": "PartBody.Material",
  "Operator": [["ANY"]],
  "Value": [[["Steel"], ["Aluminium"]]],
  "AllowedParams": [""]
}
```

Risk: the system may output `=` or old-style `in` instead of `ANY`.

---

## 6. Boolean `.Is` Rules

Boolean `.Is` parameters should use `Yes` or `No`.

Example:

```text
In drilling, check if the holes are blind.
```

Expected:

```json
{
  "ExpName": "Hole.IsBlind",
  "Operator": [["="]],
  "Value": [[["Yes"]]],
  "AllowedParams": [""]
}
```

Risk: the system may output `True`, `False`, `1`, or `0`.

---

## 7. Negative Boolean Rules

Negative or avoidance wording should map to `No`.

Example:

```text
Avoid flat bottom holes.
```

Expected:

```json
{
  "ExpName": "Hole.IsFlatBottom",
  "Operator": [["="]],
  "Value": [[["No"]]],
  "AllowedParams": [""]
}
```

Risk: the system may miss the negation and output `Yes`.

---

## 8. Filter vs Condition

Filters select applicable instances. Conditions create branches with different validation values.

Filter example:

```text
Ensure washer is present for fasteners engaging with specific materials.
```

Expected filter logic:

```json
"FilterParamList": [
  {
    "ExpName": "Fastener.FirstEngagedComp.Material",
    "Operator": ["="],
    "Value": ["Steel"]
  }
]
```

Condition example:

```text
Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes.
```

Expected condition logic:

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
]
```

Risk: the system may put branch conditions into `FilterParamList`, losing the mapping between condition and validation value.

---

## 9. Branch Value Alignment

For conditional rules, condition values and validation values must align by position.

Expected:

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

Meaning:

- `Yes` maps to `2.0`
- `No` maps to `4.0`

Risk: the system may extract both branches but swap the order.

---

## 10. AdditionalParamList vs ValidationParamList

Extra report-only parameters should not become validation checks.

Example:

```text
Also check hole diameter at bottom additionally for each instance.
```

Expected:

```json
"AdditionalParamList": [
  {
    "ExpName": "Hole.DiameterAtBot"
  }
]
```

Risk: the system may incorrectly place `Hole.DiameterAtBot` into `ValidationParamList` with an empty operator/value.

---

## 11. AllowedParams

If a validation value references another schema parameter, that parameter must be listed in `AllowedParams`.

Example:

```text
The minimum width should be at least 0.8 times sheet thickness.
```

Expected:

```json
{
  "ExpName": "Spoon.Width",
  "Operator": [[">="]],
  "Value": [[["0.8*SheetMetal.Thickness"]]],
  "AllowedParams": ["SheetMetal.Thickness"]
}
```

Risk: the system may generate the expression but forget to populate `AllowedParams`.

---

## 12. Hierarchical Parameters

Nested object paths must be preserved exactly.

Example:

```text
In an assembly, ensure fasteners are engaged with specific materials.
```

Expected:

```json
"ExpName": "Fastener.FirstEngagedComp.Material"
```

Risk: the system may simplify the path to `Fastener.Material`, which changes the rule meaning.

---

## 13. Color Parameters

Color values may need target-system encoding, not natural-language color names.

Example:

```text
In drilling, ensure partface colour is blue.
```

Expected:

```json
{
  "ExpName": "PartFace.Color",
  "Operator": [["="]],
  "Value": [[["0,0,255"]]],
  "AllowedParams": [""]
}
```

Risk: the system may output `"Blue"` instead of `"0,0,255"`.

---

## 14. String and Type Values

String-like values are valid rule values and should not be rejected.

Examples:

```text
In drilling, check if the hole's thread type is UNF.
In assembly module, check if the component's name is xyz.
```

Expected:

```json
{
  "ExpName": "Hole.ThreadType",
  "Operator": [["="]],
  "Value": [[["UNF"]]],
  "AllowedParams": [""]
}
```

Risk: the system may treat non-numeric values as invalid.

---

## 15. Category Spelling Variants

The examples may use inconsistent spelling or casing.

Examples:

```text
SheetMetal
Sheetmetal
Sheetmetal Forming
Injection Molding
```

Risk: the system may treat spelling variants as different domains.

Need: normalize domain names before final output.

---

## 16. Same Parameter, Different Scope

The same concept can appear at different scopes.

Examples:

- `PartBody.Material` is module-level.
- `Fastener.FirstEngagedComp.Material` is feature-level and hierarchical.

Risk: the system may rely only on the word "material" and choose the wrong `RuleType` or `ExpName`.

---

## 17. Multiple Validation Expressions

A single rule may contain multiple validations for the same feature.

Example:

```text
Card guide length should be at most 127.0 mm and opening angle should be at least 15.0 degrees.
```

Expected: one rule with multiple `ValidationParamList` entries.

Risk: the system may split it into two rules or keep only one validation expression.

---

## 18. Conditional Values With Same ExpName

The same validation expression may have different values under different conditions.

Example:

```text
Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes.
```

Expected: one validation expression with branched values.

Risk: the system may create two separate rules instead of one conditional rule.

---

## 19. Empty Placeholder Lists

The latest format requires all five constraint lists even when unused.

Risk: the system may omit unused lists like `UserParamList` or `AdditionalParamList`, causing schema mismatch.

Need: always emit placeholders for unused lists.

---

## 20. Unit and Text Cleanup

Natural language may include units or words that should not appear in numeric values.

Examples:

```text
13.0 degrees
127.0 mm
2.0 times sheet thickness
```

Expected values:

```text
13.0
127.0
2.0*SheetMetal.Thickness
```

Risk: the system may output `"13.0 degrees"` or `"127.0 mm"` in `Value`.

---

## 21. Object Name Normalization

Natural language object names may differ from schema names.

Examples:

```text
hole -> SimpleHole
part edge -> Part Edge
sheet metal nominal thickness -> SheetMetalForm.NominalThickness
sheet thickness -> SheetMetal.Thickness
```

Risk: the system may preserve raw text names instead of schema names.

---

## 22. Operator Direction

Natural language can invert comparison direction.

Examples:

```text
does not exceed 8.0 -> <= 8.0
at least 13.0 -> >= 13.0
minimum height between 0.5 and 1.2 -> > 0.5 and < 1.2
```

Risk: the system may choose the wrong operator direction.

---

## 23. Empty vs Missing Values

The format expects empty strings inside placeholder objects, not missing keys.

Risk: output may be valid JSON but invalid for the target schema if keys are omitted.

Need: emit every key exactly as specified in `format1.json`.

---

## 24. BucketList Case Coverage Checklist

Use these cases as required extraction tests:

- Feature validation with one numeric expression
- Feature validation with range expression
- Module material list with `ANY`
- Hierarchical feature parameter
- Color parameter
- Defined material list
- Defined type list
- Boolean `.Is` parameter
- String input parameter
- Expression using `AllowedParams`
- Filter plus validation
- Condition branches plus validation
- Additional info parameter
- Distance rule with `Object1/Object2`
- Module-level ratio rule

