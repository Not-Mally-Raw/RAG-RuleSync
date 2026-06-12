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

A DFM rule is a **quantifiable manufacturing constraint** applied to a geometric feature, material property, or process parameter that ensures a part can be manufactured reliably, cost-effectively, and within quality tolerances.

**Key properties of a DFM rule:**
- It constrains a **measurable attribute** (dimension, angle, ratio, boolean state)
- It specifies a **limit or threshold** (minimum, maximum, range, equality, set membership)
- It applies to **one or more physical features** on a part (holes, bends, ribs, walls, etc.)
- It belongs to a specific **manufacturing domain** (Sheet Metal, Milling, Injection Molding, etc.)

**What is NOT a DFM rule:**
- General design advice without quantifiable bounds (e.g., "Consider weight reduction")
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

Every formalized DFM rule follows this exact schema. Each component MUST be populated (empty string `""` if not applicable).

### 3.1 The Schema Structure

```
RuleCategory = <domain>
Name = <semantic rule name>

Feature1 = <primary feature or measurement type>
Feature2 = ""
Object1 = <first physical entity>
Object2 = <second physical entity>

ExpName = <mathematical expression>
Operator = <comparison operator>
Recom = <threshold value>
```

### 3.2 Component Definitions

| Component | Required? | Description | How to Populate |
|:---|:---:|:---|:---|
| **RuleCategory** | ✅ | The manufacturing domain this rule belongs to | See Section 4 for the complete list |
| **Name** | ✅ | A concise human-readable name describing the rule | Derive from the rule's intent: e.g., "Bridge Spacing", "Minimum Bend Radius" |
| **Feature1** | ✅ | The primary measurable feature or property class. This is the TYPE of measurement being made. | `Distance`, `Bend`, `Boss`, `Rib`, `Wall`, `Hole`, `PMI`, `Text`, `Pin`, etc. Use `""` only for module-level checks |
| **Feature2** | ✅ | A secondary feature (if the rule involves interaction between two different feature types). Almost always `""` | Only populated when two DIFFERENT feature types interact |
| **Object1** | ✅ | The first physical topology/entity being constrained | `Bridge`, `Cutout`, `Bend`, `PartEdge`, `Component`, `Tube`, etc. Use `""` when the feature IS the object |
| **Object2** | ✅ | The second physical entity (for inter-feature rules) | `Bridge`, `Bend`, `PartEdge`, etc. Use `""` for single-feature rules |
| **ExpName** | ✅ | The mathematical/programmatic expression representing the metric | `Distance.MinValue/SheetMetal.Thickness`, `Boss.OuterRadiusAtBot`, `Hole.IsFlatBottom` |
| **Operator** | ✅ | The comparison operator | `>=`, `<=`, `==`, `between`, `in` |
| **Recom** | ✅ | The threshold value or state | `4.5`, `True`, `False`, `0.5:1.2` (for between), `1A, 2A` (for in) |

### 3.3 When Feature1 vs Object1 Differ

This is a critical distinction:

- **Feature1 = Distance**: The MEASUREMENT TYPE is "distance". Object1 and Object2 specify WHAT the distance is measured between.
  - Example 1: `Feature1=Distance, Object1=Bridge, Object2=Bridge` → distance between two bridges
  - Example 7: `Feature1=Distance, Object1=Emboss, Object2=Cutout` → distance between emboss and cutout

- **Feature1 = Boss**: The FEATURE ITSELF is a boss. Object1 and Object2 are `""` because we're measuring the boss's own attributes.
  - Example 59: `Feature1=Boss, Object1="", Object2=""` → boss's own inner radius

- **Feature1 = Clearance**: Special measurement type for assembly.
  - Example 27: `Feature1=Clearance, Object1=Component, Object2=Component` → clearance between components

### 3.4 Multi-Expression Rules

A single formalized rule can have **multiple ExpName/Operator/Recom groups** when the rule constrains multiple attributes of the same feature simultaneously:

```
ExpName = CardGuide.Length
Operator = <=
Recom = 127.0

ExpName = CardGuide.OpeningAngle
Operator = >=
Recom = 15.0
```

