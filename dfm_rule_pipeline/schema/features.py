assembly = """
    Object: Component
    Attributes: Name, FileName, Identifier, ParentName, ParentFileName,ParentIdentifier,Type

    Object: Distance
    Attributes: Value, CustomValue

    Object: Interference
    Attributes: IsInterfering, Volume

    Object: Clearance
    Attribute: MinValue, IsTouching, IsInterfering

    Object: Fastener
    Attributes: Type, Name, IsWasherPresent, IsFirstEngagedCompInContact, WrenchFlatDiameter, BearingArea, MinSupportWidth, ContactWidth, FirstEngagedComp, ScrewDiameter, FirstEngagedHole

    Object: Bolt
    Attributes: Size, Name, IsWasherPresent, IsFirstEngagedCompInContact, WrenchFlatDiameter, BearingArea, MinSupportWidth, ContactWidth, FirstEngagedComp, ScrewDiameter, FirstEngagedHole, ClearanceHoleDepth, ShankLength, ThreadPitch, ExtendedThreadLength, LastEngagedHole, IsThreaded, Length

    Object: Nut
    Attributes: Name, IsWasherPresent, IsFirstEngagedCompInContact, WrenchFlatDiameter, BearingArea, MinSupportWidth, ContactWidth, FirstEngagedComp, ScrewDiameter, FirstEngagedHole
"""

additive = """
    Object: AMFace
    Attributes: MinThickness, MaxThickness, MinGap

    Object: Pin
    Attributes: RadiusAtTop, DiameterAtTop, TotalHeight, IsPartial, IsTopSpherical

    Object: Hole
    Attributes: RadiusAtTop, DiameterAtTop, RadiusAtBot, DiameterAtBot, TotalDepth, IsBlind, IsPartial, IsTapered, TaperAngle

    Object: Text
    Attributes: Height, Width

    Object: Wall
    Attributes: MinThickness, MaxThickness, IsSupported

    Object: PMI
    Attributes: Angularity

    Object: ModuleParams
    Attributes: NominalThickness, MPPrintSize (PrintSize), SubProcessType

    Object: PrintSize
    Attributes: Length, Height, Width
"""

diecast = """
    Object: MoldFace
    Attributes: MinThickness, MaxThickness, MoldWallThickness, DraftAngle, MoldClassificationType, IsUndercut, IsFillet, Height

    Object: Boss
    Attributes: OuterRadiusAtTop, OuterDiameterAtTop, OuterRadiusAtBot, OuterDiameterAtBot, InnerRadiusAtTop, InnerDiameterAtTop, InnerRadiusAtBot, InnerDiameterAtBot, TotalHeight, IsPartial, OuterSurfaceDraftAngle, InnerSurfaceDraftAngle, WrapAngle, IsChamferAtTop

    Object: Rib
    Attributes: DraftAngle, ProfileArea, RadiusAtBot, Height, TopThickness, ThicknessAtBotWithFillet, ThicknessAtBot

    Object: WallThickness
    Attributes: MinValue, MaxValue

    Object: MoldWall
    Attributes: MinValue, Height

    Object: Draft
    Attributes: Angle, Type, Height

    Object: Text
    Attributes: Height, DraftAngle
"""

drill = """
Object: Hole
    Attributes: Radius, Diameter, IsBlind, IsThreaded, ThreadDepth, DrillDepth, ThreadSize, ThreadDrillDiameter, ThreadType, EntryAngle, ExitAngle, IsFlatBottom, IsPartial, WrapAngle, TipDepth, TipAngle, NumElemHole, TotalDepth, PositionTolerance

    Object: HoleSegment
    Attributes: Radius, Diameter, Depth, TaperAngle, IsTapered, IsPartial, WrapAngle, PositionTolerance

    Object: SimpleHole
    Attributes: Radius, Diameter, IsBlind, IsThreaded, ThreadDepth, DrillDepth, ThreadSize, ThreadDrillDiameter, ThreadType, EntryAngle, ExitAngle, IsFlatBottom, IsPartial, WrapAngle, TipDepth, TipAngle, NumElemHole, TotalDepth, TaperAngle, IsTapered, Depth, PositionTolerance

    Object: CompoundHole
    Attributes: Radius, Diameter, IsBlind, IsThreaded, ThreadDepth, DrillDepth, ThreadSize, ThreadDrillDiameter, ThreadType, EntryAngle, ExitAngle, IsFlatBottom, IsPartial, WrapAngle, TipDepth, TipAngle, NumElemHole, TotalDepth, Depth, PositionTolerance

    Object: CBHole
    Attributes: Radius, Diameter, IsBlind, IsThreaded, ThreadDepth, DrillDepth, ThreadSize, ThreadDrillDiameter, ThreadType, EntryAngle, ExitAngle, IsFlatBottom, IsPartial, WrapAngle, TipDepth, TipAngle, NumElemHole, TotalDepth, Depth, BoreRadius, BoreDiameter, BoreDepth, PositionTolerance

    Object: CSHole
    Attributes: Radius, Diameter, IsBlind, IsThreaded, ThreadDepth, DrillDepth, ThreadSize, ThreadDrillDiameter, ThreadType, EntryAngle, ExitAngle, IsFlatBottom, IsPartial, WrapAngle, TipDepth, TipAngle, NumElemHole, TotalDepth, Depth, SunkRadius, SunkDiameter, SunkDepth, SunkAngle, PositionTolerance

    Object: CDHole
    Attributes: Radius, Diameter, IsBlind, IsThreaded, ThreadDepth, DrillDepth, ThreadSize, ThreadDrillDiameter, ThreadType, EntryAngle, ExitAngle, IsFlatBottom, IsPartial, WrapAngle, TipDepth, TipAngle, NumElemHole, TotalDepth, Depth, BoreRadius, BoreDiameter, SunkDepth, SunkAngle, BoreDepth, PositionTolerance

    Object: HoleChain
    Attributes: IsBlind, IsThreaded, ThreadDepth, DrillDepth, ThreadSize, ThreadDrillDiameter, ThreadType, EntryAngle, ExitAngle, IsFlatBottom, IsPartial, WrapAngle, TipDepth, TipAngle, NumElemHole, TotalDepth, MaxRadius, MaxDiameter, MinRadius, MinDiameter, PositionTolerance
"""

