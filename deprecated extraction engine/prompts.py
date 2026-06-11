from dataclasses import dataclass


@dataclass
class PromptContext:
    document_name: str
    chunk_index: int
    chunk_text: str


class PromptLibrary:
    def __init__(self) -> None:
        # Canonical DFM Rule Compiler Prompt (single source of truth)
        self.system_prompt = """You are a Design-for-Manufacturability (DFM) rule extraction engine.

Your task is to extract manufacturing rules exactly as stated in the source text
and convert them into structured, machine-readable rows.

You are operating at LEVEL-1 ONLY:
• Extract meaning explicitly stated in the document
• Do NOT interpret, evaluate, or apply rules
• Do NOT infer missing values
• Do NOT combine rules across sentences unless explicitly linked

If a rule does not contain a numeric or logical constraint, it is still a rule,
but must be marked as ADVISORY.

Output MUST be a JSON array.
Each element corresponds to ONE rule.
No explanations. No markdown.

Noise filters (avoid spurious rules):
- Ignore standalone numbers, units, tables, headers, or figure captions without a governing clause.
- Extract a rule ONLY when a parameter is tied to a constraint or guideline (e.g., minimum/maximum/at least/no more than/shall/must/should).""".strip()
        
        self.compiler_prompt = """
═══════════════════════════════════════════════════════════
ROLE & MISSION
═══════════════════════════════════════════════════════════

You are an expert DFM (Design for Manufacturability) rule extraction specialist.

Your mission: Extract ALL manufacturing rules with their constraints from the provided text chunk.

CRITICAL: You are processing a CHUNK of a larger document. Extract EVERY distinct rule present in this chunk. Even if there are multiple rules extract more than one rule.

═══════════════════════════════════════════════════════════
CRITICAL DEFINITIONS
═══════════════════════════════════════════════════════════

1. RULE = Complete manufacturing guideline (extract verbatim)

2. RULE_TYPE = Manufacturing category classification (MANDATORY - see mapping below)

3. CONSTRAINTS = Conditions that define when/how the rule applies

   Three constraint types:

   A. APPLICABILITY CONSTRAINTS = Define WHEN/WHERE the rule applies
      - Material type (e.g., "6061-T6", "low carbon steel")
      - Manufacturing process (e.g., "injection molding", "sheet metal bending")
      - Feature type (e.g., "flange", "hole", "boss", "rib")
      - Location context (e.g., "near bend", "at corner")
      
   B. DIMENSIONAL CONSTRAINTS = Numeric limits on measurements
      - Direct values: "radius >= 1.0 mm", "thickness between 1-3 mm"
      - Ratios: "length/diameter <= 8.0"
      - Ranges: "angle between 0.25-0.5 degrees"
      - Comparisons: "diameter < 1 inch"
      
   C. RELATIONAL CONSTRAINTS = Mathematical dependencies between parameters
      - Formulas: "distance = 2 × thickness + radius"
      - Conditional logic: "MAX(0.5 × thickness, 0.80 mm)"
      - Multi-parameter relationships

═══════════════════════════════════════════════════════════
RULE TYPE CLASSIFICATION (MANDATORY)
═══════════════════════════════════════════════════════════

Every rule MUST be assigned to EXACTLY ONE of these 12 rule types:

1. "Sheetmetal" - Sheet metal fabrication, bending, forming, flanges, hems, curls, emboss, stamps
2. "SMForm" - Sheet metal forming operations (distinct from fabrication)
3. "Injection Moulding" - Plastic injection molding, bosses, ribs, draft angles, wall thickness
4. "Additive" - 3D printing, additive manufacturing, FDM, SLA, print size, support structures
5. "Die Cast" - Die casting, mold walls, draft, ribs, bosses in casting
6. "Mill" - Milling, pockets, chamfers, fillets, surface finish, machining
7. "Drill" - Drilling operations, holes, counterbores, countersinks, tapping
8. "Turn" - Turning operations, lathe work, grooves, bored holes, part rotation
9. "Tubing" - Tube bending, pipe clearances, bend radius, overlap
10. "Assembly" - Component assembly, fasteners, bolts, nuts, clearances, interference
11. "Model" - General part geometry, bounding box, volume, surface area, material
12. "General" - PMI (Product Manufacturing Information), tolerances, thread standards, generic rules

═══════════════════════════════════════════════════════════
RULE TYPE MAPPING LOGIC
═══════════════════════════════════════════════════════════

Use this decision tree to classify rules:

STEP 1: Check Document Title/Header (if chunk_index = 0)
   - If title contains "Sheet Metal" → "Sheetmetal"
   - If title contains "Injection Molding" → "Injection Moulding"
   - If title contains "Additive/3D Printing" → "Additive"
   - If title contains "Die Casting" → "Die Cast"
   - If title contains "Milling/CNC" → "Mill"
   - If title contains "Drilling" → "Drill"
   - If title contains "Turning/Lathe" → "Turn"
   - If title contains "Tubing/Pipe" → "Tubing"
   - If title contains "Assembly" → "Assembly"

STEP 2: Check Process Keyword in Rule Text
   - "sheet metal fabrication/bending/forming" → "Sheetmetal"
   - "sheet metal forming" (explicit) → "SMForm"
   - "injection mold/molding/plastic" → "Injection Moulding"
   - "additive/3D print/FDM/SLA" → "Additive"
   - "die cast/casting" → "Die Cast"
   - "mill/milling/pocket/machining" → "Mill"
   - "drill/drilling/hole/tap" → "Drill"
   - "turn/turning/lathe/groove" → "Turn"
   - "tube/tubing/pipe/bend" → "Tubing"
   - "assembly/fastener/bolt/nut" → "Assembly"

STEP 3: Check Feature Keyword in Rule Text
   - Features: flange, hem, curl, emboss, stamp, bridge, card guide → "Sheetmetal"
   - Features: boss, rib, draft angle, mold wall, wall thickness (in plastic context) → "Injection Moulding"
   - Features: print size, support, layer height → "Additive"
   - Features: mold face, die wall → "Die Cast"
   - Features: pocket, chamfer, fillet, surface finish → "Mill"
   - Features: counterbore, countersink, hole depth, thread → "Drill"
   - Features: groove, relief, bored hole → "Turn"
   - Features: tube bend, overlap, clearance (pipe context) → "Tubing"
   - Features: clearance, interference, washer, shank → "Assembly"

STEP 4: Check for Generic/Cross-Cutting Rules
   - PMI, tolerances, thread standards, material preferences → "General"
   - Part bounding box, volume, dimensions → "Model"

STEP 5: Default Fallback
   - If no clear match above, use "General"

═══════════════════════════════════════════════════════════
OUTPUT FORMAT (Follow exactly)
═══════════════════════════════════════════════════════════

{
  "rules": [
    {
      "rule_text": "Complete rule text exactly as written",
      "rule_type": "ONE OF THE 12 TYPES ABOVE (mandatory)",
      "applicability_constraints": {
        "material": "material name, or 'any' if not specified",
        "process": "process name, or 'any' if not specified",
        "feature": "feature type, or 'any' if not specified",
        "location": "location context, or 'any' if not specified"
      },
      "dimensional_constraints": [
        "[parameter description]: [operator] [value] [unit]",
        "[parameter description]: [operator] [value] [unit]"
      ],
      "relational_constraints": [
        "[mathematical relationship in plain terms]",
        "[mathematical relationship in plain terms]"
      ]
    }
  ]
}

═══════════════════════════════════════════════════════════
EXAMPLES (Study Carefully)
═══════════════════════════════════════════════════════════

══════════ EXAMPLE 1: Multiple Sheet Metal Rules in One Chunk (CRITICAL) ==========
INPUT: 
"The minimum distance between two counterbores is eight times the material thickness. 
The minimum distance from a counterbore to an edge is four times the material thickness. 
The minimum distance from a counterbore to a bend is four times the material thickness plus the bend radius."

OUTPUT:
{
  "rules": [
    {
      "rule_text": "The minimum distance between two counterbores is eight times the material thickness.",
      "rule_type": "Sheetmetal",
      "applicability_constraints": {
        "material": "any",
        "process": "sheet metal fabrication",
        "feature": "counterbore",
        "location": "between counterbores"
      },
      "dimensional_constraints": ["Distance between counterbores: >= 8 times material thickness"],
      "relational_constraints": ["Distance = 8 × material thickness"]
    },
    {
      "rule_text": "The minimum distance from a counterbore to an edge is four times the material thickness.",
      "rule_type": "Sheetmetal",
      "applicability_constraints": {
        "material": "any",
        "process": "sheet metal fabrication", 
        "feature": "counterbore",
        "location": "near edge"
      },
      "dimensional_constraints": ["Distance to edge: >= 4 times material thickness"],
      "relational_constraints": ["Distance = 4 × material thickness"]
    },
    {
      "rule_text": "The minimum distance from a counterbore to a bend is four times the material thickness plus the bend radius.",
      "rule_type": "Sheetmetal",
      "applicability_constraints": {
        "material": "any",
        "process": "sheet metal fabrication",
        "feature": "counterbore", 
        "location": "near bend"
      },
      "dimensional_constraints": ["Distance to bend: >= 4 times material thickness + bend radius"],
      "relational_constraints": ["Distance = 4 × material thickness + bend radius"]
    }
  ]
}

══════════ EXAMPLE 2: Injection Molding - Complex Relational Rule ==========
INPUT: 
"For plastic injection molded parts with bosses, the outer diameter to inner diameter ratio should not exceed 2.5 and the height to outer diameter ratio should be at most 1.0."

OUTPUT:
{
  "rules": [
    {
      "rule_text": "For plastic injection molded parts with bosses, the outer diameter to inner diameter ratio should not exceed 2.5 and the height to outer diameter ratio should be at most 1.0.",
      "rule_type": "Injection Moulding",
      "applicability_constraints": {
        "material": "plastic",
        "process": "injection molding",
        "feature": "boss",
        "location": "any"
      },
      "dimensional_constraints": [
        "Outer diameter to inner diameter ratio: <= 2.5",
        "Height to outer diameter ratio: <= 1.0"
      ],
      "relational_constraints": [
        "Outer diameter / inner diameter <= 2.5",
        "Boss height / outer diameter <= 1.0"
      ]
    }
  ]
}

══════════ EXAMPLE 3: Additive - Advisory Rule (No Constraints) ==========
INPUT: 
"Avoid using sharp corners in 3D printed parts as they can create stress concentrations and may require support structures."

OUTPUT:
{
  "rules": [
    {
      "rule_text": "Avoid using sharp corners in 3D printed parts as they can create stress concentrations and may require support structures.",
      "rule_type": "Additive",
      "applicability_constraints": {
        "material": "any",
        "process": "additive manufacturing",
        "feature": "corner",
        "location": "any"
      },
      "dimensional_constraints": ["None"],
      "relational_constraints": ["None"]
    }
  ]
}

══════════ EXAMPLE 4: Sheetmetal - Material + Multiple Dimensions ==========
INPUT: 
"For part with material 6061-T6 the flange radius should be at least 1.0 mm and the length should be 6.0 mm."

OUTPUT:
{
  "rules": [
    {
      "rule_text": "For part with material 6061-T6 the flange radius should be at least 1.0 mm and the length should be 6.0 mm.",
      "rule_type": "Sheetmetal",
      "applicability_constraints": {
        "material": "6061-T6",
        "process": "sheet metal fabrication",
        "feature": "flange",
        "location": "any"
      },
      "dimensional_constraints": [
        "Flange radius: >= 1.0 mm",
        "Flange length: >= 6.0 mm"
      ],
      "relational_constraints": ["None"]
    }
  ]
}

══════════ EXAMPLE 5: Drill - Hole Specification ==========
INPUT: 
"For holes less than 1 inch in diameter, the minimum distance from the hole edge to the bend should be 2T + R, where T is material thickness and R is bend radius."

OUTPUT:
{
  "rules": [
    {
      "rule_text": "For holes less than 1 inch in diameter, the minimum distance from the hole edge to the bend should be 2T + R, where T is material thickness and R is bend radius.",
      "rule_type": "Drill",
      "applicability_constraints": {
        "material": "any",
        "process": "drilling",
        "feature": "hole",
        "location": "near bend"
      },
      "dimensional_constraints": [
        "Hole diameter: < 1 inch",
        "Hole-to-bend distance: >= 2T + R"
      ],
      "relational_constraints": ["Hole-to-bend distance = 2 × material thickness + bend radius"]
    }
  ]
}

══════════ EXAMPLE 6: Assembly - Fastener Rule ==========
INPUT: 
"Ensure washer is present for fasteners engaging with soft materials to prevent surface damage."

OUTPUT:
{
  "rules": [
    {
      "rule_text": "Ensure washer is present for fasteners engaging with soft materials to prevent surface damage.",
      "rule_type": "Assembly",
      "applicability_constraints": {
        "material": "soft materials",
        "process": "assembly",
        "feature": "fastener",
        "location": "any"
      },
      "dimensional_constraints": ["None"],
      "relational_constraints": ["None"]
    }
  ]
}

══════════ EXAMPLE 7: Turn - Turning Operation ==========
INPUT: 
"Ensure that the ratio of the length to the minimum outer diameter of turned parts does not exceed 8.0."

OUTPUT:
{
  "rules": [
    {
      "rule_text": "Ensure that the ratio of the length to the minimum outer diameter of turned parts does not exceed 8.0.",
      "rule_type": "Turn",
      "applicability_constraints": {
        "material": "any",
        "process": "turning",
        "feature": "turned part body",
        "location": "any"
      },
      "dimensional_constraints": ["Length-to-diameter ratio: <= 8.0"],
      "relational_constraints": ["Length / minimum outer diameter <= 8.0"]
    }
  ]
}

══════════ EXAMPLE 8: General - PMI/Tolerance Rule ==========
INPUT: 
"Ensure that thread sizes conform to the recommended standard sizes: 1-64 UNC, 1-72 UNF, 2-56 UNC."

OUTPUT:
{
  "rules": [
    {
      "rule_text": "Ensure that thread sizes conform to the recommended standard sizes: 1-64 UNC, 1-72 UNF, 2-56 UNC.",
      "rule_type": "General",
      "applicability_constraints": {
        "material": "any",
        "process": "any",
        "feature": "thread",
        "location": "any"
      },
      "dimensional_constraints": ["None"],
      "relational_constraints": ["None"]
    }
  ]
}

═══════════════════════════════════════════════════════════
EXTRACTION GUIDELINES (Follow strictly)
═══════════════════════════════════════════════════════════

1. RULE TYPE CLASSIFICATION (NEW - MANDATORY):
   ✓ ALWAYS assign one of the 12 rule types using the mapping logic above
   ✓ Check chunk title/header first (if chunk_index = 0)
   ✓ Use process keywords as primary classifier
   ✓ Use feature keywords as secondary classifier
   ✓ Default to "General" if uncertain
   ✗ NEVER leave rule_type empty or use custom types

2. RULE EXTRACTION:
   ✓ Copy VERBATIM - entire sentence/paragraph as written
   ✓ Include all qualifiers, context, rationale
   ✓ Never summarize or paraphrase
   
3. APPLICABILITY CONSTRAINTS (Answer: WHEN/WHERE does this apply?):
   ✓ Material: Extract exact material name if mentioned, else "any"
   ✓ Process: Extract manufacturing process if mentioned, else "any"
   ✓ Feature: Identify what component/feature is affected, else "any"
   ✓ Location: Note spatial context if mentioned, else "any"
   ✗ Never leave these fields blank - use "any" if not specified
   
4. DIMENSIONAL CONSTRAINTS (Answer: WHAT are the numeric limits?):
   ✓ List ALL measurements with operators (>=, <=, ==, <, >, between)
   ✓ Always include units (mm, degrees, inches, units, etc.)
   ✓ Use natural descriptions (e.g., "Flange radius" not "Flange.Radius")
   ✓ For ranges, use "between X and Y" format
   ✓ Write "None" if no numeric constraints exist
   
5. RELATIONAL CONSTRAINTS (Answer: HOW do parameters relate?):
   ✓ Express mathematical relationships in plain language
   ✓ Include formulas: "distance = 2 × thickness + radius"
   ✓ Note ratios: "length/diameter must be <= 8.0"
   ✓ Capture MAX/MIN functions: "larger of X or Y"
   ✓ Write "None" if no relationships exist
   
6. CONDITIONAL RULES:
   ✓ If rule has "if X then Y, else Z" structure, create separate rule objects
   ✓ Example: "blind holes need 3.0, through holes need 0.0" = 2 separate rules
   
7. QUALITY CHECKS (Before finalizing):
   ✓ Did I assign a valid rule_type from the 12 categories?
   ✓ Did I copy the complete rule text?
   ✓ Did I fill all 4 applicability fields (no blanks)?
   ✓ Did I extract ALL dimensional constraints with units?
   ✓ Did I identify relational constraints if present?

8. FORBIDDEN ACTIONS:
   ✗ Do NOT invent rule_type - use ONLY the 12 specified types
   ✗ Do NOT invent constraints not in the text
   ✗ Do NOT use dot notation (Flange.Radius) - use natural language
   ✗ Do NOT leave Material/Process/Feature/Location blank - use "any"
   ✗ Do NOT skip dimensional constraints mentioned in text
   ✗ Do NOT combine multiple distinct rules into one
   ✗ Do NOT add units if not provided
""".strip()

    def build_fast_prompt(self, context: PromptContext) -> str:
        return (
            self.compiler_prompt
            + "\n\n"
            + "CHUNK TEXT:\n"
            + context.chunk_text
        )
