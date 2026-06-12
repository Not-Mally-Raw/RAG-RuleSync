**1. Rule Category:** SheetMetal
**Rule Text:** "Distance between bridges should  be atleast 4.5 times sheet thickness"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Bridge Spacing

Feature1 = Distance
Feature2 = """"
Object1 = Bridge
Object2 = Bridge

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 4.5"
}

**2. Rule Category:** SheetMetal
**Rule Text:** "Card guide length should be at most 127.0 mm and the opening angle should be at least 15.0 degrees"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Card Guide Parameters

Feature1 = CardGuide
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = CardGuide.Length
Operator = <=
Recom = 127.0

ExpName = CardGuide.OpeningAngle
Operator = >=
Recom = 15.0"
}

**3. Rule Category:** SheetMetal
**Rule Text:** "Distance between card guide form and bend should be at least 5.0 times sheet thickness"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Card Guide Form to Bend Distance

Feature1 = Distance
Feature2 = """"
Object1 = CardGuide
Object2 = Bend

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 5.0"

}

**4. Rule Category:** SheetMetal
**Rule Text:** "Distance between curl and bends should be at least 4.5 times sheet thickness plus twice the rolled hem radius"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Curl to Bend Distance

Feature1 = Distance
Feature2 = """" 
Object1 = RolledHem
Object2 = Bend

ExpName = Distance.MinValue -( 2.0*RolledHem.Radius ) / SheetMetal.Thickness
Operator = >=
Recom = 4.5"

}

**5. Rule Category:** SheetMetal
**Rule Text:** "Distance between curl and cutouts should be at least 3.0 times sheet thickness minus the rolled hem radius"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Curl to Cutout Distance

Feature1 = Distance
Feature2 = """" 
Object1 = RolledHem
Object2 = Cutout

ExpName = (Distance.MinValue-RolledHem.Radius)/SheetMetal.Thickness
Operator = >=
Recom = 3.0
"

}

**6. Rule Category:** SheetMetal
**Rule Text:** "Distance between cutout and part edge should be at least 2.0 times sheet thickness"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Cutout to Part Edge Distance

Feature1 = Distance
Feature2 = """" 
Object1 = Cutout
Object2 = PartEdge

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 2.0
"

}

**7. Rule Category:** SheetMetal
**Rule Text:** "Distance between emboss and cutouts should be at least 4.0 times sheet thickness"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Emboss to Cutout Distance

Feature1 = Distance
Feature2 = """" 
Object1 = Emboss
Object2 = Cutout

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 4.0
"

}

**8. Rule Category:** SheetMetal
**Rule Text:** "Distance between embosses should be at least 10.0 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Emboss Spacing

Feature1 = Distance
Feature2 = """" 
Object1 = Emboss
Object2 = Emboss

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 10.0
"

}

**9. Rule Category:** SheetMetal
**Rule Text:** " Distance between emboss and bend should be at least 5.0 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Emboss to Bend Distance

Feature1 = Distance
Feature2 = """" 
Object1 = Emboss
Object2 = Bend

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 5.0
"

}

**10. Rule Category:** SheetMetal
**Rule Text:** " Distance between emboss and part edge should be at least 4.0 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Emboss to Part Edge Distance

Feature1 = Distance
Feature2 = """" 
Object1 = Emboss
Object2 = PartEdge

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 4.0
"

}

**11. Rule Category:** SheetMetal
**Rule Text:** " Distance between extruded form and cutouts should be at least 2.0 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Extruded Form to Cutout Distance

Feature1 = Distance
Feature2 = """" 
Object1 = ExtrudedForm
Object2 = Cutout

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 2.0
"

}

**12. Rule Category:** SheetMetal
**Rule Text:** " Distance between extruded form and part edge should be at least 4.0 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Extruded Form Distance to Part Edge 

Feature1 = Distance
Feature2 = """" 
Object1 = ExtrudedForm
Object2 = PartEdge

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 4.0
"

}

**13. Rule Category:** SheetMetal
**Rule Text:** " Distance between extruded forms should be at least 8.0 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Extruded Form Spacing 

Feature1 = Distance
Feature2 = """" 
Object1 = ExtrudedForm
Object2 = ExtrudedForm

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 8.0
"

}

**14. Rule Category:** SheetMetal
**Rule Text:** " Distance between extruded form and bend should be at least 8.0 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Extruded Form to Bend Distance 

