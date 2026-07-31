"""
Registry for DFM rule structural buckets.

Each bucket defines:
- bucket_id: unique identifier
- description: human-readable explanation
- active_lists: which constraint lists are populated for this bucket type
- cues: keyword triggers for the regex fast-path classifier
- exemplars: representative sentences for the embedding similarity classifier
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class BucketDefinition:
    """Definition of a structural rule bucket."""
    bucket_id: str
    description: str
    active_lists: List[str]
    cues: List[str] = field(default_factory=list)
    exemplars: List[str] = field(default_factory=list)

BUCKET_REGISTRY: Dict[str, BucketDefinition] = {
    "SimpleValidation": BucketDefinition(
        bucket_id="SimpleValidation",
        description="One feature, one pass/fail expression (>, <, >=, <=, =).",
        active_lists=["ValidationParamList"],
        cues=[],
        exemplars=[
            "The side face angle of the pocket should be at least 13.0 degrees",
            "Boss outer radius at top should be at least 0.254",
            "Ensure minimum clearance is at least 0.1 units",
            "The draft angle should not exceed 5.0 degrees",
        ]
    ),
    "RangeValidation": BucketDefinition(
        bucket_id="RangeValidation",
        description="One feature with lower/upper range (between X and Y).",
        active_lists=["ValidationParamList"],
        cues=["between", "range"],
        exemplars=[
            "For a spoon feature the minimum height should be between 0.5 and 1.2 times sheet thickness",
            "Pin diameter should be between 2.0 and 5.0 mm",
            "Wall thickness must be in the range of 1.0 to 3.0 mm",
        ]
    ),
    "SetMembership": BucketDefinition(
        bucket_id="SetMembership",
        description="Field must be one of allowed values.",
        active_lists=["ValidationParamList"],
        cues=["one of", "from the following list", "any of"],
        exemplars=[
            "The partbody material should be from the following list - Steel, Aluminium",
            "Thread sizes conform to the recommended standard sizes: 1-64 UNC, 1-72 UNF",
            "Material type must be one of ABS, Nylon, Polycarbonate",
        ]
    ),
    "BooleanValidation": BucketDefinition(
        bucket_id="BooleanValidation",
        description="Yes/No or True/False state using .Is... parameter.",
        active_lists=["ValidationParamList"],
        cues=[],
        exemplars=[
            "In drilling, check if the holes are blind",
            "Avoid flat bottom holes",
            "Ensure the hole is threaded",
            "Check whether the bend has null radius",
        ]
    ),
    "FilteredValidation": BucketDefinition(
        bucket_id="FilteredValidation",
        description="Fixed applicability filter plus validation.",
        active_lists=["FilterParamList", "ValidationParamList"],
        cues=["where", "when"],
        exemplars=[
            "Ensure washer is present for fasteners engaging with Steel material",
            "For holes with diameter greater than 5mm, check the drill depth",
            "When the component type is bracket, ensure thickness is at least 2mm",
        ]
    ),
    "ConditionalValidation": BucketDefinition(
        bucket_id="ConditionalValidation",
        description="If/then branching with branch-aligned values.",
        active_lists=["ConditionParamList", "ValidationParamList"],
        cues=["otherwise"],
        exemplars=[
            "Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes",
            "Wall thickness should be 1.5 for small parts and 2.0 for large parts",
            "Draft angle must be 1.0 for internal surfaces and 0.5 for external surfaces",
        ]
    ),
    "AdditionalInfoValidation": BucketDefinition(
        bucket_id="AdditionalInfoValidation",
        description="Validation plus report-only fields.",
        active_lists=["ValidationParamList", "AdditionalParamList"],
        cues=["report", "additionally", "also check"],
        exemplars=[
            "Hole depth to diameter ratio should be at most 3.0, also check hole diameter at bottom additionally",
            "Check bend angle and additionally report bend radius",
            "Validate wall thickness and also report the draft angle for each instance",
        ]
    ),
    "DistanceRule": BucketDefinition(
        bucket_id="DistanceRule",
        description="Distance or clearance between two objects.",
        active_lists=["ValidationParamList"],
        cues=["distance", "clearance", "spacing"],
        exemplars=[
            "Distance between bridges should be at least 4.5 times sheet thickness",
            "Distance between hole and part edge should be at least 2.0 times nominal thickness",
            "Minimum clearance between cutout and bend should be 3mm",
            "Spacing between holes should not be less than 2 times diameter",
        ]
    ),
    "ModuleValidation": BucketDefinition(
        bucket_id="ModuleValidation",
        description="Module-level rule with no feature instance.",
        active_lists=["ValidationParamList"],
        cues=["module", "overall", "partbody", "machinability"],
        exemplars=[
            "Ensure the ratio of length to minimum outer diameter does not exceed 8.0",
            "The machinability index should be at least 0.5",
            "In sheetmetal module, the partbody material should be Steel",
            "Overall part length should not exceed 500mm",
        ]
    ),
    "MultiExpressionValidation": BucketDefinition(
        bucket_id="MultiExpressionValidation",
        description="Multiple checks on same feature/context.",
        active_lists=["ValidationParamList"],
        cues=[],
        exemplars=[
            "Card guide length should be at most 127.0 mm and opening angle should be at least 15.0 degrees",
            "Boss outer diameter ratio and height to diameter ratio should both be checked",
            "Rib height should be at most 3.0 times thickness and draft angle at least 0.5 degrees",
        ]
    ),
    "NestedConditionalValidation": BucketDefinition(
        bucket_id="NestedConditionalValidation",
        description="Multiple condition dimensions or branch tables.",
        active_lists=["ConditionParamList", "ValidationParamList"],
        cues=["table", "nested"],
        exemplars=[
            "Position tolerance depends on both part size and hole diameter",
            "Draft angle varies based on material type and wall height",
            "Minimum radius depends on whether the bend is internal or external and the material grade",
        ]
    ),
    "AllowedParamValidation": BucketDefinition(
        bucket_id="AllowedParamValidation",
        description="Validation value references another parameter via formula.",
        active_lists=["ValidationParamList"],
        cues=["times", "multiplied by"],
        exemplars=[
            "Spoon width should be at least 0.8 times sheet thickness",
            "Bend radius must be at least 1.5 times material thickness",
            "Hole spacing should be at least 3 times the hole diameter",
            "Minimum flange height should be three times the material thickness",
        ]
    ),
    "TypedValueValidation": BucketDefinition(
        bucket_id="TypedValueValidation",
        description="Material, color, type, name, string, thread class.",
        active_lists=["ValidationParamList"],
        cues=["colour", "color", "thread type", "thread class"],
        exemplars=[
            "In drilling, check if the hole thread type is UNF",
            "Ensure partface colour is blue",
            "Component name should be xyz",
            "The material type must be Carbon Steel",
        ]
    ),
    "HierarchicalParamValidation": BucketDefinition(
        bucket_id="HierarchicalParamValidation",
        description="Uses nested object access like Fastener.FirstEngagedComp.Material.",
        active_lists=["ValidationParamList"],
        cues=[],
        exemplars=[
            "Ensure fasteners are engaged with specific materials",
            "Check the first engaged component material of the fastener",
            "The bolt first engaged hole depth should be validated",
        ]
    ),
}

def get_bucket(bucket_id: str) -> Optional[BucketDefinition]:
    """Retrieve a bucket definition by its ID."""
    return BUCKET_REGISTRY.get(bucket_id)

def list_buckets() -> List[str]:
    """List all available bucket IDs."""
    return list(BUCKET_REGISTRY.keys())

def get_active_lists(bucket_id: str) -> List[str]:
    """Get the active lists for a specific bucket ID. Returns empty list if not found."""
    bucket = get_bucket(bucket_id)
    if bucket:
        return bucket.active_lists
    return []

def get_all_exemplars() -> Dict[str, List[str]]:
    """Get all exemplar sentences grouped by bucket ID. Used by the embedding classifier."""
    return {
        bid: bdef.exemplars
        for bid, bdef in BUCKET_REGISTRY.items()
        if bdef.exemplars
    }