This occurs in Example 2 (Card Guide Parameters) where length AND opening angle are both constrained. The key is that both constraints apply to the same Feature1/Object combination.

### 3.5 Numbered ExpName Variants

When a rule constrains two aspects of the same object but needs to keep them paired (common with min/max bounds), the schema uses numbered suffixes:

```
ExpName1 = Wall.MinThickness
Operator1 = >=
Recom1 = 5.0

ExpName2 = Wall.MaxThickness
Operator2 = <=
Recom2 = 10.0
```

This occurs in Example 46 (Thickness Check), Example 50 (Recommended Tube Bend Radius), Example 72 (Uniform Wall Thickness), and Example 74 (Entry-Exit Surface for Holes).

---

## 4. Rule Categories (Manufacturing Domains)

There are **10 primary manufacturing domains** plus 2 sub-domains. Each has its own RuleCategory string:

| Domain Key | RuleCategory String | Description |
|:---|:---|:---|
| SheetMetal | `Sheet Metal` | Bending, punching, forming of sheet metal parts |
| SMForm | `Sheet Metal Forming` | Press-forming specific rules (simpler sheet metal) |
| Additive | `Additive Manufacturing` | 3D printing / additive processes |
| Assembly | `Assembly` | Multi-component assembly constraints |
| DieCasting | `Die Casting` | Die casting process rules |
| InjectionMolding | `Injection Molding` | Plastic injection molding |
| Mill | `Milling` or `Drilling` | CNC milling and drilling operations |
| Turn | `Turning` | Lathe / turning operations |
| Tubing | `Tubing` | Tube bending and routing |
| General | `General` | Cross-domain rules (PMI, threads, materials) |

**IMPORTANT: The Mill domain produces TWO different RuleCategory strings:**
- `Milling` — for pocket, fillet, and surface rules (Examples 73, 75, 77, 81, 83, 84, 86, 87, 88, 89)
- `Drilling` — for hole-related rules (Examples 74, 76, 78, 79, 80, 82, 85)

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

Every rule falls into one of these structural types. Understanding the type is essential for correct formalization.

### Type 1: Simple Single-Expression Rule
**One feature, one constraint, one threshold.**

**Pattern:** `Feature.Attribute Operator Value`

**Example 1 (Bridge Spacing):**
```
Rule Text: "Distance between bridges should be at least 4.5 times sheet thickness"

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 4.5
```

**More examples:** #3, #6, #7, #8, #9, #10, #11, #12, #13, #14, #15, #16, #17, #21, #23, #24, #26, #31, #32, #33, #40, #41, #42, #43, #44, #45, #48, #49, #51, #53, #54, #55, #56, #57, #59, #61, #62, #64, #66, #69, #70, #71, #73, #75, #76, #77, #78, #79, #80, #81, #87, #88

### Type 2: Multi-Expression Rule (Same Feature, Multiple Constraints)
**One feature, multiple attributes constrained simultaneously.**

**Pattern:** Multiple `ExpName/Operator/Recom` blocks under the same Feature1/Object1.

**Example 2 (Card Guide Parameters):**
```
Rule Text: "Card guide length should be at most 127.0 mm and the opening angle should be at least 15.0 degrees"

Feature1 = CardGuide

ExpName = CardGuide.Length
Operator = <=
Recom = 127.0

ExpName = CardGuide.OpeningAngle
Operator = >=
Recom = 15.0
```

**Example 19 (Spoon Parameters — 3 constraints including a "between"):**
```
ExpName = Spoon.FlangeWidth/SheetMetal.Thickness
Operator = >=
Recom = 0.8

ExpName = Spoon.Length/SheetMetal.Thickness
Operator = >=
Recom = 10.0

ExpName = Spoon.Height/SheetMetal.Thickness
Operator = between
Recom = 0.5:1.2
```

**More examples:** #5, #22, #25, #34, #35, #36, #37, #63, #65, #68

### Type 3: Numbered Multi-Expression Rule
**Similar to Type 2, but uses numbered suffixes (ExpName1/Operator1/Recom1, ExpName2/Operator2/Recom2) to pair related constraints.**