Feature1 = Distance
Feature2 = """" 
Object1 = ExtrudedForm
Object2 = Bend

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 8.0
"

}

**15. Rule Category:** SheetMetal
**Rule Text:** " Distance between gussets should be at least 10.0 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Gusset Spacing
 
Feature1 = Distance
Feature2 = """" 
Object1 = Gusset
Object2 = Gusset

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 10.0
"

}

**16. Rule Category:** SheetMetal
**Rule Text:** " Distance between hem and cutouts should be at least 3.5 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Hem to Cutout Distance

Feature1 = Distance
Feature2 = """" 
Object1 = Hem
Object2 = Cutout

ExpName = Distance.MinValue/SheetMetal.Thickness
Operator = >=
Recom = 3.5
"

}

**17. Rule Category:** SheetMetal
**Rule Text:** " Minimum bridge width should be at least 3.0 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Minimum Bridge Width

Feature1 = Bridge
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Bridge.Width/SheetMetal.Thickness
Operator = >=
Recom = 3.0
"

}

**18. Rule Category:** SheetMetal
**Rule Text:** ""For part with material 6061-T6 the flange radius should be atleast 1.0 mm and the length should be 6.0 mm. 
The sheet thickness for the part with material 6061-T6 should be atleast 2.0 mm."
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Recommended Flange Parameters

Feature1 = Flange
Feature2 = """" 
Object1 = """"
Object2 = """"

Constraint : ExpName = PartBody.Material , Operator = == , Value = 6061-T6
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
"

}

**19. Rule Category:** SheetMetal
**Rule Text:** "For a spoon feature the minimum width should be atleast 0.8 times sheet thickness, minimum length should be atleast 10.0 times sheet thickness, minimum height should be  between 0.5 and 1.2 times sheet thickness
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Recommended Spoon Parameters

Feature1 = Spoon
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Spoon.FlangeWidth/SheetMetal.Thickness
Operator = >=
Recom = 0.8

ExpName = Spoon.Length/SheetMetal.Thickness
Operator = >=
Recom = 10.0

ExpName = Spoon.Height/SheetMetal.Thickness
Operator = between
Recom = 0.5:1.2
"

}

**20. Rule Category:** SheetMetal
**Rule Text:** " Ensure the part is a sheet metal part
"
**DFM Format:** {
"RuleCategory= Sheet Metal
Name = Sheet Metal Part Check

Feature1 = """"
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = SheetMetal.IsSheetMetalPart
Operator = ==
Recom = True
"
}

**21. Rule Category:** Additive
**Rule Text:** " Ensure there are no sharp edges in the part"
**DFM Format:** {
"RuleCategory= Additive Manufacturing
Name = Avoid Sharp Edges

Feature1 = """"
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = PartEdge.IsSharp
Operator = ==
Recom = False"
}

**22. Rule Category:** Additive
**Rule Text:** " Ensure the part does not exceed maximum print size: length 300.0, width 300.0, height 600.0"
**DFM Format:** {
"RuleCategory= Additive Manufacturing
Name = Maximum Print Size 

Feature1 = """"
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Additive.PrintSize.Length
Operator = <=
Recom = 300.0

ExpName = Additive.PrintSize.Width
Operator = <=
Recom = 300.0

ExpName = Additive.PrintSize.Height
Operator = <=
Recom = 600.0
"
}

**23. Rule Category:** Additive
**Rule Text:** " Ensure angular tolerance is at least 0.1 degrees"
**DFM Format:** {
"RuleCategory= Additive Manufacturing
Name = Recommended Angular Tolerance 

Feature1 = PMI
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = PMI.Angularity
Operator = >=
Recom = 0.1
"
}

**24. Rule Category:** Additive
**Rule Text:** " Ensure text height is at least 0.6 units and text width is at least 2.0 units"
**DFM Format:** {
"RuleCategory= Additive Manufacturing
Name = Recommended Text Parameters 

Feature1 = Text
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Text.Height
Operator = >=
Recom = 0.6

ExpName = Text.Width
Operator = >=
Recom = 2.0
"
}

**25. Rule Category:** Additive
**Rule Text:** " Ensure pin height is between 0 and 10 units and pin diameter is between 3 and 5 units"
**DFM Format:** {
"RuleCategory= Additive Manufacturing
Name = Recommended Pin Diameter 

Feature1 = Pin
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Pin.TotalHeight
Operator = between
Recom = 0:10

ExpName = Pin.DiameterAtTop
Operator = between
Recom = 3:5
"
}

**26. Rule Category:** Additive
**Rule Text:** " Ensure wall thickness is at least 0.8 units for both supported and unsupported walls"
**DFM Format:** {
"RuleCategory= Additive Manufacturing
Name = Minimum Wall Thickness 

Feature1 = Wall
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Wall.MinThickness
Operator = >=
Recom = 0.8
"
}

**27. Rule Category:** Assembly
**Rule Text:** " Ensure minimum clearance between components is at least 0.1 units"
**DFM Format:** {
"RuleCategory= Assembly
Name = Minimum Clearance Between Components 

Feature1 = Clearance
Feature2 = """" 
Object1 = Component
Object2 = Component

ExpName = Clearance.MinValue
Operator = >=
Recom = 0.1
"
}

