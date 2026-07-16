# Comprehensive DFM Rule Taxonomy

This document is the **single authoritative reference** for understanding, identifying, classifying, and formalizing Design for Manufacturability (DFM) rules. It is built from 89 real-world formalized examples across 10 manufacturing domains and the complete feature schema. Any LLM, pipeline stage, or human reviewer should consult this document before attempting rule extraction or formalization.

---

## Table of Contents
1. [What is a DFM Rule?](#1-what-is-a-dfm-rule)
2. [How to Identify a Rule in Raw Text](#2-how-to-identify-a-rule-in-raw-text)
3. [Core Components of a Formalized Rule (Schema)](#3-core-components-of-a-formalized-rule-schema)
4. [Rule Categories (Manufacturing Domains)](#4-rule-categories-manufacturing-domains)
5. [How to Identify the Domain Accurately](#5-how-to-identify-the-domain-accurately)
6. [Rule Structural Types (Classification by Complexity)](#6-rule-structural-types-classification-by-complexity)
7. [Operators: The Complete Set](#7-operators-the-complete-set)
8. [Expression Name (ExpName) Patterns](#8-expression-name-expname-patterns)
9. [Feature & Object Reference per Domain](#9-feature--object-reference-per-domain)
10. [Handling Applicability Constraints](#10-handling-applicability-constraints)
11. [Handling Multi-Rule Divergence from Single Text](#11-handling-multi-rule-divergence-from-single-text)
12. [Chain-of-Thought (CoT) Formalization Pipeline](#12-chain-of-thought-cot-formalization-pipeline)
13. [Current Pipeline Architecture & Improvement Opportunities](#13-current-pipeline-architecture--improvement-opportunities)
14. [Complete Worked Examples](#14-complete-worked-examples)

---

## 1. What is a DFM Rule?

A DFM rule is a **qualitative and quantitive manufacturing constraint** applied to a geometric feature, material property, or process parameter that ensures a part can be manufactured reliably, cost-effectively, and within quality tolerances.

**Key properties of a DFM rule:**
- It constrains a **measurable attribute** (dimension, angle, ratio, boolean state)
- It constraints **qualitative and quantitive**()
- It specifies a **limit or threshold** (minimum, maximum, range, equality, set membership)
- It applies to **one or more physical features** on a part (holes, bends, ribs, walls, etc.)
- It belongs to a specific **manufacturing domain** (Sheet Metal, Milling, Injection Molding, etc.)

**What is NOT a DFM rule:**
- General design advice with or without quantifiable bounds (e.g., "Consider weight reduction")
- Material selection guidance without threshold constraints
- Process descriptions (e.g., "The part is manufactured using CNC milling")

---

## 2. How to Identify a Rule in Raw Text

When scanning raw text from a document, look for these **identification triggers**:

### 2.1 Linguistic Triggers
| Trigger Type | Examples |
|:---|:---|
| **Modal verbs** | "should be", "must be", "shall be", "is recommended" |
| **Imperatives** | "Ensure", "Avoid", "Check", "Use" |
| **Comparative phrases** | "at least", "at most", "greater than", "less than", "no more than", "not exceed" |
| **Equality constraints** | "should be set to", "must equal", "conform to" |
| **Range expressions** | "between X and Y", "from X to Y" |
| **Set membership** | "conform to the recommended sizes: ...", "one of the preferred materials" |

`Add a trigger for colours and type of material or thread or etc.`
### 2.2 Quantitative Triggers
- **Explicit dimensions**: "2.0 mm", "15.0 degrees", "0.254 units"
- **Relative multipliers**: "4.5 times sheet thickness", "0.8 times the nominal thickness"
- **Ratios**: "depth to diameter ratio", "height to outer diameter ratio"
- **Percentages**: "75% of the drill depth"
- **Boolean states**: "is present", "is sharp", "is flat bottom"

### 2.3 Structural Triggers
- Found in lists, tables, or sections titled "Guidelines", "Constraints", "Design Rules", or "Parameters"
- Often follow a pattern: `[Feature] should be [comparison] [value] [optional: relative to another feature]`

### 2.4 Real Examples from the Rule Corpus

| Raw Text | Why it IS a rule |
|:---|:---|
| "Distance between bridges should be at least 4.5 times sheet thickness" | Modal verb + comparison + relative multiplier |
| "Avoid flat bottom holes" | Imperative + boolean constraint |
| "Ensure minimum clearance between components is at least 0.1 units" | Imperative + comparison + explicit dimension |
| "Thread sizes conform to the recommended standard sizes: 1-64 UNC, 1-72 UNF, 2-56 UNC" | Set membership constraint |

---

## 3. Core Components of a Formalized Rule (Schema)

Every formalized DFM rule follows the updated JSON schema from `format1 (1).json`. Each top-level field MUST be present. Populate unavailable scalar fields with an empty string `""`; keep empty constraint lists as one empty placeholder object matching the schema.

### 3.1 The Schema Structure

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
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### 3.2 Component Definitions

| Component | Required? | Description | How to Populate |
|:---|:---:|:---|:---|
| **Name** | Yes | Concise human-readable rule name | Derive from rule intent, e.g., `Bridge Spacing`, `Minimum Bend Radius` |
| **RuleCategory** | Yes | Manufacturing domain | Use the canonical domain strings in Section 4 |
| **Results** | Yes | Rule outcome/action | Use `Validation` for standard DFM validation rules |
| **RuleType** | Yes | Rule scope | Use `Feature` when validating a feature, distance, clearance, PMI, thread, etc.; use `Module` for module-level checks with no feature instance |
| **Feature1** | Yes | Primary feature or measurement type | `Distance`, `Bend`, `Boss`, `Rib`, `Hole`, `PMI`, `Thread`, etc.; empty for module-level checks |
| **Feature2** | Yes | Secondary feature type | Populate only when two different feature types interact; otherwise `""` |
| **Object1** | Yes | First physical entity for distance/interaction rules | `Bridge`, `Cutout`, `Bend`, `PartEdge`, `Component`, etc.; empty when the feature itself is validated |
| **Object2** | Yes | Second physical entity for distance/interaction rules | Populate for inter-feature measurements; otherwise `""` |
| **Constraints.FilterParamList** | Yes | Fixed applicability filters used to select candidate instances | Shallow arrays: `Operator: ["="]`, `Value: ["Steel"]` |
| **Constraints.ConditionParamList** | Yes | Branching conditions that align with branch-specific validation values | Nested arrays: `Operator: [["="]]`, `Value: [[["Yes"]], [["No"]]]`| `Operator: [[">","<"]] , Value: [[["4","6"]]]` | `Operator: [["ANY"]], Value: [[["Steel"],["Aluminium"]]]` |
| **Constraints.ValidationParamList** | Yes | Actual validation expressions and limits | Nested arrays: `Operator: [[">="]]`, `Value: [[["4.5"]]]`; include `AllowedParams` |
| **Constraints.AdditionalParamList** | Yes | Extra attributes to return/report but not validate | Only `ExpName` is required |
| **Constraints.UserParamList** | Yes | Runtime user inputs available to the rule | Include `ParamName`, `DisplayName`, `Value`, `MinValue`, `MaxValue` |

### 3.3 Constraint List Semantics

**FilterParamList** is for fixed preselection. Example: validate only fasteners whose first engaged component material is steel.

**ConditionParamList** is for branching. Each condition case must line up by index with the corresponding validation `Value` case. Example: `Hole.IsBlind = Yes` maps to a ratio value of `2.0`, and `Hole.IsBlind = No` maps to `4.0`.

**ValidationParamList** contains the metric being checked. Multiple validation entries replace the old numbered suffix pattern.

**AdditionalParamList** requests extra data to be returned per instance. It does not define pass/fail.

**UserParamList** is for parameters supplied at runtime, such as configurable thresholds or display names.

### 3.4 Operator and Value Nesting Rules

Use the array shapes from `format1 (1).json` exactly:

| List | Operator Shape | Value Shape | Example |
|:---|:---|:---|:---|
| `FilterParamList` | `["="]` | `["Steel"]` | One fixed filter value |
| `ConditionParamList` | `[["="]]` | `[[["Yes"]], [["No"]]]` | Two branch cases |
| `ValidationParamList` | `[[">="]]` | `[[["4.5"]]]` | One validation limit |
| `ValidationParamList` with range | `[[">", "<"]]` | `[[["0.5", "1.2"]]]` | Replacement for old `between` |
| `ValidationParamList` with set membership | `[["ANY"]]` | `[[["Steel"], ["Aluminium"]]]` | Replacement for old `in` / `any` |

### 3.5 When Feature1 vs Object1 Differ

- **Feature1 = Distance**: the measurement type is distance. `Object1` and `Object2` specify what the distance is measured between.
  - Example: `Feature1=Distance, Object1=Bridge, Object2=Bridge`
  - Example: `Feature1=Distance, Object1=Emboss, Object2=Cutout`
- **Feature1 = Boss**: the feature itself is the boss. `Object1` and `Object2` are `""`.
- **Feature1 = Clearance**: use this special measurement type for assembly clearances, with objects such as `Component` and `Component`.

### 3.6 Multi-Expression Rules

A single formalized rule can have multiple validation entries when all constraints apply to the same feature or interaction. Example: card guide length and opening angle stay in one rule because both validate `CardGuide`.

```json
{
  "Name": "Card Guide Parameters",
  "RuleCategory": "SheetMetal",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "CardGuide",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "CardGuide.Length",
        "Operator": [
          [
            "<="
          ]
        ],
        "Value": [
          [
            [
              "127.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "CardGuide.OpeningAngle",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "15.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### 3.7 Numbered ExpName Variants Are Deprecated

Do not use numbered field suffixes for paired constraints. In the new schema, paired or numbered constraints are separate objects inside `ValidationParamList`.

```json
{
  "Name": "Thickness Check",
  "RuleCategory": "General",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Wall",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Wall.MinThickness",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "5.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "Wall.MaxThickness",
        "Operator": [
          [
            "<="
          ]
        ],
        "Value": [
          [
            [
              "10.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

## 4. Rule Categories (Manufacturing Domains)

There are **10 primary manufacturing domains** plus 2 sub-domains. In the updated JSON schema, use the latest `RuleCategory` strings from the BucketList examples. Older taxonomy strings and spacing variants should be normalized before emitting final JSON.

| Domain Key | Latest RuleCategory String | Old Canonical / Accepted Aliases | Description |
|:---|:---|:---|:---|
| SheetMetal | `SheetMetal` | `Sheet Metal`, `Sheetmetal` | Bending, punching, forming of sheet metal parts |
| SMForm | `Sheetmetal Forming` | `Sheet Metal Forming`, `SheetMetalForm`, `SMForm` | Press-forming specific rules |
| Additive | `Additive Manufacturing` | `Additive` | 3D printing / additive processes |
| Assembly | `Assembly` | `Assembly` | Multi-component assembly constraints |
| DieCasting | `Die Casting` | `DieCasting`, `Casting` | Die casting process rules |
| InjectionMolding | `Injection Molding` | `InjectionMolding`, `Molding` | Plastic injection molding |
| Mill | `Milling` | `Mill` | CNC milling pocket, fillet, surface, and machinability rules |
| Drill | `Drilling` | `Mill` when the rule is hole/drill-specific | Hole, thread, drill-depth, entry/exit angle, and hole tolerance rules |
| Turn | `Turning` | `Turn` | Lathe / turning operations |
| Tubing | `Tubing` | `Tube`, `Pipe` | Tube bending and routing |
| General | `General` | `Model`, cross-domain rule | Cross-domain rules such as PMI, threads, materials |

**Normalization rule:** emit only the latest `RuleCategory` string in final JSON. Use aliases only during extraction/classification.

**IMPORTANT: The Mill domain produces TWO different latest `RuleCategory` strings:**
- `Milling` for pocket, fillet, surface, machinability, and milling-operation rules.
- `Drilling` for hole-related rules, including hole diameter, drill depth, thread depth, flat-bottom holes, entry/exit angles, and hole-position tolerance.

---

## 5. How to Identify the Domain Accurately

### 5.1 Keyword-Based Domain Detection

| Domain | Primary Keywords | Secondary Keywords |
|:---|:---|:---|
| **Sheet Metal** | sheet thickness, bend radius, flange, curl, rolled hem, bridge, emboss, gusset, cutout, louver, spoon, card guide, extruded form | SheetMetal.Thickness |
| **Sheet Metal Forming** | sheet metal nominal thickness, SMFace, forming | SheetMetalForm.NominalThickness |
| **Additive** | print size, overhang, infill, layer height, sharp edges (part), supported wall, unsupported wall | Additive.PrintSize |
| **Assembly** | clearance between components, fastener, washer, bolt, shank length, thread pitch, engagement | Clearance.MinValue, Fastener |
| **Die Casting** | mold wall, draft angle (casting), boss (casting), rib (casting), nominal thickness (casting) | PartBody.NominalThickness |
| **Injection Molding** | draft angle (molding), cored hole, lip, boss (molding), rib (molding), IMFace | InjectionMolding.NominalThickness |
| **Milling** | pocket, side face angle, fillet on top edges, bottom chamfer, machinability, surface finish | Pocket.SideFaceAngle, Mill.Machinability |
| **Drilling** | hole diameter, hole depth, flat bottom hole, thread depth, drill depth, partial hole, wrap angle | Hole.TotalDepth, Hole.DrillDepth |
| **Turning** | turned parts, bored hole, relief, outer diameter (turning), internal corner radius | Turn.Body, BoredHole, TurnCorner |
| **Tubing** | tube, pipe, bend radius (tube), overlap length, clearance between tubes, common radius | Tube.OuterDiameter, Tube.IsUniformBendRadius |
| **General** | PMI, thread size, thread class, thread unit, preferred materials, wall thickness (generic) | PMI.IsAttached, Thread.Size, PartBody.Material |


### 5.2 Disambiguation Rules

Some features appear in MULTIPLE domains (e.g., Boss exists in DieCasting AND InjectionMolding, Hole exists in Drilling AND InjectionMolding AND Additive). Use these disambiguation rules:

1. **If the text mentions "mold" or "molding" or "draft angle for ribs/bosses"** → Injection Molding
2. **If the text mentions "die" or "casting" or "mold wall"** → Die Casting
3. **If the text mentions "sheet thickness" or SM-specific features (flange, hem, bridge, emboss)** → Sheet Metal
4. **If the text mentions "pocket" or "machining" or "milling"** → Milling
5. **If the text mentions "hole" with "drill depth" or "entry/exit angle"** → Drilling (under Mill)
6. **If the text mentions "tube" or "pipe" or "bend" in tubing context** → Tubing
7. **If the text mentions "turned parts" or "lathe" or "bored hole"** → Turning
8. **If the text mentions "print size" or "3D printing" or "additive"** → Additive
9. **If the text mentions "assembly" or "fastener" or "component clearance"** → Assembly
10. **If the text mentions "PMI" or "thread" generically or "preferred materials"** → General

### 5.3 The Thickness Variable is Domain-Specific

Each domain has its own "thickness" or "nominal thickness" variable. This is CRITICAL for formalization:

| Domain | Thickness Variable |
|:---|:---|
| Sheet Metal | `SheetMetal.Thickness` |
| Sheet Metal Forming | `SheetMetalForm.NominalThickness` |
| Die Casting | `PartBody.NominalThickness` |
| Injection Molding | `InjectionMolding.NominalThickness` |
| Milling | `PartBody.NominalThickness` |
| Turning | `PartBody.NominalThickness` |
| General | `PartBody.NominalThickness` |

---

## 6. Rule Structural Types (Classification by Complexity)

The old flat schema represented every structural type with `ValidationParamList`. The updated schema represents the same rule families through `Constraints`, especially `ValidationParamList`, `FilterParamList`, and `ConditionParamList`.

### Type 1: Simple Single-Expression Rule

**Pattern:** one validation expression, one operator group, one value group.

**Example 1 (Bridge Spacing):**
```json
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
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Distance.MinValue/SheetMetal.Thickness",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "4.5"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Type 2: Multi-Expression Rule (Same Feature, Multiple Constraints)

**Pattern:** multiple `ValidationParamList` entries under the same top-level feature/object context.

**Example 2 (Card Guide Parameters):**
```json
{
  "Name": "Card Guide Parameters",
  "RuleCategory": "SheetMetal",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "CardGuide",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "CardGuide.Length",
        "Operator": [
          [
            "<="
          ]
        ],
        "Value": [
          [
            [
              "127.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "CardGuide.OpeningAngle",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "15.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

**Example 19 (Spoon Parameters, including the old `between` case):**
```json
{
  "Name": "Recommended Spoon Parameters",
  "RuleCategory": "SheetMetal",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Spoon",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Spoon.FlangeWidth/SheetMetal.Thickness",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "0.8"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "Spoon.Length/SheetMetal.Thickness",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "10.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "Spoon.Height/SheetMetal.Thickness",
        "Operator": [
          [
            ">",
            "<"
          ]
        ],
        "Value": [
          [
            [
              "0.5",
              "1.2"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Type 3: Deprecated Numbered Multi-Expression Rule

The old schema used `numbered validation suffixes` and `numbered validation suffixes`. In the updated schema, use separate validation entries.

**Example 46 (Thickness Check):**
```json
{
  "Name": "Thickness Check",
  "RuleCategory": "General",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Wall",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Wall.MinThickness",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "5.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "Wall.MaxThickness",
        "Operator": [
          [
            "<="
          ]
        ],
        "Value": [
          [
            [
              "10.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Type 4: Boolean State Rule

**Pattern:** `.Is...` expression with equality to a boolean-like value. Preserve the value convention used by the consuming system (`Yes`/`No`), but keep it nested as a string.

**Example 78 (Flat Bottom Holes):**
```json
{
  "Name": "Avoid Flat Bottom Holes",
  "RuleCategory": "Drilling",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Hole",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Hole.IsFlatBottom",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "No"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Type 5: Set Membership Rule

**Pattern:** old `in` or `any` becomes `Operator: [["ANY"]]`. Each allowed value is its own inner value item.

**Example 42 (Thread Sizes):**
```json
{
  "Name": "Recommended Standard Thread Sizes",
  "RuleCategory": "General",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Thread",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Thread.Size",
        "Operator": [
          [
            "ANY"
          ]
        ],
        "Value": [
          [
            [
              "1-64 UNC"
            ],
            [
              "1-72 UNF"
            ],
            [
              "2-56 UNC"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Type 6: Filtered Applicability Rule

**Pattern:** fixed applicability belongs in `FilterParamList`; validations still live in `ValidationParamList`.

**Example 18 (Material-Specific Flange Parameters):**
```json
{
  "Name": "Recommended Flange Parameters",
  "RuleCategory": "SheetMetal",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Flange",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "PartBody.Material",
        "Operator": [
          "="
        ],
        "Value": [
          "6061-T6"
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "SheetMetal.Thickness",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "2.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "Flange.Radius",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "1.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "Flange.Length",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "6.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Type 7: Conditional Branch Rule

**Pattern:** branch values in `ConditionParamList` align with branch values in `ValidationParamList` by index.

**Example 60 (Blind vs Through Hole Ratio):**
```json
{
  "Name": "Recommended Ratio of Hole Depth to Diameter",
  "RuleCategory": "Injection Molding",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Hole",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "Hole.IsBlind",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "Yes"
            ]
          ],
          [
            [
              "No"
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "2.0"
            ]
          ],
          [
            [
              "4.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Type 8: Nested / Multi-Level Conditional Rule

**Pattern:** use multiple `ConditionParamList` entries when a validation value depends on several condition dimensions. For ranges, encode the operator list as paired comparisons such as `[[">", "<="]]` with paired values.

**Example 84 (Line Profile Tolerance based on Part Size):**
```json
{
  "Name": "Recommended Line Profile Tolerance Based on Part Size",
  "RuleCategory": "Milling",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "PMI",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "PartBody.TightBoxDiagonalLength",
        "Operator": [
          [
            ">",
            "<="
          ]
        ],
        "Value": [
          [
            [
              "0.0",
              "25.4"
            ]
          ],
          [
            [
              "25.4",
              "152.4"
            ]
          ],
          [
            [
              "152.4",
              "2540.0"
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "PMI.ProfileOfLine",
        "Operator": [
          [
            "<="
          ]
        ],
        "Value": [
          [
            [
              "0.0508"
            ]
          ],
          [
            [
              "0.1016"
            ]
          ],
          [
            [
              "0.1524"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

## 7. Operators: The Complete Set

Operators must use the JSON array shape required by the target constraint list. Do not emit legacy scalar range or set-membership operators.

| Logical Meaning | FilterParamList Encoding | Condition/Validation Encoding | Value Encoding | Example |
|:---|:---|:---|:---|:---|
| Greater than or equal to | `[">="]` | `[[">="]]` | Filter: `["4.5"]`; Validation: `[[["4.5"]]]` | minimum spacing |
| Less than or equal to | `["<="]` | `[["<="]]` | `[[["127.0"]]]` | maximum length |
| Greater than | `[">"]` | `[[">"]]` | `[[["25.4"]]]` | lower open bound |
| Less than | `["<"]` | `[["<"]]` | `[[["1.2"]]]` | upper open bound |
| Equal to | `["="]` | `[["="]]` | `[[["False"]]]` | boolean/string equality |
| Range / old `between` | not recommended for filters; use two filter entries if needed | `[[">", "<"]]` or `[[">", "<="]]` | `[[["0.5", "1.2"]]]` | height between two limits |
| Set membership / old `in` or `any` | `["ANY"]` if the engine supports set filters | `[["ANY"]]` | `[[["Steel"], ["Aluminium"]]]` | allowed material list |

**Important range rule:** if the text says "between X and Y", do not write `Operator: [["between"]]`. Write the operator list as the two comparisons, for example `Operator: [[">", "<"]]`, and put the matching lower/upper values in the same `Value` group.

**Equality normalization:** old examples sometimes use `==`. Normalize to `"="`.

## 8. Expression Name (ExpName) Patterns

The ExpName is the most critical field to get right. It follows strict patterns:

### 8.1 Direct Attribute Access
```
Feature.Attribute
```
Examples: `Boss.OuterRadiusAtTop`, `Hole.IsFlatBottom`, `PMI.IsAttached`, `Rib.DraftAngle`

### 8.2 Ratio (Division by Reference Variable)
```
Feature.Attribute / DomainModule.ThicknessVariable
```
Examples:
- `Distance.MinValue/SheetMetal.Thickness` (Sheet Metal distance rules)
- `Rib.Height/PartBody.NominalThickness` (Die Casting rib rules)
- `Rib.Height/InjectionMolding.NominalThickness` (Injection Molding rib rules)
- `Bend.Radius/SheetMetalForm.NominalThickness` (SM Forming bend rules)
- `SimpleHole.Diameter/SheetMetalForm.NominalThickness` (SM Forming hole rules)

### 8.3 Ratio Between Feature Attributes
```
Feature.Attribute1 / Feature.Attribute2
```
Examples:
- `Boss.OuterDiameterAtTop/Boss.InnerDiameterAtTop` (Boss OD/ID ratio)
- `Hole.TotalDepth/Hole.DiameterAtTop` (Hole depth-to-diameter ratio)
- `Hole.ThreadDepth/Hole.DrillDepth` (Thread depth percentage)
- `Bend.Radius/Tube.OuterDiameter` (Tube bend ratio)
- `Bolt.ExtendedThreadLength/Bolt.ThreadPitch` (Thread engagement ratio)

### 8.4 Complex Arithmetic
```
(Feature.Attribute - offset) / Reference
```
Examples:
- `(Distance.MinValue-RolledHem.Radius)/SheetMetal.Thickness` (Example 5)
- `Distance.MinValue -( 2.0*RolledHem.Radius ) / SheetMetal.Thickness` (Example 4)
- `(Hole.WrapAngle/360)*100` (Example 82, percentage calculation)

### 8.5 Module-Level Accessor
```
DomainModule.Property
```
Examples:
- `SheetMetal.IsSheetMetalPart` (Example 20)
- `SheetMetal.Thickness` (Example 18, inside constraint)
- `Additive.PrintSize.Length` (Example 22, nested object)
- `Turn.Body.Length/Turn.Body.MinOuterDiameter` (Example 39, nested object ratio)
- `Mill.Machinability` (Example 87)
- `Tube.IsUniformBendRadius` (Example 52)

### 8.6 Nested Object Access
```
Object.SubObject.Attribute
```
Examples:
- `Additive.PrintSize.Length`, `Additive.PrintSize.Width`, `Additive.PrintSize.Height` (Example 22)
- `BoredHole.Relief.Value` (Example 38)
- `Turn.Body.Length`, `Turn.Body.MinOuterDiameter` (Example 39)

---

## 9. Feature & Object Reference per Domain

This section lists EVERY valid Object and its Attributes for each domain, as defined in features.py.

### 9.1 Sheet Metal
| Object | Attributes |
|:---|:---|
| Bend | MinRadius, MaxRadius, Angle, IsNullRadius, IsConical |
| BendRelief | Depth, Width |
| Hem | Radius, Angle, Length |
| OpenHem | Radius, Length |
| ClosedHem | Length |
| RolledHem | Radius, HemOpening |
| TearDropHem | Radius, Length, HemOpening |
| Stamp | Height, TaperAngle, PunchInnerRadius, PunchOuterRadius, DieInnerRadius, DieOuterRadius |
| Dowel | OuterRadius, OuterDiameter, OuterDiameterHeight |
| Dimple | DieInnerRadius, PunchOuterRadius, Height |
| Bridge | Length, Width |
| ExtrudedHole | InnerRadius, InnerDiameter, OuterRadius, OuterDiameter |
| CardGuide | Length, OpeningAngle |
| Cutout / SimpleCutout | IsInternal, IsInternalWithSingleFace, IsPlaner |
| Flange / EdgeFlange | Radius, Angle, Length |
| Emboss | Height, TaperAngle, PunchInnerRadius, PunchOuterRadius, DieInnerRadius, DieOuterRadius |
| Gusset | Width, Depth, HeadAngle |
| Louver | Breadth |
| Spoon | Length, FlangeWidth, Width, Height |
| Distance | MinValue |
| Hole / SimpleHole | Radius, Diameter |
| CompoundHole | Radius, Diameter, Depth |
| ModuleParams | Thickness, IsSheetMetalPart |

### 9.2 Die Casting
| Object | Attributes |
|:---|:---|
| MoldFace | MinThickness, MaxThickness, MoldWallThickness, DraftAngle, MoldClassificationType, IsUndercut, IsFillet, Height |
| Boss | OuterRadiusAtTop, OuterDiameterAtTop, OuterRadiusAtBot, OuterDiameterAtBot, InnerRadiusAtTop, InnerDiameterAtTop, InnerRadiusAtBot, InnerDiameterAtBot, TotalHeight, IsPartial, OuterSurfaceDraftAngle, InnerSurfaceDraftAngle, WrapAngle, IsChamferAtTop |
| Rib | DraftAngle, ProfileArea, RadiusAtBot, Height, TopThickness, ThicknessAtBotWithFillet, ThicknessAtBot |
| WallThickness | MinValue, MaxValue |
| MoldWall | MinValue, Height |
| Draft | Angle, Type, Height |
| Text | Height, DraftAngle |

### 9.3 Injection Molding
| Object | Attributes |
|:---|:---|
| Hole | RadiusAtTop, DiameterAtTop, RadiusAtBot, DiameterAtBot, TotalDepth, IsBlind, IsPartial, IsTapered, TaperAngle |
| Pin | RadiusAtTop, DiameterAtTop, TotalHeight, IsPartial, IsTopSpherical, WrapAngle |
| IMFace | MinThickness, MaxThickness, MoldWallThickness, DraftAngle, MoldClassificationType, IsUndercut |
| Lip | MinThickness, RadiusAtBot |
| Boss | (same as Die Casting) |
| Rib | DraftAngle, ProfileArea, RadiusAtBot, Height, TopThickness, ThicknessAtBotWithFillet, ThicknessAtBot |
| Draft | Angle, Type, Height |
| Text | Height, DraftAngle |
| ModuleParams | NominalThickness |

### 9.4 Milling
| Object | Attributes |
|:---|:---|
| Pocket | Depth, IsDrafted, DraftAngle, MinSideRadius, MaxSideRadius, MinBotRadius, MaxBotRadius, IsOpen, IsBotFilleted, IsTopFilleted, IsSideFilleted, NumBotSharpEdges, NumSideSharpEdges, DraftType, IsBotChamfered, SideFaceAngle, ExtendedDepth |
| BotFillet | MinRadius, MaxRadius, IsVariableRadius |
| SideFillet / TopFillet / Fillet | MinRadius, MaxRadius, IsVariableRadius |
| Chamfer | Width, Angle1, Angle2, IsVertex, Distance1, Distance2 |
| PMI | ProfileOfLine, ProfileOfSurface, SurfaceFinish |
| ModuleParams | Machinability |

### 9.5 Drilling (sub-domain of Mill)
| Object | Attributes |
|:---|:---|
| Hole | Radius, Diameter, IsBlind, IsThreaded, ThreadDepth, DrillDepth, ThreadSize, ThreadDrillDiameter, ThreadType, EntryAngle, ExitAngle, IsFlatBottom, IsPartial, WrapAngle, TipDepth, TipAngle, NumElemHole, TotalDepth, PositionTolerance |
| HoleSegment | Radius, Diameter, Depth, TaperAngle, IsTapered, IsPartial, WrapAngle, PositionTolerance |
| SimpleHole / CompoundHole / CBHole / CSHole / CDHole / HoleChain | (various hole-type-specific attributes) |

### 9.6 Assembly
| Object | Attributes |
|:---|:---|
| Component | Name, FileName, Identifier, ParentName, ParentFileName, ParentIdentifier, Type |
| Distance | Value, CustomValue |
| Interference | IsInterfering, Volume |
| Clearance | MinValue, IsTouching, IsInterfering |
| Fastener | Type, Name, IsWasherPresent, IsFirstEngagedCompInContact, WrenchFlatDiameter, BearingArea, MinSupportWidth, ContactWidth, FirstEngagedComp, ScrewDiameter, FirstEngagedHole |
| Bolt | Size, Name, IsWasherPresent, ..., ClearanceHoleDepth, ShankLength, ThreadPitch, ExtendedThreadLength, ..., IsThreaded, Length |
| Nut | Name, IsWasherPresent, ... |

### 9.7 Additive Manufacturing
| Object | Attributes |
|:---|:---|
| AMFace | MinThickness, MaxThickness, MinGap |
| Pin | RadiusAtTop, DiameterAtTop, TotalHeight, IsPartial, IsTopSpherical |
| Hole | RadiusAtTop, DiameterAtTop, RadiusAtBot, DiameterAtBot, TotalDepth, IsBlind, IsPartial, IsTapered, TaperAngle |
| Text | Height, Width |
| Wall | MinThickness, MaxThickness, IsSupported |
| PMI | Angularity |
| PrintSize | Length, Height, Width |

### 9.8 Turning
| Object | Attributes |
|:---|:---|
| TurnCorner | Radius, IsSharp, IsConcave |
| FaceFeature | FlatnessTolerance, PerpendicularityTolerance, SurfaceFinish |
| TurnProfileSegment | MinAngle, MaxAngle, IsExternal, IsLinear, Length, MaxContourRadius, MinContourRadius, MaxDiameter, MinDiameter, ... (many tolerance attributes) |
| Body | Length, MaxOuterDiameter, MinOuterDiameter, MaxInnerDiameter, MinInnerDiameter |
| BoredHole | MinDiameter, MaxDiameter, IsBlind, Depth, Relief (sub-object) |
| Relief | Value |

### 9.9 Tubing
| Object | Attributes |
|:---|:---|
| Bend | Radius, Angle, IsAtEnd, SupportLength1, SupportLength2 |
| Straight | Length, IsAtEnd |
| Clearance | MinValue, IsTouching, IsInterfering |
| Tube | Thickness, OuterDiameter, InnerDiameter, Length, IsUniformBendRadius, MaxBendRadius, MinBendRadius |
| Overlap | Length |

### 9.10 Sheet Metal Forming
| Object | Attributes |
|:---|:---|
| SimpleHole | Radius, Diameter, Depth, TaperAngle, IsTapered |
| Bend | Radius |
| SMFace | Thickness |
| ModuleParams | NormalThickness |

### 9.11 General & Model
| Object | Attributes |
|:---|:---|
| PMI | Straightness, Flatness, Circularity, Cylindricity, Angularity, Parallelism, Perpendicularity, ProfileOfLine, ProfileOfSurface, Position, Concentricity, Symmetry, Runout, TotalRunout, IsAttached |
| PartEdge | IsSharp |
| Hole | InternalThreadClass |
| Thread | ExternalThreadClass, Size, Unit |
| PartBody | Material, Length, Width, Height, DiagonalLength, TightBoxLength, TightBoxWidth, TightBoxHeight, TightBoxDiagonalLength, Volume, SurfaceArea |

---

## 10. Handling Applicability Constraints

Applicability is now represented through two different mechanisms:

- Use `FilterParamList` when the rule applies only to instances matching a fixed criterion.
- Use `ConditionParamList` when the rule has multiple branches with different validation values.

### 10.1 Filter Structure

Filters use shallow arrays:

```json
{
  "FilterParamList": [
    {
      "ExpName": "Fastener.FirstEngagedComp.Material",
      "Operator": [
        "="
      ],
      "Value": [
        "Steel"
      ]
    }
  ]
}
```

### 10.2 Condition Structure

Conditions use nested operator/value arrays and align by case index with validation values:

```json
{
  "ConditionParamList": [
    {
      "ExpName": "Hole.IsBlind",
      "Operator": [
        [
          "="
        ]
      ],
      "Value": [
        [
          [
            "Yes"
          ]
        ],
        [
          [
            "No"
          ]
        ]
      ]
    }
  ],
  "ValidationParamList": [
    {
      "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
      "Operator": [
        [
          "="
        ]
      ],
      "Value": [
        [
          [
            "2.0"
          ]
        ],
        [
          [
            "4.0"
          ]
        ]
      ],
      "AllowedParams": [
        ""
      ]
    }
  ]
}
```

### 10.3 Types of Conditions

| Condition Type | Condition Expression | Encoding Pattern |
|:---|:---|:---|
| Material match | `PartBody.Material = 6061-T6` | Filter if it only scopes applicability |
| Boolean state | `Hole.IsBlind = Yes/No` | Condition if each branch has a different validation value |
| Numeric threshold | `PartBody.TightBoxDiagonalLength <= 25.4` | Condition with `[["<="]]` |
| Numeric range | `Pin.TotalHeight between 0.0 and 10.0` | Condition with `[[">", "<"]]` and two values |

### 10.4 Single vs Multiple Branches

**Single fixed applicability (filter):**
```json
{
  "Name": "Presence of Washer for Fasteners",
  "RuleCategory": "Assembly",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Fastener",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "Fastener.FirstEngagedComp.Material",
        "Operator": [
          "="
        ],
        "Value": [
          "Steel"
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Fastener.IsWasherPresent",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "Yes"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

**Branch-specific values (condition):**
```json
{
  "Name": "Recommended Ratio of Hole Depth to Diameter",
  "RuleCategory": "Injection Molding",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Hole",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "Hole.IsBlind",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "Yes"
            ]
          ],
          [
            [
              "No"
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "2.0"
            ]
          ],
          [
            [
              "4.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### 10.5 Resolution Strategy

1. If a phrase only narrows the target population (`for steel fasteners`, `for material 6061-T6`), use `FilterParamList`.
2. If a phrase changes the validation threshold (`2.0 for blind holes and 4.0 for through holes`), use `ConditionParamList`.
3. If multiple conditions define the same branch, include multiple condition entries with the same number of case values.
4. If a condition is a range, encode it as paired comparison operators, not as `between`.

## 11. Handling Multi-Rule Divergence from Single Text

### 11.1 Type A: Conjuncted Independent Rules

When one sentence contains unrelated constraints on different features, split it into separate rule JSON objects.

**Borderline case that stays as one rule:**

`"Card guide length should be at most 127.0 mm and the opening angle should be at least 15.0 degrees"`

This remains one rule because both constraints apply to `CardGuide`.

**Case that splits into two rules:**

`"The hole diameter should be at least 5mm and the pocket should be filleted"`

These are unrelated constraints (`Hole` vs `Pocket`) and should become two separate JSON rules.

### 11.2 Type B: Conditional Branching (Applicability Divergence)

When one expression has different values under different conditions, keep it as one rule with aligned condition and validation cases.

**Example 60 (Hole Depth Ratio):**
```json
{
  "Name": "Recommended Ratio of Hole Depth to Diameter",
  "RuleCategory": "Injection Molding",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Hole",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "Hole.IsBlind",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "Yes"
            ]
          ],
          [
            [
              "No"
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "2.0"
            ]
          ],
          [
            [
              "4.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### 11.3 Decision Matrix

| Situation | Action | Why |
|:---|:---|:---|
| Same feature, multiple attributes | One rule, multiple validation entries | Same instance context |
| Different unrelated features | Split into multiple rules | Different validation targets |
| Same expression, different condition values | One rule with `ConditionParamList` | Branch cases align cleanly |
| Fixed applicability only | One rule with `FilterParamList` | No branch-specific output |
| Extra data needed but not validated | Add `AdditionalParamList` | Avoid mixing reporting data with pass/fail |

## 12. Chain-of-Thought (CoT) Formalization Pipeline

### Step 1: Is this a Rule?
**Question:** "Does this text impose a measurable or boolean manufacturing constraint?"

Positive indicators:
- Modal verbs (`should`, `must`, `shall`)
- Numeric thresholds
- Boolean states (`avoid`, `ensure no`, `must be present`)
- Set membership (`one of`, `from the following list`)

### Step 2: Domain Classification
**Question:** "Which manufacturing domain owns this rule?"

Use the keyword and disambiguation rules in Section 5. Normalize category names to the canonical `RuleCategory` strings in Section 4.

### Step 3: Sentence Segmentation & Structural Classification
**Question:** "Is this one rule or multiple?"

```
Has unrelated features?
  Yes -> split into multiple JSON rules
  No  -> continue

Has branch-specific thresholds?
  Yes -> use ConditionParamList
  No  -> continue

Has fixed applicability?
  Yes -> use FilterParamList
  No  -> use empty placeholder filter

Has multiple attributes on the same feature?
  Yes -> multiple ValidationParamList entries
  No  -> single ValidationParamList entry
```

### Step 4: Entity Extraction
**Question:** "What are Feature1, Feature2, Object1, and Object2?"

| Scenario | Feature1 | Object1 | Object2 |
|:---|:---|:---|:---|
| Distance between bridges | `Distance` | `Bridge` | `Bridge` |
| Boss radius | `Boss` | `""` | `""` |
| PMI angularity | `PMI` | `""` | `""` |
| Module material | `""` | `""` | `""` |

### Step 5: Expression Formulation (ExpName)
**Question:** "How is the constraint mathematically expressed?"

| Raw Text Pattern | ExpName Pattern |
|:---|:---|
| "X times sheet thickness" | `Feature.Measurement/SheetMetal.Thickness` |
| "depth to diameter ratio" | `Hole.TotalDepth/Hole.DiameterAtTop` |
| "is flat bottom" | `Hole.IsFlatBottom` |
| "material should be from list" | `PartBody.Material` |

### Step 6: Bounding (Operator & Value)
**Question:** "What is the limit, and in which direction?"

| Text Pattern | Operator Encoding | Value Encoding |
|:---|:---|:---|
| at least / minimum | `[[">="]]` | `[[["value"]]]` |
| at most / not exceed | `[["<="]]` | `[[["value"]]]` |
| equal / should be | `[["="]]` | `[[["value"]]]` |
| between X and Y | `[[">", "<"]]` | `[[["X", "Y"]]]` |
| one of / from list | `[["ANY"]]` | `[[["A"], ["B"]]]` |

### Step 7: Constraint Placement

1. Put the pass/fail metric in `ValidationParamList`.
2. Put fixed applicability in `FilterParamList`.
3. Put branch selectors in `ConditionParamList`.
4. Put report-only attributes in `AdditionalParamList`.
5. Put runtime inputs in `UserParamList`.

### Step 8: Validation

Before finalizing a rule JSON object, verify:

1. All required top-level fields exist.
2. `Results` is populated, usually with `Validation`.
3. `RuleType` is `Feature` or `Module`.
4. `Feature1`, `Object1`, and `Object2` match the entity structure.
5. Every validation has `ExpName`, nested `Operator`, nested `Value`, and `AllowedParams`.
6. Legacy scalar recommendation, range, and set-membership operator fields are not present.
7. `between` text is encoded as paired comparison operators.
8. Condition and validation branch counts align.

## 13. Current Pipeline Architecture & Improvement Opportunities

### 13.1 Current Pipeline Stages

The existing DFM formalization pipeline (in `dfm_rule_pipeline/`) follows this flow:

```
Stage 1: Intent Extraction (LLM)
    → Determines: is_quantifiable, requires_geometry, requires_tolerance, domain
    
Stage 2: Rule Resolution (LLM)
    → Determines: rule_category (Geometry | Tolerance | Attribute)
    
Stage 2b/2c: Geometry/Tolerance Sub-Resolution (LLM)
    → Handles spatial and tolerance-specific logic
    
Stage 3: Formalization (LLM)
    → Converts validated intent into equation/AST format
    
Stage 3b: Attribute Formalization (LLM)
    → Alternative path for attribute-type rules
    
Stage 4: Self-Validation (LLM)
    → Validates the output
    
Formatter: Post-Processing
    → Converts LLM output into final DFM JSON format
    → Handles variable substitution, algebra normalization, semantic naming
```

### 13.2 Key Components in the Formatter

The `formatter.py` handles critical post-processing:

1. **Domain Configuration** — Maps each domain to its RuleCategory string, thickness variable, and aliases
2. **Variable Substitution** — Replaces aliases (e.g., `ModuleParams.Thickness` → `SheetMetal.Thickness`)
3. **Algebra Normalization** — Converts `LHS >= N * Thickness` into `LHS/Thickness >= N`
4. **Semantic Name Generation** — Creates human-readable rule names from features and objects

### 13.3 Improvement Opportunities for Phase 3

Based on this taxonomy, the following improvements should be considered:

1. **LLM should focus on text-clipping and domain classification only** (Steps 1-3). The heavy lifting of entity extraction, expression formulation, and constraint wrapping should be handled by the deterministic pipeline stages.

2. **Sentence segmentation needs to handle Type 6 and Type 7 rules** — Currently, the pipeline may not properly handle nested constraint blocks.

3. **Feature schema validation should be enforced** — Every ExpName should be validated against the features_dict for the detected domain.

4. **Multi-expression rules should not be split** — When multiple constraints apply to the same feature, they should remain in one rule object.

5. **The formatter's algebra normalization** already handles the common case of `X >= N * Thickness` → `X/Thickness >= N`. This pattern should be preserved and extended to cover more complex arithmetic patterns (e.g., Example 4 and 5).

---

## 14. Complete Worked Examples

### Example A: Simple Distance Rule (Type 1)

**Input:** "Distance between emboss and cutouts should be at least 4.0 times sheet thickness"

**Reasoning Summary:**
- Domain: Sheet Metal
- RuleType: Feature
- Feature1: Distance
- Object1/Object2: Emboss and Cutout
- Validation: `Distance.MinValue/SheetMetal.Thickness >= 4.0`

```json
{
  "Name": "Emboss to Cutout Distance",
  "RuleCategory": "SheetMetal",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Distance",
  "Feature2": "",
  "Object1": "Emboss",
  "Object2": "Cutout",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Distance.MinValue/SheetMetal.Thickness",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "4.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example B: Multi-Expression Rule (Type 2)

**Input:** "Recommended boss parameters: Outer Diameter to Inner Diameter ratio should be at least 2.0, and Height to Outer Diameter ratio should be at least 3.0."

**Reasoning Summary:**
- Domain: Injection Molding
- RuleType: Feature
- Feature1: Boss
- Two validation expressions under one feature context

```json
{
  "Name": "Recommended Boss Parameters",
  "RuleCategory": "Injection Molding",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Boss",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Boss.OuterDiameterAtTop/Boss.InnerDiameterAtTop",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "2.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "Boss.TotalHeight/Boss.OuterDiameterAtTop",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "3.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example C: Conditional Rule (Type 7)

**Input:** "Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes."

**Reasoning Summary:**
- Domain: Injection Molding
- Condition: `Hole.IsBlind` has two branch values
- Validation values align with the condition branch index

```json
{
  "Name": "Recommended Ratio of Hole Depth to Diameter",
  "RuleCategory": "Injection Molding",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Hole",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "Hole.IsBlind",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "Yes"
            ]
          ],
          [
            [
              "No"
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "2.0"
            ]
          ],
          [
            [
              "4.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example D: Boolean Rule (Type 4)

**Input:** "Ensure there are no sharp edges in the part."

**Reasoning Summary:**
- Domain: Additive Manufacturing
- Boolean validation: sharp edges should be false

```json
{
  "Name": "Sharp Edge Check",
  "RuleCategory": "Additive Manufacturing",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "PartEdge",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "PartEdge.IsSharp",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "No"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example E: Set Membership Rule (Type 5)

**Input:** "Ensure that thread sizes conform to the recommended standard sizes: 1-64 UNC, 1-72 UNF, 2-56 UNC."

**Reasoning Summary:**
- Domain: General
- Old `in` / `any` becomes `ANY`
- Each allowed value is an inner value item

```json
{
  "Name": "Recommended Standard Thread Sizes",
  "RuleCategory": "General",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Thread",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Thread.Size",
        "Operator": [
          [
            "ANY"
          ]
        ],
        "Value": [
          [
            [
              "1-64 UNC"
            ],
            [
              "1-72 UNF"
            ],
            [
              "2-56 UNC"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example F: Between / Range Rule

**Input:** "For a spoon feature the minimum height should be between 0.5 and 1.2 times sheet thickness."

**Reasoning Summary:**
- Legacy scalar range operator syntax is not valid in the new schema
- Use `Operator: [[">", "<"]]` with lower and upper values in the same value group

```json
{
  "Name": "Recommended Minimum Height of Spoon Feature",
  "RuleCategory": "SheetMetal",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Spoon",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Spoon.Height/SheetMetal.Thickness",
        "Operator": [
          [
            ">",
            "<"
          ]
        ],
        "Value": [
          [
            [
              "0.5",
              "1.2"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example G: Filtered Rule

**Input:** "In an assembly, ensure washer is present for fasteners engaging with steel."

**Reasoning Summary:**
- Fastener material is a fixed applicability filter
- Washer presence is the validation

```json
{
  "Name": "Presence of Washer for Fasteners",
  "RuleCategory": "Assembly",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Fastener",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "Fastener.FirstEngagedComp.Material",
        "Operator": [
          "="
        ],
        "Value": [
          "Steel"
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Fastener.IsWasherPresent",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "Yes"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example H: Additional Parameter Rule

**Input:** "In Injection Molding part, Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes; also check hole diameter at bottom additionally for each instance."

**Reasoning Summary:**
- Branching stays in `ConditionParamList`
- Pass/fail ratio stays in `ValidationParamList`
- `Hole.DiameterAtBot` is report-only, so it goes in `AdditionalParamList`

```json
{
  "Name": "Recommended Ratio of Hole Depth to Diameter",
  "RuleCategory": "Injection Molding",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Hole",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "Hole.IsBlind",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "Yes"
            ]
          ],
          [
            [
              "No"
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Hole.TotalDepth/Hole.DiameterAtTop",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "2.0"
            ]
          ],
          [
            [
              "4.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      }
    ],
    "AdditionalParamList": [
      {
        "ExpName": "Hole.DiameterAtBot"
      }
    ],
    "UserParamList": [
      {
        "ParamName": "",
        "DisplayName": "",
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example I: Fixed-Diameter Tube Bend Radius

**Input:** "Bend radius should be at least 14.2748 units for tubes with an outer diameter of 6.35 units."

**Reasoning Summary:**
- Domain: Tubing
- Fixed tube outer diameter is applicability, so it belongs in `FilterParamList`
- Bend radius is the pass/fail validation

```json
{
  "Name": "Recommended Tube Bend Radius",
  "RuleCategory": "Tubing",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Bend",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "Tube.OuterDiameter",
        "Operator": [
          "="
        ],
        "Value": [
          "6.35"
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Bend.Radius",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "14.2748"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example J: Boss Cored-Hole Radius

**Input:** "Cored hole radius in boss should be at least 0.254 units."

**Reasoning Summary:**
- Domain: Injection Molding
- `Boss` is the feature itself; `Object1` and `Object2` stay empty
- Inner boss radius is a direct validation expression

```json
{
  "Name": "Cored Hole Radius in Boss",
  "RuleCategory": "Injection Molding",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Boss",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Boss.InnerRadiusAtBot",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "0.254"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example K: Range Condition with Range Validation

**Input:** "For pins with height between 0 and 10 units recommended pin diameter should be between 0.5 and 1.5 units."

**Reasoning Summary:**
- The pin-height range is a branch condition
- The pin-diameter recommendation is also a range validation
- Both old `between` phrases become paired operator lists

```json
{
  "Name": "Recommended Pin Diameter Based on Pin Height",
  "RuleCategory": "Injection Molding",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Pin",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "Pin.TotalHeight",
        "Operator": [
          [
            ">",
            "<"
          ]
        ],
        "Value": [
          [
            [
              "0.0",
              "10"
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Pin.DiameterAtTop",
        "Operator": [
          [
            ">",
            "<"
          ]
        ],
        "Value": [
          [
            [
              "0.5",
              "1.5"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example L: Uniform Wall Thickness Min/Max

**Input:** "The uniform wall thickness should be between 2.0 and 3.0 units."

**Reasoning Summary:**
- Preserve the paired min/max expression pattern from the old taxonomy
- Emit separate validation entries instead of numbered suffix fields

```json
{
  "Name": "Uniform Wall Thickness",
  "RuleCategory": "Injection Molding",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "IMFace",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "IMFace.MinThickness",
        "Operator": [
          [
            ">="
          ]
        ],
        "Value": [
          [
            [
              "2.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "IMFace.MaxThickness",
        "Operator": [
          [
            "<="
          ]
        ],
        "Value": [
          [
            [
              "3.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example M: Hole Entry and Exit Angles

**Input:** "The entry and exit angles for holes should be 0.0 degrees for proper drilling."

**Reasoning Summary:**
- Domain: Drilling, because this is hole-specific under the Mill family
- Entry and exit angle are paired equality validations

```json
{
  "Name": "Entry-Exit Surface for Holes",
  "RuleCategory": "Drilling",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "Hole",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "",
        "Operator": [
          [
            ""
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "Hole.EntryAngle",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "0.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
      },
      {
        "ExpName": "Hole.ExitAngle",
        "Operator": [
          [
            "="
          ]
        ],
        "Value": [
          [
            [
              "0.0"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

### Example N: Multi-Condition Position Tolerance

**Input:** "Recommended position tolerance for holes should be 0.0254 for default, 0.0508 for parts with diagonal length 0.0 to 25.4 and diameter 5.05714 to 7.54126, 0.127 for parts with diagonal length 25.4 to 152.4 and diameter 5.05714 to 7.54126, and 0.254 for parts with diagonal length 152.4 to 2540.0 and diameter 5.05714 to 7.54126."

**Reasoning Summary:**
- This restores the old triple-nested Example 85 guidance in the new schema
- Multiple `ConditionParamList` entries align by branch index
- The first branch is the default case; if a consuming engine cannot use an empty second condition for the default branch, split the default into a separate module/feature rule

```json
{
  "Name": "Recommended Position Tolerance for Hole",
  "RuleCategory": "Drilling",
  "Results": "Validation",
  "RuleType": "Feature",
  "Feature1": "HoleSegment",
  "Feature2": "",
  "Object1": "",
  "Object2": "",
  "Constraints": {
    "FilterParamList": [
      {
        "ExpName": "",
        "Operator": [
          ""
        ],
        "Value": [
          ""
        ]
      }
    ],
    "ConditionParamList": [
      {
        "ExpName": "PartBody.TightBoxDiagonalLength",
        "Operator": [
          [
            "="
          ],
          [
            ">",
            "<="
          ],
          [
            ">",
            "<="
          ],
          [
            ">",
            "<="
          ]
        ],
        "Value": [
          [
            [
              "Default"
            ]
          ],
          [
            [
              "0.0",
              "25.4"
            ]
          ],
          [
            [
              "25.4",
              "152.4"
            ]
          ],
          [
            [
              "152.4",
              "2540.0"
            ]
          ]
        ]
      },
      {
        "ExpName": "HoleSegment.Diameter",
        "Operator": [
          [
            ""
          ],
          [
            ">",
            "<="
          ],
          [
            ">",
            "<="
          ],
          [
            ">",
            "<="
          ]
        ],
        "Value": [
          [
            [
              ""
            ]
          ],
          [
            [
              "5.05714",
              "7.54126"
            ]
          ],
          [
            [
              "5.05714",
              "7.54126"
            ]
          ],
          [
            [
              "5.05714",
              "7.54126"
            ]
          ]
        ]
      }
    ],
    "ValidationParamList": [
      {
        "ExpName": "HoleSegment.PositionTolerance",
        "Operator": [
          [
            "<="
          ]
        ],
        "Value": [
          [
            [
              "0.0254"
            ]
          ],
          [
            [
              "0.0508"
            ]
          ],
          [
            [
              "0.127"
            ]
          ],
          [
            [
              "0.254"
            ]
          ]
        ],
        "AllowedParams": [
          ""
        ]
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
        "Value": [
          ""
        ],
        "MinValue": "",
        "MaxValue": ""
      }
    ]
  }
}
```

## Summary Statistics

| Metric | Value |
|:---|:---:|
| Source example corpus | 89 DFX rule examples |
| Manufacturing domains | 10 primary + 2 sub-domains |
| Updated schema family | `format1 (1).json` |
| Primary result type | `Validation` |
| Rule scopes | `Feature`, `Module` |
| Constraint lists | `FilterParamList`, `ConditionParamList`, `ValidationParamList`, `AdditionalParamList`, `UserParamList` |
| Restored advanced edge cases | Tubing fixed filters, boss radius, range condition + range validation, IM min/max thickness, drilling entry/exit angles, multi-condition hole position tolerance |
| Core comparison operators | `>=`, `<=`, `>`, `<`, `=` |
| Set operator | `ANY` |
| Range encoding | paired operators such as `[[">", "<"]]`, not scalar `between` |