**Example 46 (Thickness Check):**
```
ExpName1 = Wall.MinThickness
Operator1 = >=
Recom1 = 5.0

ExpName2 = Wall.MaxThickness
Operator2 = <=
Recom2 = 10.0
```

**More examples:** #50 (Tube Bend Radius), #72 (IM Uniform Wall Thickness), #74 (Entry-Exit Angles), #89 (Side Fillets)

### Type 4: Boolean State Rule
**Checking whether a feature has a boolean property (true/false).**

**Pattern:** `Feature.IsProperty Operator Boolean`

**Example 20 (Sheet Metal Part Check):**
```
ExpName = SheetMetal.IsSheetMetalPart
Operator = ==
Recom = True
```

**Example 78 (Flat Bottom Holes):**
```
ExpName = Hole.IsFlatBottom
Operator = ==
Recom = False
```

**More examples:** #21 (Sharp Edges), #28 (Washer Present), #41 (PMI Attached), #52 (Uniform Bend Radius), #81 (Variable Radius), #83 (Bottom Chamfered)

### Type 5: Set Membership Rule
**The value must be one of a predefined set.**

**Pattern:** `Feature.Attribute in SetOfValues`

**Example 42 (Thread Sizes):**
```
ExpName = Thread.Size
Operator = in
Recom = 1-64 UNC, 1-72 UNF, 2-56 UNC
```

**More examples:** #43 (External Thread Class), #44 (Internal Thread Class), #47 (Preferred Materials)

### Type 6: Applicability Constraint Rule (Conditional Rule)
**The rule includes a `Constraint` block that specifies WHEN the inner constraints apply. The inner constraints are only evaluated if the outer condition is met.**

**Pattern:**
```
Constraint : ExpName = <condition_expression>, Operator = <op>, Value = <val>
{
    ExpName = <constrained_expression>
    Operator = <op>
    Recom = <value>
}
```

**Example 18 (Material-Specific Flange Parameters):**
```
Rule Text: "For part with material 6061-T6 the flange radius should be at least 1.0 mm
            and the length should be 6.0 mm. The sheet thickness should be at least 2.0 mm."

Constraint : ExpName = PartBody.Material, Operator = ==, Value = 6061-T6
{
    ExpName = SheetMetal.Thickness
    Operator = >=
    Recom = 2.0

    ExpName = Flange.Radius
    Operator = >=
    Recom = 1.0

    ExpName = Flange.Length
    Operator = >=
    Recom = 6.0
}
```

**Example 38 (Blind vs Non-Blind Hole Relief — multiple constraint blocks):**
```
Rule Text: "Ensure that blind holes have a relief value of 3.0 units,
            and non-blind holes have a relief value of 0.0 units"

Constraint : ExpName= BoredHole.IsBlind, Operator= ==, Value = True
{
        ExpName= BoredHole.Relief.Value
        Operator= ==
        Recom = 3.0
}

Constraint : ExpName = BoredHole.IsBlind, Operator = ==, Value = False
{
        ExpName = BoredHole.Relief.Value
        Operator = ==
        Recom = 0.0
}
```

**More examples:** #60 (Hole Depth Ratio), #67 (Pin Diameter), #82 (Partial Holes)

### Type 7: Nested Constraint Rule (Multi-Level Conditional)
**Constraints nested inside other constraints, creating a hierarchical condition tree. These are the most complex rules.**

**Example 84 (Line Profile Tolerance based on Part Size):**
```
Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = 25.4
{
        ExpName = PMI.ProfileOfLine
        Operator = <=
        Recom = 0.0508
}
Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = >, Value = 25.4
{
        ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = 152.4
        {
                ExpName = PMI.ProfileOfLine
                Operator = <=
                Recom = 0.1016
        }
}
Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = >, Value = 152.4
{
        ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = 2540.0
        {
                ExpName = PMI.ProfileOfLine
                Operator = <=
                Recom = 0.1524
        }
}
```