**28. Rule Category:** Assembly
**Rule Text:** " Ensure washer is present for fasteners engaging with specific materials"
**DFM Format:** {
"RuleCategory= Assembly
Name = Missing Washer 

Feature1 = Fastener
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Fastener.IsWasherPresent
Operator = ==
Recom = True"
}

**29. Rule Category:** Assembly
**Rule Text:** " Ensure extended thread length to thread pitch ratio for a bolt is at least 2.0"
**DFM Format:** {
"RuleCategory= Assembly
Name = Recommended Extended Thread Length 

Feature1 = Bolt
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Bolt.ExtendedThreadLength/Bolt.ThreadPitch
Operator = >=
Recom = 2.0"
}

**30. Rule Category:** Assembly
**Rule Text:** " Ensure shank length is less than or equal to the clearance hole depth"
**DFM Format:** {
"RuleCategory= Assembly
Name = Recommended Shank Length 

Feature1 = Bolt
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Bolt.ShankLength
Operator = <=
Recom = Bolt.ClearanceHoleDepth"
}

**31. Rule Category:** DieCasting
**Rule Text:** " Ensure the ratio of the outer radius at the base of the boss to the nominal thickness of the part body is at least 0.25"
**DFM Format:** {
"RuleCategory= Die Casting
Name = Minimum Radius at Base of Boss 

Feature1 = Boss
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Boss.OuterRadiusAtBot/PartBody.NominalThickness
Operator = >=
Recom = 0.25"
}

**32. Rule Category:** DieCasting
**Rule Text:** " Ensure the ratio of the radius at the base of the rib to the top thickness of the rib is between 0.25 and 0.5"
**DFM Format:** {
"RuleCategory= Die Casting
Name = Minimum Radius at Base of Rib 

Feature1 = Rib
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Rib.RadiusAtBot/Rib.TopThickness
Operator = between
Recom = 0.25:0.5"
}

**33. Rule Category:** DieCasting
**Rule Text:** " Ensure the outer radius at the tip of the boss is at least 1.5 unit"
**DFM Format:** {
"RuleCategory= Die Casting
Name = Minimum Radius at Tip of Boss 

Feature1 = Boss
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Boss.OuterRadiusAtTop
Operator = >=
Recom = 1.5"
}

**34. Rule Category:** DieCasting
**Rule Text:** " Ensure mold wall height is at least 2.0 units and the ratio of mold wall thickness to part body nominal thickness is at least 3.0"
**DFM Format:** {
"RuleCategory= Die Casting
Name = Mold Wall Parameters

Feature1 = MoldWall
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = MoldWall.Height
Operator = >=
Recom = 2.0

ExpName = MoldWall.MinValue/PartBody.NominalThickness
Operator = >=
Recom = 3.0"
}

**35. Rule Category:** DieCasting
**Rule Text:** "Ensure the ratio of the outer diameter to the inner diameter of the boss is at most 2.5 and the ratio of the total height to the outer diameter of the boss is at most 1.0"
**DFM Format:** {
"RuleCategory= Die Casting
Name = Recommended Boss Parameters 

Feature1 = Boss
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Boss.OuterDiameterAtTop/Boss.InnerDiameterAtTop
Operator = <=
Recom = 2.5

ExpName = Boss.TotalHeight/Boss.OuterDiameterAtTop
Operator = <=
Recom = 1.0"
}

