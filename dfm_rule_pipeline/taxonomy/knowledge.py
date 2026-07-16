"""General taxonomy knowledge used by the v3 formalization pipeline.

The constants in this module are taxonomy-level guidance, not exact rule
fallbacks. They describe reusable domain signals, expression aliases, and
compact examples so the LLM can generalize across BucketList-style rules.
"""

from typing import Dict, List, Tuple


LATEST_DOMAINS = {
    "Assembly",
    "Additive Manufacturing",
    "Die Casting",
    "Drilling",
    "General",
    "Injection Molding",
    "Milling",
    "SheetMetal",
    "Sheetmetal Forming",
    "Tubing",
    "Turning",
}


DOMAIN_ALIASES: Dict[str, str] = {
    "additive": "Additive Manufacturing",
    "additivemanufacturing": "Additive Manufacturing",
    "am": "Additive Manufacturing",
    "assembly": "Assembly",
    "diecast": "Die Casting",
    "diecasting": "Die Casting",
    "casting": "Die Casting",
    "drill": "Drilling",
    "drilling": "Drilling",
    "general": "General",
    "model": "General",
    "injectionmoulding": "Injection Molding",
    "injectionmolding": "Injection Molding",
    "moulding": "Injection Molding",
    "molding": "Injection Molding",
    "mill": "Milling",
    "milling": "Milling",
    "sheetmetal": "SheetMetal",
    "sheetmetals": "SheetMetal",
    "sheetmetalforming": "Sheetmetal Forming",
    "sheetmetalform": "Sheetmetal Forming",
    "smform": "Sheetmetal Forming",
    "tube": "Tubing",
    "tubing": "Tubing",
    "pipe": "Tubing",
    "turn": "Turning",
    "turning": "Turning",
    "lathe": "Turning",
}


TAXONOMY_TO_SCHEMA_DOMAIN = {
    "Additive Manufacturing": "Additive",
    "Assembly": "Assembly",
    "Die Casting": "Die Cast",
    "Drilling": "Drill",
    "General": "General",
    "Injection Molding": "Injection Moulding",
    "Milling": "Mill",
    "SheetMetal": "Sheetmetal",
    "Sheetmetal Forming": "SMForm",
    "Tubing": "Tubing",
    "Turning": "Turn",
}


DOMAIN_PROFILES: Dict[str, Dict[str, List[str]]] = {
    "SheetMetal": {
        "primary": [
            "sheet metal",
            "sheetmetal",
            "sheet thickness",
            "bend radius",
            "flange",
            "curl",
            "rolled hem",
            "hem",
            "bridge",
            "emboss",
            "gusset",
            "cutout",
            "slot",
            "slots",
            "opening",
            "louver",
            "spoon",
            "card guide",
            "extruded form",
            "extruded hole",
        ],
        "secondary": ["SheetMetal.Thickness", "material thickness", "bend relief", "teardrop", "inside surface"],
    },
    "Sheetmetal Forming": {
        "primary": [
            "sheet metal nominal thickness",
            "nominal thickness",
            "normal thickness",
            "smface",
            "sheetmetal forming",
            "forming",
        ],
        "secondary": ["SheetMetalForm.NominalThickness", "part edge", "return flange"],
    },
    "Additive Manufacturing": {
        "primary": ["additive", "3d printing", "3d printed", "print size", "overhang", "infill", "layer height"],
        "secondary": ["supported wall", "unsupported wall", "amface", "Additive.PrintSize", "sub process"],
    },
    "Assembly": {
        "primary": [
            "assembly",
            "component clearance",
            "clearance between components",
            "fastener",
            "washer",
            "bolt",
            "nut",
            "shank length",
            "thread pitch",
            "engagement",
        ],
        "secondary": ["interference", "bearing area", "first engaged"],
    },
    "Die Casting": {
        "primary": ["die cast", "diecast", "die casting", "casting", "mold wall", "mould wall"],
        "secondary": ["casting boss", "casting rib", "nominal thickness casting", "MoldWall"],
    },
    "Injection Molding": {
        "primary": ["injection", "molding", "moulding", "molded", "moulded", "cored hole", "lip", "imface"],
        "secondary": ["boss", "rib", "draft angle", "InjectionMolding.NominalThickness"],
    },
    "Milling": {
        "primary": ["milling", "machining", "pocket", "side face angle", "fillet", "bottom chamfer", "machinability"],
        "secondary": ["surface finish", "closed angle machining", "Pocket.SideFaceAngle", "Mill.Machinability"],
    },
    "Drilling": {
        "primary": [
            "drilling",
            "drilled",
            "counterbore",
            "counterbores",
            "drill depth",
            "thread depth",
            "entry and exit",
            "entry angle",
            "exit angle",
            "flat bottom",
            "partial hole",
            "partial exit",
            "wrap angle",
        ],
        "secondary": ["hole diameter", "hole depth", "thread size", "thread type", "position tolerance", "counterbore"],
    },
    "Turning": {
        "primary": ["turning", "turned parts", "lathe", "bored hole", "relief", "outer diameter", "internal corner radius"],
        "secondary": ["min outer diameter", "minimum outer diameter", "Turn.Body", "BoredHole", "TurnCorner"],
    },
    "Tubing": {
        "primary": ["tube", "tubing", "pipe", "bend radius tube", "overlap length", "clearance between tubes"],
        "secondary": ["common radius", "straight length", "Tube.OuterDiameter", "Tube.IsUniformBendRadius"],
    },
    "General": {
        "primary": ["pmi", "thread size", "thread class", "thread unit", "preferred materials", "preferred material"],
        "secondary": ["wall thickness", "PartBody.Material", "Thread.Size", "PartEdge.IsSharp"],
    },
}