**Example 85 (Position Tolerance — triple-nested with diameter AND part-size conditions):**
```
Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = 25.4
{
        ExpName = HoleSegment.Diameter, Operator = <=, Value = 7.54126
        {
                ExpName = HoleSegment.Diameter, Operator = >=, Value = 5.05714
                {
                        ExpName = HoleSegment.PositionTolerance
                        Operator = <=
                        Recom = 0.0508
                }
        }
}
```

**More examples:** #86 (Surface Profile Tolerance)

---

## 7. Operators: The Complete Set

| Operator | Meaning | Recom Format | Example |
|:---:|:---|:---|:---|
| `>=` | Greater than or equal to (minimum) | Single numeric value | `Recom = 4.5` |
| `<=` | Less than or equal to (maximum) | Single numeric value | `Recom = 127.0` |
| `==` | Exactly equal to | Numeric, Boolean, or String | `Recom = True`, `Recom = English` |
| `between` | Within a range (inclusive) | Colon-separated pair `min:max` | `Recom = 0.25:0.5` |
| `in` | Must be a member of a set | Comma-separated list | `Recom = 1A, 2A` |

**Usage distribution across the 89 examples:**
- `>=` — Most common (≈55%). Used for minimum thresholds.
- `<=` — Second most common (≈25%). Used for maximum limits.
- `==` — Used for exact matches and boolean checks (≈12%).
- `between` — Used for range constraints (≈5%). Examples: #19, #25, #32.
- `in` — Used for set membership (≈3%). Examples: #42, #43, #44, #47.

---

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

Applicability constraints occur when a rule's thresholds **change based on a condition** (material, geometry state, size range, etc.).

### 10.1 Structure

```
Constraint : ExpName = <condition_variable>, Operator = <condition_op>, Value = <condition_value>
{
    ExpName = <constrained_variable>
    Operator = <op>
    Recom = <value>
}
```

### 10.2 Types of Conditions

| Condition Type | Condition Expression | Example |
|:---|:---|:---|
| **Material match** | `PartBody.Material == 6061-T6` | Example 18 |
| **Boolean state** | `Hole.IsBlind == True` | Examples 38, 60 |
| **Size range** | `PartBody.TightBoxDiagonalLength <= 25.4` | Examples 84, 85, 86 |
| **Feature state** | `Hole.IsPartial == True` | Example 82 |
| **Numeric range** | `Pin.TotalHeight between 0.0:10` | Example 67 |

### 10.3 Single vs Multiple Constraint Blocks

**Single block (Example 18):** One condition, multiple inner constraints.
```
Constraint : ExpName = PartBody.Material, Operator = ==, Value = 6061-T6
{
    ExpName = SheetMetal.Thickness  →  >= 2.0
    ExpName = Flange.Radius         →  >= 1.0
    ExpName = Flange.Length          →  >= 6.0
}
```

**Dual blocks (Example 38):** Two mutually exclusive conditions.
```
Constraint : BoredHole.IsBlind == True  → Relief.Value == 3.0
Constraint : BoredHole.IsBlind == False → Relief.Value == 0.0
```

**Multiple blocks with ranges (Example 84):** Cascading size ranges.
```
Constraint : DiagonalLength <= 25.4     → ProfileOfLine <= 0.0508
Constraint : DiagonalLength > 25.4, <= 152.4  → ProfileOfLine <= 0.1016
Constraint : DiagonalLength > 152.4, <= 2540.0 → ProfileOfLine <= 0.1524
```

### 10.4 Resolution Strategy

When encountering a conditional rule in raw text:

1. **Identify the condition variable** — What determines which branch applies? (material? blind/through? size?)
2. **Identify the number of branches** — How many distinct conditions exist?
3. **For each branch, extract the inner constraints** — Each branch becomes its own Constraint block
4. **ALL branches go into ONE formalized rule object** — Do NOT split into separate rules. Use the `Constraint { }` structure.

---

## 11. Handling Multi-Rule Divergence from Single Text

Sometimes a single sentence contains what are actually **multiple independent rules**. These must be correctly identified and handled.

### 11.1 Type A: Conjuncted Independent Rules
**Two or more unrelated constraints joined by "and", "while", or comma in a single sentence.**