**36. Rule Category:** DieCasting
**Rule Text:** " Ensure the ratio of rib height to part body nominal thickness is at most 3.0, the ratio of rib thickness at the bottom to part body nominal thickness is at most 0.6, and the ratio of rib thickness at the bottom with fillet to part body nominal thickness is at most 0.6."
**DFM Format:** {
"RuleCategory= Die Casting
Name = Recommended Rib Parameters 

Feature1 = Rib
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Rib.Height/PartBody.NominalThickness
Operator = <=
Recom = 3.0

ExpName = Rib.ThicknessAtBot/PartBody.NominalThickness
Operator = <=
Recom = 0.6

ExpName = Rib.ThicknessAtBotWithFillet/PartBody.NominalThickness
Operator = <=
Recom = 0.6"
}

**37. Rule Category:** DieCasting
**Rule Text:** " Ensure the minimum wall thickness is at least 3.0 units and the maximum wall thickness is at most 5.0 units."
**DFM Format:** {
"RuleCategory= Die Casting
Name = Uniform Wall Thickness 

Feature1 = WallThickness
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = WallThickness.MinValue
Operator = >=
Recom = 3.0

ExpName = WallThickness.MaxValue
Operator = <=
Recom = 5.0"
}

**38. Rule Category:** Turn
**Rule Text:** " Ensure that blind holes have a relief value of 3.0 units, and non-blind holes have a relief value of 0.0 units"
**DFM Format:** {
"RuleCategory= Turning
Name = Blind Hole Relief 

Feature1 = BoredHole
Feature2 = """" 
Object1 = """"
Object2 = """"

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
"
}

**39. Rule Category:** Turn
**Rule Text:** " Ensure that the ratio of the length to the minimum outer diameter of turned parts does not exceed 8.0."
**DFM Format:** {
"RuleCategory= Turning
Name = Length to Outer Diameter Ratio

Feature1 = FaceFeature
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Turn.Body.Length/Turn.Body.MinOuterDiameter
Operator = <=
Recom = 8.0"
}

**40. Rule Category:** Turn
**Rule Text:** " Ensure that the internal corner radius of turned parts is at least 0.5 units."
**DFM Format:** {
"RuleCategory= Turning
Name = Minimum Internal Corner Radius 

Feature1 = TurnCorner
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = TurnCorner.Radius
Operator = >=
Recom = 0.5"
}

**41. Rule Category:** General
**Rule Text:** " Ensure that all PMI (Product and Manufacturing Information) is associated with the relevant features."
**DFM Format:** {
"RuleCategory= General
Name = Avoid Non-Associated PMI 

Feature1 = PMI
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = PMI.IsAttached
Operator = ==
Recom = True
"
}

**42. Rule Category:** General
**Rule Text:** " Ensure that thread sizes conform to the recommended standard sizes: 1-64 UNC, 1-72 UNF, 2-56 UNC."
**DFM Format:** {
"RuleCategory= General
Name = Recommended Standard Thread Sizes 

Feature1 = Thread
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Thread.Size
Operator = in
Recom = 1-64 UNC, 1-72 UNF, 2-56 UNC"
}

**43. Rule Category:** General
**Rule Text:** " Ensure that external threads conform to the recommended thread classes: 1A, 2A."
**DFM Format:** {
"RuleCategory= General
Name = Recommended Thread Class - External Threads 

Feature1 = Thread
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Thread.ExternalThreadClass
Operator = in
Recom = 1A, 2A"
}

**44. Rule Category:** General
**Rule Text:** " Ensure that internal threads conform to the recommended thread classes: 1B, 2B."
**DFM Format:** {
"RuleCategory= General
Name = Recommended Thread Class - Internal Threads 

Feature1 = Hole
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Hole.InternalThreadClass
Operator = in
Recom = 1B, 2B"
}

**45. Rule Category:** General
**Rule Text:** " Ensure that the thread unit is set to English."
**DFM Format:** {
"RuleCategory= General
Name = Recommended Thread Unit 

Feature1 = Thread
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Thread.Unit
Operator = ==
Recom = English"
}

**46. Rule Category:** General
**Rule Text:** " Ensure that the wall thickness is between the minimum value of 5.0 units and the maximum value of 10.0 units."
**DFM Format:** {
"RuleCategory= General
Name = Thickness Check 

Feature1 = Wall
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName1 = Wall.MinThickness
Operator1 = >=
Recom1 = 5.0

ExpName2 = Wall.MaxThickness
Operator2 = <=
Recom2 = 10.0"
}

**47. Rule Category:** General
**Rule Text:** " Ensure that the part body material is one of the preferred materials."
**DFM Format:** {
"RuleCategory= General
Name = Use Preferred Materials 

Feature1 = PartBody
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = PartBody.Material
Operator = in
Recom = [List of preferred materials]
"
}

**48. Rule Category:** Tubing
**Rule Text:** "Clearance between tubes should be at least 5.0 units."
**DFM Format:** {
"RuleCategory= Tubing
Name = Minimum Clearance Between Tubes 

Feature1 = Clearance
Feature2 = """" 
Object1 = Tube
Object2 = Tube

ExpName = Clearance.MinValue
Operator = >=
Recom = 5.0"
}