DISAMBIGUATION_PATTERNS: List[Tuple[str, List[str], List[str]]] = [
    ("Sheetmetal Forming", ["sheetmetal forming", "sheet metal forming", "smface"], []),
    ("Die Casting", ["die cast", "diecast", "die casting", "mold wall", "mould wall"], []),
    ("Injection Molding", ["injection", "molding", "moulding", "molded", "moulded", "imface", "cored hole"], []),
    ("Drilling", ["drilled", "counterbore", "counterbores", "drill depth", "thread depth", "entry and exit", "entry angle", "exit angle", "flat bottom", "partial hole", "partial exit"], []),
    ("Milling", ["pocket", "machining", "milling", "machinability", "surface finish"], ["drilled", "drill depth", "entry and exit", "entry angle", "exit angle", "partial exit"]),
    ("Tubing", ["tube", "tubing", "pipe"], []),
    ("Turning", ["turned parts", "turning", "lathe", "bored hole", "min outer diameter", "minimum outer diameter"], []),
    ("Additive Manufacturing", ["additive", "3d printing", "3d printed", "print size", "overhang", "infill"], []),
    ("Assembly", ["assembly", "fastener", "component clearance", "clearance between components", "washer", "bolt"], []),
    ("SheetMetal", ["sheet metal", "sheetmetal", "sheet thickness", "flange", "hem", "bridge", "emboss", "cutout", "slot", "slots"], []),
    ("General", ["pmi", "preferred materials", "thread class", "thread unit"], []),
]


THICKNESS_VARIABLE_BY_DOMAIN = {
    "SheetMetal": "SheetMetal.Thickness",
    "Sheetmetal Forming": "SheetMetalForm.NominalThickness",
    "Die Casting": "PartBody.NominalThickness",
    "Injection Molding": "InjectionMolding.NominalThickness",
    "Milling": "PartBody.NominalThickness",
    "Turning": "PartBody.NominalThickness",
    "General": "PartBody.NominalThickness",
}


GLOBAL_PATH_ALIASES = {
    "Partbody.Material": "PartBody.Material",
    "PartBody.Mat": "PartBody.Material",
    "Material": "PartBody.Material",
    "Colour": "PartFace.Color",
    "Color": "PartFace.Color",
    "PartFace.Colour": "PartFace.Color",
    "Part.Color": "PartFace.Color",
    "Part.Colour": "PartFace.Color",
}