**How to identify:** The constraints involve DIFFERENT features/objects with no logical dependency between them.

**Example 2 (Card Guide — borderline case that stays as ONE rule):**
```
"Card guide length should be at most 127.0 mm and the opening angle should be at least 15.0 degrees"
```
This stays as ONE rule because both constraints apply to the SAME feature (CardGuide). They are multi-expression, not multi-rule.

**True conjuncted independent rules would be:**
```
"The hole diameter should be at least 5mm and the pocket should be filleted"
```
These are UNRELATED constraints (Hole vs Pocket) and should become TWO separate rules.

**Resolution:** During sentence segmentation (Step 2 of the CoT), identify whether the conjuncted constraints share the same Feature1/Object1. If YES → multi-expression rule. If NO → split into separate rules.

### 11.2 Type B: Conditional Branching (Applicability Divergence)
**A rule that specifies different thresholds based on conditions.**

**Example 60 (Hole Depth Ratio):**
```
"Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes"
```

This becomes ONE rule with TWO Constraint blocks (NOT two separate rules):
```
Constraint : Hole.IsBlind == True  → TotalDepth/DiameterAtTop <= 2.0
Constraint : Hole.IsBlind == False → TotalDepth/DiameterAtTop <= 4.0
```

### 11.3 Decision Matrix

| Scenario | Same Feature? | Dependent? | Resolution |
|:---|:---:|:---:|:---|
| "Length <= 127 and Angle >= 15" for CardGuide | ✅ | N/A | ONE rule, multi-expression (Type 2) |
| "Hole diameter >= 5 and Pocket is filleted" | ❌ | No | TWO separate rules |
| "Relief = 3.0 if blind, 0.0 if not" | ✅ | Conditional | ONE rule with Constraint blocks (Type 6) |
| "Thickness >= 2.0 and Radius >= 1.0 if material is 6061-T6" | ✅ | Conditional | ONE rule with Constraint block containing multiple expressions |

---

## 12. Chain-of-Thought (CoT) Formalization Pipeline

This is the step-by-step process any LLM or pipeline should follow to convert raw text into a formalized DFM rule. Each step builds on the previous.

### Step 1: Is this a Rule?
**Question:** "Does this text contain a quantifiable manufacturing constraint?"

**Check for:**
- ✅ Presence of a measurable attribute (dimension, angle, ratio, boolean)
- ✅ Presence of a threshold or limit (number, range, boolean value, set)
- ✅ Presence of a directive (should, must, ensure, avoid)

**If NO to any → Skip. Not a rule.**

### Step 2: Domain Classification
**Question:** "What manufacturing process is this text referring to?"

**Action:**
1. Scan for domain-specific keywords (see Section 5.1)
2. Apply disambiguation rules (see Section 5.2)
3. Map to the correct `RuleCategory` string (see Section 4)
4. Select the correct thickness variable for later use

**Output:** `RuleCategory = "Sheet Metal"` and `DomainThicknessVar = "SheetMetal.Thickness"`

### Step 3: Sentence Segmentation & Structural Classification
**Question:** "Is this a single rule, a multi-expression rule, or multiple independent rules?"

**Action:**
1. Count the number of distinct constraints in the sentence
2. Check if they share the same Feature1/Object1
3. Check for conditional branching (if/when/for material X)
4. Classify into Type 1-7 (see Section 6)

**Decision tree:**
```
Has conditions (if/when/for)?
├── YES → Type 6 or 7 (Constraint blocks)
│   └── Nested conditions? → Type 7
└── NO → Multiple constraints?
    ├── YES → Same feature?
    │   ├── YES → Type 2 or 3 (Multi-expression)
    │   └── NO → SPLIT into separate rules
    └── NO → Boolean check?
        ├── YES → Type 4
        └── NO → Set membership?
            ├── YES → Type 5
            └── NO → Type 1 (Simple)
```

### Step 4: Entity Extraction
**Question:** "What physical features and objects are involved?"