**49. Rule Category:** Tubing
**Rule Text:** "Ensure that the Overlap length between pipes should be at least 45.0 units."
**DFM Format:** {
"RuleCategory= Tubing
Name = Minimum Overlap Length Between Pipes 

Feature1 = Overlap
Feature2 = """" 
Object1 = Tube
Object2 = Tube

ExpName = Overlap.Length
Operator = >=
Recom = 45.0"
}

**50. Rule Category:** Tubing
**Rule Text:** "Bend radius should be at least 14.2748 units for tubes with an outer diameter of 6.35 units."
**DFM Format:** {
"RuleCategory= Tubing
Name = Recommended Tube Bend Radius 

Feature1 = Bend
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName1 = Tube.OuterDiameter
Operator1 = ==
Recom1 = 6.35

ExpName2 = Bend.Radius
Operator2 = >=
Recom2 = 14.2748"
}

**51. Rule Category:** Tubing
**Rule Text:** "Bend radius to outer diameter ratio should be at least 3.0."
**DFM Format:** {
"RuleCategory= Tubing
Name = Tube Bend to OD Ratio 

Feature1 = Bend
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Bend.Radius/Tube.OuterDiameter
Operator = >=
Recom = 3.0"
}

**52. Rule Category:** Tubing
**Rule Text:** "All bends should have a common radius."
**DFM Format:** {
"RuleCategory= Tubing
Name = Use Common Bend Radius 

Feature1 = Bend
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Tube.IsUniformBendRadius
Operator = ==
Recom = True"
}

**53. Rule Category:** SMForm
**Rule Text:** "Distance between holes should be at least 2.0 times the sheet metal nominal thickness."
**DFM Format:** {
"RuleCategory= Sheet Metal Forming
Name = Hole Spacing 

Feature1 = Distance
Feature2 = """" 
Object1 = SimpleHole
Object2 = SimpleHole

ExpName = Distance.MinValue/SheetMetalForm.NominalThickness
Operator = >=
Recom = 2.0"
}

**54. Rule Category:** SMForm
**Rule Text:** "Distance between hole and bend should be at least 2.5 times the sheet metal nominal thickness."
**DFM Format:** {
"RuleCategory= Sheet Metal Forming
Name = Hole To Bend Distance 

Feature1 = Distance
Feature2 = """" 
Object1 = SimpleHole
Object2 = Bend

ExpName = Distance.MinValue/SheetMetalForm.NominalThickness
Operator = >=
Recom = 2.5"
}

**55. Rule Category:** SMForm
**Rule Text:** "Distance between hole and part edge should be at least 2.0 times the sheet metal nominal thickness."
**DFM Format:** {
"RuleCategory= Sheet Metal Forming
Name = Hole To Part Edge Distance 

Feature1 = Distance
Feature2 = """" 
Object1 = SimpleHole
Object2 = PartEdge

ExpName = Distance.MinValue/SheetMetalForm.NominalThickness
Operator = >=
Recom = 2.0"
}

**56. Rule Category:** SMForm
**Rule Text:** "Bend radius should be at least 1.3 times the sheet metal nominal thickness."
**DFM Format:** {
"RuleCategory= Sheet Metal Forming
Name = Minimum Bend Radius 

Feature1 = Bend
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Bend.Radius/SheetMetalForm.NominalThickness
Operator = >=
Recom = 1.3"
}

**57. Rule Category:** SMForm
**Rule Text:** "Sheet thickness should be at least 1.0 unit."
**DFM Format:** {
"RuleCategory= Sheet Metal Forming
Name = Minimum Sheet Thickness 

Feature1 = SMFace
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = SMFace.Thickness
Operator = >=
Recom = 1.0"
}

**58. Rule Category:** SMForm
**Rule Text:** "Hole diameter should be at least 1.0 times the sheet metal nominal thickness."
**DFM Format:** {
"RuleCategory= Sheet Metal Forming
Name = Recommended Hole Diameter 

Feature1 = SimpleHole
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = SimpleHole.Diameter/SheetMetalForm.NominalThickness
Operator = >=
Recom = 1.0
"
}