PATH_ALIASES_BY_DOMAIN: Dict[str, Dict[str, str]] = {
    "SheetMetal": {
        "ModuleParams.Thickness": "SheetMetal.Thickness",
        "ModuleParams.Material": "PartBody.Material",
        "Sheetmetal.Thickness": "SheetMetal.Thickness",
        "Sheetmetal.Material": "PartBody.Material",
        "Opening.Length": "Slot.Length",
        "SlotEdge.Length": "Slot.Length",
    },
    "Sheetmetal Forming": {
        "ModuleParams.NormalThickness": "SheetMetalForm.NominalThickness",
        "ModuleParams.NominalThickness": "SheetMetalForm.NominalThickness",
        "SheetmetalForm.NormalThickness": "SheetMetalForm.NominalThickness",
        "SheetmetalForm.NominalThickness": "SheetMetalForm.NominalThickness",
        "SMFace.NormalThickness": "SheetMetalForm.NominalThickness",
    },
    "Injection Molding": {
        "ModuleParams.NominalThickness": "InjectionMolding.NominalThickness",
        "Mold.NominalThickness": "InjectionMolding.NominalThickness",
        "Mould.NominalThickness": "InjectionMolding.NominalThickness",
    },
    "Die Casting": {
        "ModuleParams.NominalThickness": "PartBody.NominalThickness",
        "MoldWall.Thickness": "MoldWall.MinValue",
    },
    "Milling": {
        "ModuleParams.Machinability": "Mill.Machinability",
        "Milling.Machinability": "Mill.Machinability",
    },
    "Turning": {
        "LengthToMinOuterDiameterRatio": "Turn.Body.Length/Turn.Body.MinOuterDiameter",
        "Body.Length/Body.MinOuterDiameter": "Turn.Body.Length/Turn.Body.MinOuterDiameter",
        "Body.Length / Body.MinOuterDiameter": "Turn.Body.Length/Turn.Body.MinOuterDiameter",
        "ModuleParams.Body.Length/ModuleParams.Body.MinOuterDiameter": "Turn.Body.Length/Turn.Body.MinOuterDiameter",
    },
    "Additive Manufacturing": {
        "ModuleParams.PrintSize": "AdditiveManufacturing.PrintSize",
        "ModuleParams.MPPrintSize": "AdditiveManufacturing.PrintSize",
        "Additive.PrintSize": "AdditiveManufacturing.PrintSize",
    },
}


OBJECT_ALIASES_BY_DOMAIN: Dict[str, Dict[str, str]] = {
    "Sheetmetal Forming": {
        "SMFace": "Part Edge",
        "PartEdge": "Part Edge",
        "Part edge": "Part Edge",
        "Hole": "SimpleHole",
    },
    "SheetMetal": {
        "Part Edge": "PartEdge",
        "Part edge": "PartEdge",
        "Slot Edge": "Slot",
        "SlotEdge": "Slot",
        "Opening": "Slot",
    },
}


DOMAIN_SCHEMA_EXTENSIONS: Dict[str, Dict[str, List[str]]] = {
    "SheetMetal": {
        "Slot": ["Length", "Width"],
    },
    "General": {
        "Wall": ["MinThickness", "MaxThickness", "Thickness"],
    }
}


OBJECT_TEXT_ALIASES: Dict[str, List[str]] = {
    "Bend": ["bend", "bends"],
    "Bridge": ["bridge", "bridges"],
    "Hem": ["hem", "hems"],
    "OpenHem": ["open hem", "open hems"],
    "ClosedHem": ["closed hem", "closed hems"],
    "RolledHem": ["rolled hem", "rolled hems"],
    "TearDropHem": ["teardrop hem", "teardrop hems", "tear drop hem", "tear drop hems"],
    "Flange": ["flange", "flanges", "return flange", "return flanges"],
    "EdgeFlange": ["edge flange", "edge flanges", "return flange", "return flanges"],
    "Cutout": ["cutout", "cutouts", "slot", "slots", "opening", "openings"],
    "SimpleCutout": ["simple cutout", "slot", "slots", "opening", "openings"],
    "Slot": ["slot", "slots", "slot edge", "edge of a slot", "opening", "openings"],
    "PartEdge": ["part edge", "part edges"],
    "Part Edge": ["part edge", "part edges"],
    "Hole": ["hole", "holes"],
    "SimpleHole": ["hole", "holes", "simple hole", "simple holes"],
    "Component": ["component", "components"],
    "Fastener": ["fastener", "fasteners"],
    "Tube": ["tube", "tubes", "pipe", "pipes"],
}


NON_PHYSICAL_OBJECTS = {
    "ModuleParams",
    "SheetMetal",
    "Sheetmetal",
    "SheetMetalForm",
    "SheetmetalForming",
    "InjectionMolding",
    "AdditiveManufacturing",
    "PartBody",
    "PartFace",
}


MODULE_EXPRESSION_PREFIXES = {
    "PartBody.",
    "PartFace.",
    "Turn.Body.",
    "Mill.",
    "Milling.",
    "AdditiveManufacturing.",
}


STRUCTURAL_TYPE_TO_BUCKET = {
    "simple_single_expression": "FeatureSimpleValidation",
    "multi_expression_same_context": "MultiExpressionValidation",
    "deprecated_numbered_multi_expression": "MultiExpressionValidation",
    "boolean_state": "FeatureBooleanValidation",
    "set_membership": "FeatureSetMembership",
    "filtered_applicability": "FilteredValidation",
    "conditional_branch": "ConditionalValidation",
    "nested_conditional": "NestedConditionalValidation",
    "distance_interaction": "DistanceRule",
    "module_scope": "ModuleValidation",
    "additional_info": "AdditionalInfoValidation",
}