general = """
    Object: PMI
    Attributes: Straightness, Flatness, Circularity, Cylindricity, Angularity, Parallelism, Perpendicularity, ProfileOfLine, ProfileOfSurface, Position, Concentricity, Symmetry, Runout, TotalRunout, IsAttached

    Object: PartEdge
    Attributes: IsSharp

    Object: Hole
    Attributes: InternalThreadClass

    Object: Thread
    Attributes: ExternalThreadClass, Size, Unit
"""

injection_moulding = """
    Object: Hole
    Attributes: RadiusAtTop, DiameterAtTop, RadiusAtBot, DiameterAtBot, TotalDepth, IsBlind, IsPartial, IsTapered, TaperAngle

    Object: Pin
    Attributes: RadiusAtTop, DiameterAtTop, TotalHeight, IsPartial, IsTopSpherical, WrapAngle

    Object: IMFace
    Attributes: MinThickness, MaxThickness, MoldWallThickness, DraftAngle, MoldClassificationType, IsUndercut

    Object: Lip
    Attributes: MinThickness, RadiusAtBot

    Object: Boss
    Attributes: OuterRadiusAtTop, OuterDiameterAtTop, OuterRadiusAtBot, OuterDiameterAtBot, InnerRadiusAtTop, InnerDiameterAtTop, InnerRadiusAtBot, InnerDiameterAtBot, TotalHeight, IsPartial, OuterSurfaceDraftAngle, InnerSurfaceDraftAngle, WrapAngle, IsChamferAtTop

    Object: Rib
    Attributes: DraftAngle, ProfileArea, RadiusAtBot, Height, TopThickness, ThicknessAtBotWithFillet, ThicknessAtBot

    Object: Draft
    Attributes: Angle, Type, Height

    Object: Text
    Attributes: Height, DraftAngle

    Object: ModuleParams
    Attributes: NominalThickness
"""

mill = """
    Object: Pocket
    Attributes: Depth, IsDrafted, DraftAngle, MinSideRadius, MaxSideRadius, MinBotRadius, MaxBotRadius, IsOpen, IsBotFilleted, IsTopFilleted, IsSideFilleted, NumBotSharpEdges, NumSideSharpEdges, DraftType, IsBotChamfered, SideFaceAngle, ExtendedDepth

    Object: BotFillet
    Attributes: MinRadius, MaxRadius, IsVariableRadius

    Object: SideFillet
    Attributes: MinRadius, MaxRadius, IsVariableRadius

    Object: TopFillet
    Attributes: MinRadius, MaxRadius, IsVariableRadius

    Object: Fillet
    Attributes: MinRadius, MaxRadius, IsVariableRadius

    Object: Chamfer
    Attributes: Width, Angle1, Angle2, IsVertex, Distance1, Distance2

    Object: PMI
    Attributes: ProfileOfLine, ProfileOfSurface, SurfaceFinish

    Object: ModuleParams
    Attributes: Machinability
"""

model = """
    Object: PartBody
    Attributes: Material, Length, Width, Height, DiagonalLength, TightBoxLength, TightBoxWidth, TightBoxHeight, TightBoxDiagonalLength, Volume, SurfaceArea

    Object: PartEdge
    Attributes: IsSharp
"""