**Action:**
1. Identify the primary feature type → `Feature1` (Distance, Bend, Boss, Rib, Wall, Hole, etc.)
2. Identify the physical objects → `Object1`, `Object2` (Bridge, Cutout, PartEdge, etc.)
3. If it's a self-referential feature (e.g., Boss dimensions), set Object1/Object2 = `""`
4. If it's an inter-feature measurement (e.g., distance between A and B), set Feature1=Distance, Object1=A, Object2=B

**Cross-reference with Section 9** to ensure the feature/object exists in the domain's schema.

### Step 5: Expression Formulation (ExpName)
**Question:** "How is the constraint mathematically expressed?"

**Action:**
1. Identify the measured attribute (e.g., "radius", "height", "diameter")
2. Map to the correct schema attribute (e.g., `Boss.OuterRadiusAtBot`)
3. If the rule is relative ("X times thickness"), form a ratio: `Attribute/ThicknessVar`
4. If the rule involves arithmetic ("plus twice the radius"), encode the full expression
5. Use the patterns from Section 8 as reference

**Common transformations:**
| Raw Text Pattern | ExpName Pattern |
|:---|:---|
| "X should be at least Y" | `X >= Y` |
| "X should be at least Y times thickness" | `X/Thickness >= Y` |
| "X should be at least Y plus Z" | `(X - Z) >= Y` or encoded as arithmetic |
| "ratio of X to Y" | `X/Y` |
| "percentage of X" | `X/TotalX * 100` or `X/TotalX` |

### Step 6: Bounding (Operator & Recom)
**Question:** "What is the limit, and in which direction?"

| Text Pattern | Operator | Recom |
|:---|:---:|:---|
| "at least X" / "minimum X" / "no less than X" | `>=` | X |
| "at most X" / "maximum X" / "no more than X" / "should not exceed X" | `<=` | X |
| "should be X" / "must equal X" / "is set to X" | `==` | X |
| "between X and Y" | `between` | `X:Y` |
| "one of: A, B, C" / "conform to: A, B" | `in` | `A, B, C` |
| "avoid X" / "should not have X" | `==` | `False` (for boolean) |

### Step 7: Constraint Wrapping (if applicable)
**Question:** "Is this constraint conditional on another property?"

**If YES:**
1. Identify the condition variable and value
2. Wrap the ExpName/Operator/Recom in a Constraint block
3. If there are multiple branches, create multiple Constraint blocks
4. If conditions are nested, create nested Constraint blocks

### Step 8: Validation
**Question:** "Does the formalized rule match the schema?"

**Checks:**
1. ✅ RuleCategory is a valid domain string
2. ✅ Feature1 exists in the domain's feature schema
3. ✅ Object1/Object2 exist in the domain's object list (or are "")
4. ✅ ExpName uses valid attribute names from the schema
5. ✅ Operator is one of: `>=`, `<=`, `==`, `between`, `in`
6. ✅ Recom format matches the Operator (number for >=/<=/==, X:Y for between, list for in)

---

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

**Step 1:** ✅ Rule identified (quantifiable constraint with threshold)
**Step 2:** Domain = Sheet Metal (keywords: "sheet thickness", "emboss", "cutout")
**Step 3:** Type 1 — Single expression, no conditions
**Step 4:** Feature1=Distance, Object1=Emboss, Object2=Cutout
**Step 5:** ExpName = `Distance.MinValue/SheetMetal.Thickness`
**Step 6:** Operator=`>=`, Recom=`4.0`

**Output:**
```
RuleCategory= Sheet Metal
Name = Emboss to Cutout Distance

Feature1 = Distance
Feature2 = ""
Object1 = Emboss
Object2 = Cutout

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 4.0
```

### Example B: Multi-Expression Rule (Type 2)

**Input:** "Recommended boss parameters: Outer Diameter to Inner Diameter ratio should be at least 2.0, and Height to Outer Diameter ratio should be at least 3.0."

