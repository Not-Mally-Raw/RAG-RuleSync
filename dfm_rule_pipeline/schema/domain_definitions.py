"""
Technical definitions for every Object in each manufacturing domain.
Used by the LLM-based domain resolver to semantically match a rule
to its correct domain.
"""

DOMAIN_DEFINITIONS = {
    "Assembly": """
        Component: A discrete part or subassembly within a larger assembled product, identified by name and parent hierarchy.
        Distance: The measured separation between two components or features in an assembly.
        Interference: A condition where two components occupy the same physical space, indicating a design collision.
        Clearance: The minimum gap between two assembled components; checks for touching or interfering conditions.
        Fastener: A mechanical device (bolt, screw, rivet) used to join components, characterized by type, bearing area, and engagement parameters.
        Bolt: A threaded cylindrical fastener with a head, used with a nut to clamp components together; defined by shank length, thread pitch, and clearance hole depth.
        Nut: A threaded block that mates with a bolt to create a clamping force; characterized by wrench flat diameter and bearing area.
    """,

    "Additive": """
        AMFace: A surface of an additively manufactured (3D-printed) part, characterized by its wall thickness and minimum gap to adjacent surfaces.
        Pin: A vertical cylindrical protrusion built layer-by-layer in additive manufacturing; may have a spherical top.
        Hole: A cylindrical void in an additively manufactured part; may be blind (closed-bottom) or tapered.
        Text: Raised or recessed lettering on an AM part surface, constrained by minimum height and width for printability.
        Wall: A thin vertical structure in an AM part; minimum thickness and support requirements are critical for print success.
        PMI: Product Manufacturing Information annotations such as angularity tolerances applied to AM parts.
        ModuleParams: Process-level parameters including nominal wall thickness, print size (build volume), and sub-process type (FDM, SLA, SLS, etc.).
        PrintSize: The bounding dimensions (length, height, width) of the 3D printer's build volume.
    """,

    "Die Cast": """
        MoldFace: A surface of a die-cast part in contact with the mold cavity; characterized by wall thickness, draft angle, undercut presence, and fillet conditions.
        Boss: A raised cylindrical feature on a die-cast part used for fastener mounting; defined by inner/outer diameters, draft angles, and chamfer presence.
        Rib: A thin wall projecting from the main body to increase stiffness; characterized by draft angle, height, and thickness at base and top.
        WallThickness: The minimum and maximum thickness of the casting walls; critical for material flow and solidification.
        MoldWall: The thickness of the steel mold wall itself, which affects cooling rate and mold life.
        Draft: The taper angle applied to vertical surfaces to allow part ejection from the die; defined by angle, type, and feature height.
        Text: Raised or recessed characters on the casting surface; requires sufficient draft angle for mold release.
    """,

    "Drill": """
        Hole: A cylindrical bore created by a drill bit; attributes include diameter, depth, thread specifications, entry/exit angles, and whether it is blind or through.
        HoleSegment: A single cylindrical section within a multi-step hole, potentially tapered.
        SimpleHole: A single-diameter drilled hole, the most basic hole type.
        CompoundHole: A hole with multiple diameter steps created by successive drilling or boring operations.
        CBHole: A counterbored hole — a hole with an enlarged flat-bottomed recess at the top for bolt-head clearance.
        CSHole: A countersunk hole — a hole with a conical recess at the top, typically for flat-head screws.
        CDHole: A combined counterbore-countersink hole with both a bore recess and a conical sink.
        HoleChain: A series of aligned holes processed as a group, sharing thread and depth specifications.
    """,

    "General": """
        PMI: Product Manufacturing Information — geometric dimensioning and tolerancing (GD&T) annotations including straightness, flatness, circularity, cylindricity, angularity, parallelism, perpendicularity, profile of line/surface, position, concentricity, symmetry, runout, and total runout.
        PartEdge: An edge where two surfaces meet on a part body; checked for sharpness which may need chamfering or filleting.
        Hole: A generic hole feature with internal thread class specification.
        Thread: An external helical ridge on a cylindrical surface used for fastening; defined by thread class, size, and unit system.
    """,

    "Injection Moulding": """
        Hole: A cylindrical void in a molded plastic part; may be blind, tapered, or partial.
        Pin: A cylindrical protrusion (core pin feature) in a mold, constrained by diameter, height, and wrap angle.
        IMFace: A surface of an injection-molded part in contact with the mold cavity; characterized by wall thickness, draft angle, and undercut conditions.
        Lip: A thin protruding edge on a molded part, typically at parting lines or snap-fit features; constrained by minimum thickness and fillet radius.
        Boss: A raised cylindrical feature for screw insertion or press-fit assembly; defined by inner/outer diameters, draft angles, and chamfer.
        Rib: A thin reinforcing wall projecting from the main part surface; constrained by draft angle, height, and base thickness.
        Draft: The taper angle on vertical mold surfaces required for part ejection.
        Text: Embossed or debossed lettering on the mold surface, requiring minimum height and draft for mold release.
        ModuleParams: Process-level parameters such as nominal wall thickness of the molded part.
    """,

    "Mill": """
        Pocket: A recessed cavity milled into a workpiece; characterized by depth, draft angle, corner radii, and whether it is open-sided.
        BotFillet: A rounded transition at the bottom of a milled pocket between the floor and side walls.
        SideFillet: A rounded transition along the vertical edges of a milled pocket.
        TopFillet: A rounded transition at the top entry edge of a milled feature.
        Fillet: A general rounded edge transition on a milled part.
        Chamfer: An angled cut at an edge, defined by width, angles, and distances; used to remove sharp edges or aid assembly.
        PMI: Manufacturing annotations specific to milling, including profile tolerances and surface finish requirements.
        ModuleParams: Process-level parameters such as material machinability rating.
    """,

    "Model": """
        PartBody: The overall solid body of the part, characterized by material, bounding box dimensions (length, width, height), diagonal length, tight box dimensions, volume, and surface area.
        PartEdge: An edge on the part body; checked for sharpness.
    """,

    "Sheetmetal": """
        Bend: A deformation where flat sheet metal is curved along a straight axis to form an angle; characterized by bend radius and bend angle.
        BendRelief: A cutout at the junction of a bend to prevent tearing; defined by relief depth and width.
        Hem: A fold of the sheet edge back onto itself to eliminate sharp edges and add stiffness.
        OpenHem: A hem fold that is not fully closed, leaving a gap defined by radius and length.
        ClosedHem: A hem fold that is fully flattened against the sheet surface.
        RolledHem: A hem fold curled into a cylindrical shape for a smooth edge.
        TearDropHem: A hem fold shaped like a teardrop, combining a curl with a small opening.
        Stamp: A formed feature created by pressing sheet metal into a die cavity; characterized by height, taper angle, and punch/die radii.
        Dowel: A raised cylindrical protrusion formed in sheet metal, defined by outer radius and height.
        Dimple: A small dome-shaped indentation stamped into sheet metal for alignment or stiffness.
        Bridge: A narrow strip of material left between two cutouts to maintain structural continuity during processing.
        ExtrudedHole: A hole with a cylindrical collar formed by extruding the sheet material, used for threading.
        CardGuide: A formed sheet metal feature for guiding circuit boards, defined by length and opening angle.
        Cutout: A shaped opening removed from the flat sheet, either internal or at the sheet perimeter.
        SimpleCutout: A basic single-profile cutout in sheet metal.
        Flange: A bent extension of the sheet edge for reinforcement, attachment, or stiffening.
        EdgeFlange: A flange formed specifically along the free edge of a sheet metal part.
        Emboss: A raised or depressed feature stamped into the sheet without piercing through.
        Gusset: A triangular reinforcement formed at the junction of two bends or surfaces.
        Louver: A slotted ventilation opening created by lancing and bending a strip of sheet metal.
        Spoon: A curved transition feature between a flat face and an angled flange.
        Distance: The measured separation between two features on a sheet metal part.
        Hole: A circular opening punched or drilled in sheet metal.
        SimpleHole: A basic single-diameter hole in sheet metal.
        CompoundHole: A multi-step hole in sheet metal.
        CBHole: A counterbored hole in sheet metal with a flat-bottomed recess.
        CSHole: A countersunk hole in sheet metal with a conical recess.
        CDHole: A combined counterbore-countersink hole in sheet metal.
        ModuleParams: Sheet metal process parameters including material thickness and whether the part is classified as sheet metal.
    """,

    "SMForm": """
        SimpleHole: A basic hole in a formed sheet metal part, potentially tapered.
        Bend: A curved deformation in a formed sheet metal part, defined by bend radius.
        SMFace: A face of a formed sheet metal part, characterized by its local thickness.
        ModuleParams: Process parameters for sheet metal forming, including nominal thickness.
    """,

    "Tubing": """
        Bend: A curved section of a tube, characterized by bend radius, angle, and whether it occurs at the tube end.
        Straight: A linear section of tubing between bends, defined by length.
        Clearance: The minimum gap between tube sections or between a tube and surrounding components.
        Interference: A collision condition where two tube sections or a tube and another part occupy the same space.
        Tube: The overall tube body; characterized by wall thickness, outer/inner diameters, total length, and bend radius uniformity.
        Overlap: A condition where tube sections overlap in space; defined by overlap length.
    """,

    "Turn": """
        TurnCorner: The radius at the junction of two turned surfaces on a lathe; checked for sharpness and concavity.
        FaceFeature: A flat end-face of a turned part, with associated flatness, perpendicularity, and surface finish tolerances.
        TurnProfileSegment: A section of the turned part's axial profile; characterized by angle range, linearity, diameter range, and associated GD&T tolerances.
        ModuleParams: Lathe process parameters referencing the overall turned body geometry.
        Body: The overall turned part body, defined by length and outer/inner diameter ranges.
        BoredHoleSegment: A single cylindrical section within an internal bore, potentially blind or tapered.
        BoredHole: An internal cylindrical cavity machined on a lathe, potentially with relief undercuts.
        Relief: An undercut groove at the end of a bore or thread for tool clearance.
        SquareGroove: A groove with a rectangular cross-section machined into a turned surface.
        VGroove: A groove with a V-shaped cross-section, defined by radius and included angle.
        RoundGroove: A groove with a semicircular cross-section.
        DoveTailGroove: A groove with a trapezoidal cross-section wider at the bottom than the top, defined by the dovetail angle.
        Groove: A general recessed channel on a turned part; characterized by location, type, corner radius, depth, and width dimensions.
    """,
}