**59. Rule Category:** InjectionMolding
**Rule Text:** "Cored hole radius in boss should be at least 0.254 units."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Cored Hole Radius in Boss

Feature1 = Boss
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Boss.InnerRadiusAtBot
Operator = >=
Recom = 0.254"
}

**60. Rule Category:** InjectionMolding
**Rule Text:** "Hole depth to diameter ratio should be 2.0 for blind holes and 4.0 for through holes."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Hole Depth to Diameter Ratio 

Feature1 = Hole
Feature2 = """" 
Object1 = """"
Object2 = """"

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
}"
}

**61. Rule Category:** InjectionMolding
**Rule Text:** "Rib height should be at most 4.0 times the rib thickness."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Maximum Rib Height for Rib Thickness 

Feature1 = Rib
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Rib.Height
Operator = <=
Recom = 4.0"
}

**62. Rule Category:** InjectionMolding
**Rule Text:** "Draft angle for text should be at least 0.5 degrees."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Minimum Draft Angle for Text 

Feature1 = Text
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName= Text.DraftAngle
Operator = >=
Recom = 0.5"
}

**63. Rule Category:** InjectionMolding
**Rule Text:** "Draft angle for bosses should be at least 0.25 degrees for inner surfaces and 0.5 degrees for outer surfaces."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Minimum Draft for Bosses 

Feature1 = Boss
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Boss.InnerSurfaceDraftAngle
Operator = >=
Recom = 0.25

ExpName = Boss.OuterSurfaceDraftAngle
Operator = >=
Recom = 0.5"
}

**64. Rule Category:** InjectionMolding
**Rule Text:** "Draft angle for ribs should be at least 0.5 degrees."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Minimum Draft for Ribs 

Feature1 = Rib
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Rib.DraftAngle
Operator = >=
Recom = 0.5"
}

**65. Rule Category:** InjectionMolding
**Rule Text:** "Recommended boss parameters should be as follows: Outer Diameter to Inner Diameter ratio should be at least 2.0, and Height to Outer Diameter ratio should be at least 3.0."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Recommended Boss Parameters 

Feature1 = Boss
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Boss.OuterDiameterAtTop/Boss.InnerDiameterAtTop
Operator = >=
Recom = 2.0

ExpName = Boss.TotalHeight/Boss.OuterDiameterAtTop
Operator = >=
Recom = 3.0"
}

**66. Rule Category:** InjectionMolding
**Rule Text:** "Recommended bottom radius for lip should be at least 0.5 times the minimum thickness."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Recommended Bottom Radius for Lip 

Feature1 = Lip
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Lip.RadiusAtBot/Lip.MinThickness
Operator = >=
Recom = 0.5"
}

**67. Rule Category:** InjectionMolding
**Rule Text:** "For pins with height between 0 and 10 units recommended pin diameter should be between 0.5 and 1.5 units."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Recommended Pin Diameter based on pin height

Feature1 = Pin
Feature2 = """" 
Object1 = """"
Object2 = """"

Constraint : ExpName = Pin.TotalHeight , Operator = between, Value = 0.0 : 10
{
       ExpName = Pin.DiameterAtTop
       Operator = between
       Recom = 0.5:1.5
}"
}

**68. Rule Category:** InjectionMolding
**Rule Text:** "Rib height to nominal wall thickness ratio should be at least 3.0, rib thickness with fillet to wall thickness ratio should be at least 0.6, and rib thickness to wall thickness ratio should be at least 0.6."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Recommended Rib Parameters 

Feature1 = Rib
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Rib.Height/InjectionMolding.NominalThickness
Operator = >=
Recom = 3.0

ExpName = Rib.ThicknessAtBotWithFillet/InjectionMolding.NominalThickness
Operator = >=
Recom = 0.6

ExpName = Rib.ThicknessAtBot/InjectionMolding.NominalThickness
Operator = >=
Recom = 0.6"
}

**69. Rule Category:** InjectionMolding
**Rule Text:** "The recommended text height should be at least 0.2 units."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Recommended Text Height 

Feature1 = Text
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Text.Height
Operator = >=
Recom = 0.2"
}

**70. Rule Category:** InjectionMolding
**Rule Text:** "The rib height to nominal wall thickness ratio should be at least 3.0 for proper reinforcement."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Rib Reinforcement Check 