**Step 1:** ✅ Rule identified
**Step 2:** Domain = Injection Molding (keywords: "boss", context of molding)
**Step 3:** Type 2 — Two expressions, same Feature1=Boss
**Step 4:** Feature1=Boss, Object1="", Object2=""
**Step 5:** ExpName1 = `Boss.OuterDiameterAtTop/Boss.InnerDiameterAtTop`, ExpName2 = `Boss.TotalHeight/Boss.OuterDiameterAtTop`
**Step 6:** Both `>=`, Recom1=`2.0`, Recom2=`3.0`

**Output:**
```
RuleCategory= Injection Molding
Name = Recommended Boss Parameters

Feature1 = Boss
Feature2 = ""
Object1 = ""
Object2 = ""

ExpName = Boss.OuterDiameterAtTop/Boss.InnerDiameterAtTop
Operator = >=
Recom = 2.0

ExpName = Boss.TotalHeight/Boss.OuterDiameterAtTop
Operator = >=
Recom = 3.0
```

### Example C: Conditional Rule (Type 6)

**Input:** "Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes."

**Step 1:** ✅ Rule identified
**Step 2:** Domain = Injection Molding (or Drilling depending on context)
**Step 3:** Type 6 — Conditional branching on Hole.IsBlind
**Step 4:** Feature1=Hole, Object1="", Object2=""
**Step 5-7:** Two constraint blocks based on IsBlind

**Output:**
```
RuleCategory= Injection Molding
Name = Hole Depth to Diameter Ratio

Feature1 = Hole
Feature2 = ""
Object1 = ""
Object2 = ""

Constraint : ExpName = Hole.IsBlind, Operator = ==, Value = True
{
        ExpName = Hole.TotalDepth/Hole.DiameterAtTop
        Operator = <=
        Recom = 2.0
}
Constraint : ExpName = Hole.IsBlind, Operator = ==, Value = False
{
        ExpName = Hole.TotalDepth/Hole.DiameterAtTop
        Operator = <=
        Recom = 4.0
}
```

### Example D: Boolean Rule (Type 4)

**Input:** "Ensure there are no sharp edges in the part"

**Step 1:** ✅ Rule identified (imperative + boolean constraint)
**Step 2:** Domain = Additive Manufacturing (or General depending on context)
**Step 3:** Type 4 — Boolean check
**Step 4:** Feature1="", Object1="", Object2="" (part-level check)
**Step 5:** ExpName = `PartEdge.IsSharp`
**Step 6:** Operator=`==`, Recom=`False`

**Output:**
```
RuleCategory= Additive Manufacturing
Name = Avoid Sharp Edges

Feature1 = ""
Feature2 = ""
Object1 = ""
Object2 = ""

ExpName = PartEdge.IsSharp
Operator = ==
Recom = False
```

### Example E: Set Membership Rule (Type 5)

**Input:** "Ensure that thread sizes conform to the recommended standard sizes: 1-64 UNC, 1-72 UNF, 2-56 UNC."

**Step 1:** ✅ Rule identified (set membership constraint)
**Step 2:** Domain = General
**Step 3:** Type 5 — Set membership
**Step 4:** Feature1=Thread, Object1="", Object2=""
**Step 5:** ExpName = `Thread.Size`
**Step 6:** Operator=`in`, Recom=`1-64 UNC, 1-72 UNF, 2-56 UNC`

**Output:**
```
RuleCategory= General
Name = Recommended Standard Thread Sizes

Feature1 = Thread
Feature2 = ""
Object1 = ""
Object2 = ""

ExpName = Thread.Size
Operator = in
Recom = 1-64 UNC, 1-72 UNF, 2-56 UNC
```

---

## Summary Statistics

| Metric | Count |
|:---|:---|
| Total formalized examples | 89 |
| Manufacturing domains | 10 (+2 sub-domains: Milling, Drilling) |
| Unique objects across all domains | 70+ |
| Unique operators | 5 (>=, <=, ==, between, in) |
| Type 1 (Simple) rules | ~52 |
| Type 2/3 (Multi-expression) rules | ~16 |
| Type 4 (Boolean) rules | ~10 |
| Type 5 (Set membership) rules | ~4 |
| Type 6 (Constraint) rules | ~5 |
| Type 7 (Nested constraint) rules | ~3 |