PROMPT_EXAMPLES = [
    {
        "rule": "The side face angle of the pocket should be at least 13.0 degrees.",
        "domain": "Milling",
        "bucket": "FeatureSimpleValidation",
        "shape": "Feature Pocket; Validation Pocket.SideFaceAngle >= 13.0.",
    },
    {
        "rule": "For a spoon feature the minimum height should be between 0.5 and 1.2 times sheet thickness.",
        "domain": "SheetMetal",
        "bucket": "FeatureRangeValidation",
        "shape": "Feature Spoon; use paired range operators on Spoon.Height/SheetMetal.Thickness.",
    },
    {
        "rule": "The partbody material should be from the following list - Steel, Aluminium.",
        "domain": "SheetMetal",
        "bucket": "FeatureSetMembership",
        "shape": "Module; Validation PartBody.Material ANY with each material as a separate value item.",
    },
    {
        "rule": "In drilling, check if the hole's thread type is UNF.",
        "domain": "Drilling",
        "bucket": "FeatureTypedValueValidation",
        "shape": "Feature Hole; Validation Hole.ThreadType = UNF.",
    },
    {
        "rule": "In drilling, check if the holes are blind.",
        "domain": "Drilling",
        "bucket": "FeatureBooleanValidation",
        "shape": "Feature Hole; Validation Hole.IsBlind = Yes.",
    },
    {
        "rule": "For a spoon feature the minimum width should be at least 0.8 times sheet thickness.",
        "domain": "SheetMetal",
        "bucket": "FeatureAllowedParamExpression",
        "shape": "Feature Spoon; Validation Spoon.Width >= 0.8*SheetMetal.Thickness; AllowedParams contains SheetMetal.Thickness.",
    },
    {
        "rule": "In an assembly, ensure washer is present for fasteners engaging with steel.",
        "domain": "Assembly",
        "bucket": "FilteredValidation",
        "shape": "Feature Fastener; filter Fastener.FirstEngagedComp.Material = Steel; validate Fastener.IsWasherPresent = Yes.",
    },
    {
        "rule": "Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes.",
        "domain": "Injection Molding",
        "bucket": "ConditionalValidation",
        "shape": "Feature Hole; condition Hole.IsBlind has two branches; validation Hole.TotalDepth/Hole.DiameterAtTop values align by branch.",
    },
    {
        "rule": "Hole depth to diameter ratio should vary by blind state; also check hole diameter at bottom.",
        "domain": "Injection Molding",
        "bucket": "AdditionalInfoValidation",
        "shape": "Use AdditionalParamList for Hole.DiameterAtBot; do not make it a pass/fail validation.",
    },
    {
        "rule": "Distance between hole and part edge should be at least 2.0 times sheet metal nominal thickness.",
        "domain": "Sheetmetal Forming",
        "bucket": "DistanceRule",
        "shape": "Feature1 Distance; Object1 SimpleHole, Object2 Part Edge; validate Distance.MinValue >= 2.0*SheetMetalForm.NominalThickness.",
    },
    {
        "rule": "The ratio of the length to the minimum outer diameter of turned parts should not exceed 8.0.",
        "domain": "Turning",
        "bucket": "ModuleValidation",
        "shape": "Module; Validation Turn.Body.Length/Turn.Body.MinOuterDiameter <= 8.0.",
    },
    {
        "rule": "Bend radius should be at least 14.2748 units for tubes with an outer diameter of 6.35 units.",
        "domain": "Tubing",
        "bucket": "FilteredValidation",
        "shape": "Feature Bend; filter Tube.OuterDiameter = 6.35; validate Bend.Radius >= 14.2748.",
    },
    {
        "rule": "For pins with height between 0 and 10 units, recommended pin diameter should be between 0.5 and 1.5 units.",
        "domain": "Injection Molding",
        "bucket": "ConditionalValidation",
        "shape": "Condition Pin.TotalHeight uses range operators; Validation Pin.DiameterAtTop also uses range operators.",
    },
    {
        "rule": "The entry and exit angles for holes should be 0.0 degrees.",
        "domain": "Drilling",
        "bucket": "MultiExpressionValidation",
        "shape": "Feature Hole; emit separate validation entries for Hole.EntryAngle and Hole.ExitAngle.",
    },
]