Feature1 = Rib
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Rib.Height/InjectionMolding.NominalThickness
Operator = >=
Recom = 3.0"
}

**71. Rule Category:** InjectionMolding
**Rule Text:** "The thickness at the tip of the rib should be at least 0.8 units."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Thickness at Tip of Rib

Feature1 = Rib
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Rib.TopThickness
Operator = >=
Recom = 0.8"
}

**72. Rule Category:** InjectionMolding
**Rule Text:** "The uniform wall thickness should be between 2.0 and 3.0 units."
**DFM Format:** {
"RuleCategory= Injection Molding
Name = Uniform Wall Thickness 

Feature1 = IMFace
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName1 = IMFace.MinThickness
Operator1 = >=
Recom1 = 2.0

ExpName2 = IMFace.MaxThickness
Operator2 = <=
Recom2 = 3.0"
}

**73. Rule Category:** Mill
**Rule Text:** "The side face angle of the pocket should be at least 13.0 degrees for closed angle machining."
**DFM Format:** {
"RuleCategory= Milling
Name = Closed Angle Machining

Feature1 = Pocket
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Pocket.SideFaceAngle
Operator = >=
Recom = 13.0"
}

**74. Rule Category:** Mill
**Rule Text:** "The entry and exit angles for holes should be 0.0 degrees for proper drilling."
**DFM Format:** {
"RuleCategory= Drilling
Name = Entry-Exit Surface for Holes

Feature1 = Hole
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName1 = Hole.EntryAngle
Operator1 = ==
Recom1 = 0.0

ExpName2 = Hole.ExitAngle
Operator2 = ==
Recom2 = 0.0"
}

**75. Rule Category:** Mill
**Rule Text:** "The minimum radius for fillets on top edges should be less than or equal to 25.4 units."
**DFM Format:** {
"RuleCategory= Milling
Name = Fillets on Top Edges

Feature1 = TopFillet
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = TopFillet.MinRadius
Operator = <=
Recom = 25.4"
}

**76. Rule Category:** Mill
**Rule Text:** "The hole depth to hole diameter ratio for deep holes should be less than or equal to 8.0."
**DFM Format:** {
"RuleCategory= Drilling
Name = Deep Holes

Feature1 = Hole
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Hole.TotalDepth/Hole.Diameter
Operator = <=
Recom = 8.0"
}

**77. Rule Category:** Mill
**Rule Text:** "The minimum radius for fillets on top edges should be greater than or equal to 25.4 units."
**DFM Format:** {
"RuleCategory= Milling
Name = Fillets on Top Edges

Feature1 = TopFillet
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = TopFillet.MinRadius
Operator = >=
Recom = 25.4"
}

**78. Rule Category:** Mill
**Rule Text:** "Avoid flat bottom holes"
**DFM Format:** {
"RuleCategory= Drilling
Name = Flat Bottom Holes

Feature1 = Hole
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Hole.IsFlatBottom
Operator = ==
Recom = False"
}

**79. Rule Category:** Mill
**Rule Text:** "The maximum thread depth of a hole should not exceed 75% of the drill depth."
**DFM Format:** {
"RuleCategory= Drilling
Name = Maximum Thread Depth of Hole 

Feature1 = Hole
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Hole.ThreadDepth/Hole.DrillDepth
Operator = <=
Recom = 0.75"
}

**80. Rule Category:** Mill
**Rule Text:** "The minimum hole diameter should be at least 5.0 units."
**DFM Format:** {
"RuleCategory= Drilling
Name = Minimum Hole Diameter

Feature1 = Hole
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Hole.Diameter
Operator = >=
Recom = 5.0"
}

**81. Rule Category:** Mill
**Rule Text:** "Avoid non uniform bottom radius"
**DFM Format:** {
"RuleCategory= Milling
Name = Non Uniform Bottom Radius

Feature1 = BotFillet
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = BotFillet.IsVariableRadius
Operator = ==
Recom = False"
}