sheetmetal = """
    Object: Bend
    Attributes: MinRadius, MaxRadius, Angle, IsNullRadius, IsConical

    Object: BendRelief
    Attributes: Depth, Width

    Object: Hem
    Attributes: Radius, Angle, Length

    Object: OpenHem
    Attributes: Radius, Length

    Object: ClosedHem
    Attributes: Length

    Object: RolledHem
    Attributes: Radius, HemOpening

    Object: TearDropHem
    Attributes: Radius, Length, HemOpening

    Object: Stamp
    Attributes: Height, TaperAngle, PunchInnerRadius, PunchOuterRadius, DieInnerRadius, DieOuterRadius

    Object: Dowel
    Attributes: OuterRadius, OuterDiameter, OuterDiameterHeight

    Object: Dimple
    Attributes: DieInnerRadius, PunchOuterRadius, Height

    Object: Bridge
    Attributes: Length, Width

    Object: ExtrudedHole
    Attributes: InnerRadius, InnerDiameter, OuterRadius, OuterDiameter

    Object: CardGuide
    Attributes: Length, OpeningAngle

    Object: Cutout
    Attributes: IsInternal, IsInternalWithSingleFace, IsPlaner

    Object: SimpleCutout
    Attributes: IsInternal, IsInternalWithSingleFace, IsPlaner

    Object: Flange
    Attributes: Radius, Angle, Length

    Object: EdgeFlange
    Attributes: Radius, Angle, Length

    Object: Emboss
    Attributes: Height, TaperAngle, PunchInnerRadius, PunchOuterRadius, DieInnerRadius, DieOuterRadius

    Object: Gusset
    Attributes: Width, Depth, HeadAngle

    Object: Louver
    Attributes: Breadth

    Object: Spoon
    Attributes: Length, FlangeWidth, Width, Height

    Object: Distance
    Attributes: MinValue

    Object: Hole
    Attributes: Radius, Diameter

    Object: SimpleHole
    Attributes: Radius, Diameter

    Object: CompoundHole
    Attributes: Radius, Diameter, Depth

    Object: CBHole
    Attributes: Radius, Diameter, Depth, BoreRadius, BoreDiameter, BoreDepth

    Object: CSHole
    Attributes: Radius, Diameter, Depth, SunkRadius, SunkDiameter, SunkDepth, SunkAngle

    Object: CDHole
    Attributes: Radius, Diameter, Depth, DrillDepth, DrillRadius, DrillDiameter, SunkDepth, SunkAngle

    Object: ModuleParams
    Attributes: Thickness, IsSheetMetalPart
"""

smform = """
    Object: SimpleHole
    Attributes: Radius, Diameter, Depth, TaperAngle, IsTapered

    Object: Bend
    Attributes: Radius

    Object: SMFace
    Attributes: Thickness

    Object: ModuleParams
    Attributes: NormalThickness
"""

tubing = """
    Object: Bend
    Attributes: Radius, Angle, IsAtEnd, SupportLength1, SupportLength2

    Object: Straight
    Attributes: Length, IsAtEnd

    Object: Clearance
    Attributes: MinValue, IsTouching, IsInterfering

    Object: Interference
    Attributes: IsInterfering, Volume

    Object: Tube
    Attributes: Thickness, OuterDiameter, InnerDiameter, Length, IsUniformBendRadius, MaxBendRadius, MinBendRadius

    Object: Overlap
    Attributes: Length
"""

turn = """
    Object: TurnCorner
    Attributes: Radius, IsSharp, IsConcave

    Object: FaceFeature
    Attributes: FlatnessTolerance, PerpendicularityTolerance, SurfaceFinish

    Object: TurnProfileSegment
    Attributes: MinAngle, MaxAngle, IsExternal, IsLinear, Length, MaxContourRadius, MinContourRadius, MaxDiameter, MinDiameter, StraightnessTolerance, CircularityTolerance, CylindricityTolerance, PerpendicularityTolerance, ProfileOfLineTolerance, ProfileOfSurfaceTolerance, ConcentricityTolerance, PositionTolerance, RunoutTolerance, TotalRunoutTolerance

    Object: ModuleParams
    Attributes: MPBody (Body)

    Object: Body
    Attributes: Length, MaxOuterDiameter, MinOuterDiameter, MaxInnerDiameter, MinInnerDiameter

    Object: BoredHoleSegment
    Attributes: MinDiameter, MaxDiameter, IsBlind, Depth, Angle

    Object: BoredHole
    Attributes: MinDiameter, MaxDiameter, IsBlind, Depth, BHRelief (Relief)

    Object: Relief
    Attributes: Value

    Object: SquareGroove
    Attributes: Depth

    Object: VGroove
    Attributes: Radius, Angle

    Object: RoundGroove
    Attributes: Radius

    Object: DoveTailGroove
    Attributes: Angle

    Object: Groove
    Attributes: Location, Type, MinCornerRadius, Depth, FloorWidth, TopWidth, MinDistance
"""

features_dict = {
    "Assembly": assembly,
    "Additive": additive,
    "Die Cast": diecast,
    "Drill": drill,
    "General": general,
    "Injection Moulding": injection_moulding,
    "Mill": mill,
    "Model": model,
    "Sheetmetal": sheetmetal,
    "SMForm": smform,
    "Tubing": tubing,
    "Turn": turn
}