**82. Rule Category:** Mill
**Rule Text:** "Partial holes should have a wrap angle percentage of 75.0 for partial holes."
**DFM Format:** {
"RuleCategory= Drilling
Name = Partial Holes (vrm)

Feature1 = Hole
Feature2 = """" 
Object1 = """"
Object2 = """"

Constraint : ExpName = Hole.IsPartial, Operator = ==, Value = True
{
        ExpName = (Hole.WrapAngle/360)*100
        Operator = <=
        Recom = 75.0
}"
}

**83. Rule Category:** Mill
**Rule Text:** "Avoid bottom chamfers for a pocket"
**DFM Format:** {
"RuleCategory= Milling
Name = Pockets With Bottom Chamfers

Feature1 = Pocket
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Pocket.IsBotChamfered
Operator = ==
Recom = False"
}

**84. Rule Category:** Mill
**Rule Text:** "Recommended line profile tolerance based on part size should be 0.0508 for parts with diagonal length 0.0 to 25.4, 0.1016 for parts with diagonal length 25.4 to 152.4, and 0.1524 for parts with diagonal length 152.4 to 2540.0"
**DFM Format:** {
"RuleCategory= Milling
Name = Recommended Line Profile Tolerance Based on Part Size

Feature1 = PMI
Feature2 = """" 
Object1 = """"
Object2 = """"

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
}"
}

**85. Rule Category:** Mill
**Rule Text:** "Recommended position tolerance for holes should be 0.0254 for default, 0.0508 for parts with diagonal length 0.0 to 25.4 and diameter 5.05714 to 7.54126, 0.127 for parts with diagonal length 25.4 to 152.4 and diameter 5.05714 to 7.54126, and 0.254 for parts with diagonal length 152.4 to 2540.0 and diameter 5.05714 to 7.54126"
**DFM Format:** {
"RuleCategory= Drilling
Name = Recommended Position Tolerance for Hole (vrm)

Feature1 = HoleSegment
Feature2 = """" 
Object1 = """"
Object2 = """"

Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = Default
{
        ExpName = HoleSegment.PositionTolerance
        Operator = <=
        Recom = 0.0254
}
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
Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = 152.4
{
        ExpName = HoleSegment.Diameter, Operator = <=, Value = 7.54126
        {
                ExpName = HoleSegment.Diameter, Operator = >=, Value = 5.05714
                {
                        ExpName = HoleSegment.PositionTolerance
                        Operator = <=
                        Recom = 0.127
                }
        }
}
Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = 2540.0
{
        ExpName = HoleSegment.Diameter, Operator = <=, Value = 7.54126
        {
                ExpName = HoleSegment.Diameter, Operator = >=, Value = 5.05714
                {
                        ExpName = HoleSegment.PositionTolerance
                        Operator = <=
                        Recom = 0.254
                }
        }
}"
}

**86. Rule Category:** Mill
**Rule Text:** "Recommended surface profile tolerance based on part size should be 0.0508 for parts with diagonal length 0.0 to 25.4, 0.1016 for parts with diagonal length 25.4 to 152.4, and 0.1524 for parts with diagonal length 152.4 to 2540.0."
**DFM Format:** {
"RuleCategory= Milling
Name = Recommended Surface Profile Tolerance Based on Part Size

Feature1 = PMI
Feature2 = """" 
Object1 = """"
Object2 = """"

Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = Default
{
        ExpName = PMI.ProfileOfSurface
        Operator = <=
        Recom = 0.0508
}
Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = 25.4
{
        ExpName = PMI.ProfileOfSurface
        Operator = <=
        Recom = 0.0508
}
Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = 152.4
{
        ExpName = PMI.ProfileOfSurface
        Operator = <=
        Recom = 0.1016
}
Constraint : ExpName = PartBody.TightBoxDiagonalLength, Operator = <=, Value = 2540.0
{
        ExpName = PMI.ProfileOfSurface
        Operator = <=
        Recom = 0.1524
}"
}

**87. Rule Category:** Mill
**Rule Text:** "The recommended machinability for milling operations and value should be 100."
**DFM Format:** {
"RuleCategory= Milling
Name = Recommended Machinability

Feature1 = Pocket
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = Mill.Machinability
Operator = <=
Recom = 100"
}

**88. Rule Category:** Mill
**Rule Text:** "The recommended surface finish for machined faces should be not more than 0.8."
**DFM Format:** {
"RuleCategory= Milling
Name = Surface Finish for Machined Faces

Feature1 = PMI
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName = PMI.SurfaceFinish
Operator = <=
Recom = 0.8"
}

**89. Rule Category:** Mill
**Rule Text:** "The corners of the pocket should be filleted"
**DFM Format:** {
"RuleCategory= Milling
Name = Check side fillets for pocket

Feature1 = Pocket
Feature2 = """" 
Object1 = """"
Object2 = """"

ExpName1 = Pocket.IsSideFilleted
Operator1 = ==
Recom1 = True"
}











