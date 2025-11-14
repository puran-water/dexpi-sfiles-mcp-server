# Day 2: XSD Schema Analysis - Key Findings

**Date**: 2025-11-14
**Status**: In Progress

## Critical Discovery: Actual Document Structure

### Real Structure (from TrainingTestCases)

```xml
<?xml version="1.0" encoding="utf-8"?>
<PlantModel xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:noNamespaceSchemaLocation="../ProteusPIDSchema_4.0.1.xsd">

  <PlantInformation SchemaVersion="4.0.1"
                    OriginatingSystem="SPPID"
                    Date="2019-09-30"
                    Time="07:20:00.0000000+02:00"
                    Is3D="no"
                    Units="Metre"
                    Discipline="PID">
    <UnitsOfMeasure Distance="Metre" />
  </PlantInformation>

  <PlantStructureItem ID="..." ComponentClass="ProcessPlant" ... >
    <!-- Plant hierarchy -->
  </PlantStructureItem>

  <Extent>
    <Min X="0" Y="0" />
    <Max X="0.841" Y="0.594" />
  </Extent>

  <Drawing Name="..." Type="PID" Title="..." Size="A1">
    <PlantDesignItem>
      <!-- Equipment, Piping, Instrumentation -->
    </PlantDesignItem>
  </Drawing>
</PlantModel>
```

### Key Corrections Needed

1. **UnitsOfMeasure Location**:
   - ❌ WRONG (in our docs): Sibling of PlantInformation
   - ✅ CORRECT: Child element of PlantInformation

2. **MetaData Element**:
   - NOT present in TrainingTestCases examples
   - May be optional or schema-specific

3. **Namespace Declaration**:
   - ❌ WRONG (in our code): targetNamespace `http://www.dexpi.org/2008/proteus`
   - ✅ CORRECT: `xsi:noNamespaceSchemaLocation` (NO target namespace)

4. **PlantInformation Attributes** (from real example):
   - SchemaVersion (required)
   - OriginatingSystem (required)
   - Date (required)
   - Time (required)
   - Is3D (appears in example - needs investigation)
   - Units (required)
   - Discipline (appears in example)

## XSD Schema Analysis

### Schema Properties

- **Target Namespace**: None (xsd:noNamespaceSchemaLocation)
- **Schema Version**: 4.2 (we have this file)
- **Actual Version in Example**: 4.0.1 (backwards compatibility needed)

### PlantModel Children (from XSD)

1. **PlantInformation** (1..1, required)
2. **MetaData** (0..1, optional) - may be schema extension
3. **PlantStructureItem** (0..unbounded, optional)
4. **RDLService** (0..unbounded, optional)
5. **Extent** (0..1, optional)
6. **Drawing** (implied from examples, needs XSD verification)

### PlantInformation Structure

From TrainingTestCase:
- **Attributes**:
  - SchemaVersion: "4.0.1" | "4.2"
  - OriginatingSystem: string (e.g., "SPPID", "pyDEXPI")
  - Date: ISO date (YYYY-MM-DD)
  - Time: ISO time with timezone (HH:MM:SS.ffffff+TZ)
  - Is3D: "yes" | "no"
  - Units: "Metre" | other unit systems
  - Discipline: "PID" | "PFD" | etc.

- **Child Elements**:
  - UnitsOfMeasure (with Distance attribute)

## Action Items

### Immediate Fixes Needed

1. ✅ **Update PROTEUS_XML_FORMAT.md** - COMPLETED:
   - ✅ Moved UnitsOfMeasure to be child of PlantInformation
   - ✅ Removed MetaData/UnitsOfMeasure from sibling positions
   - ✅ Updated XML structure example to match TrainingTestCases
   - ✅ Added PlantStructureItem and Extent documentation (src/exporters/proteus_xml_exporter.py:262-327)
   - ✅ Updated PlantInformation attributes table with Is3D, correct ordering
   - ✅ Documented UnitsOfMeasure as child element

2. ✅ **Update proteus_xml_exporter.py** - COMPLETED:
   - ✅ Removed default namespace (src/exporters/proteus_xml_exporter.py:247-248)
   - ✅ Changed to xsi:noNamespaceSchemaLocation (src/exporters/proteus_xml_exporter.py:255-257)
   - ✅ Updated _export_plant_information to include UnitsOfMeasure child (src/exporters/proteus_xml_exporter.py:323-325)
   - ✅ Added Is3D attribute handling (src/exporters/proteus_xml_exporter.py:308-309)
   - ✅ Added SchemaVersion, Units, Discipline attributes
   - ✅ Implemented timezone handling for Time attribute (src/exporters/proteus_xml_exporter.py:297-306)

3. ✅ **Continue XSD Analysis** - COMPLETED:
   - ✅ Extracted Drawing element structure from XSD (docs/schemas/ProteusPIDSchema_4.2.xsd:1005-1043)
   - ✅ **CRITICAL FINDING**: NO PlantDesignItem wrapper element exists!
   - ✅ Analyzed TrainingTestCase structure (E03V01-HEX.EX02.xml)

## Critical Discovery #2: PlantDesignItem Does Not Exist!

### What Our Documentation Says (WRONG ❌):

```xml
<Drawing Name="..." Type="PID">
  <PlantDesignItem>
    <!-- Equipment, Piping, Instrumentation -->
  </PlantDesignItem>
</Drawing>
```

### What XSD Schema Says (docs/schemas/ProteusPIDSchema_4.2.xsd:1005-1043):

```xml
<xsd:element name="Drawing">
  <xsd:complexType>
    <xsd:sequence>
      <xsd:element ref="Presentation" />                    <!-- Required -->
      <xsd:element ref="Extent" minOccurs="0"/>            <!-- Optional -->
      <xsd:choice minOccurs="0" maxOccurs="unbounded">
        <xsd:element ref="Component" />                    <!-- Direct child! -->
        <xsd:element ref="Curve" />
        <xsd:element ref="Surface" />
        <xsd:element ref="Text" />
        <xsd:element ref="DrawingBorder" />
        <xsd:element ref="Symbol"/>
        <xsd:element ref="InsulationSymbol"/>
        <xsd:element ref="ScopeBubble"/>
        <xsd:element ref="PropertyBreak"/>
        <xsd:element ref="Label"/>
        <xsd:element ref="PipeFlowArrow"/>
        <xsd:element ref="PipeSlopeSymbol"/>
        <xsd:element ref="GenericAttributes" />
      </xsd:choice>
    </xsd:sequence>
    <!-- Attributes: Name, Type, Revision, Title, Size, Orientation -->
  </xsd:complexType>
</xsd:element>
```

### What TrainingTestCases Show (E03V01-HEX.EX02.xml:58-4257):

```xml
<Drawing Name="E03V01-HEX.EX02" Type="PID" Title="PUMP WITH NOZZLES" Size="A1">
  <Presentation Layer="" Color="White" ... />
  <Extent>
    <Min X="0" Y="0" />
    <Max X="0.841" Y="0.594" />
  </Extent>
  <DrawingBorder>...</DrawingBorder>

  <!-- Equipment appears as DIRECT child of Drawing -->
  <Equipment ComponentName="..." ID="..." ComponentClass="CentrifugalPump" ...>
    <Description>CENTRIFUGAL PUMP</Description>
    <Position>...</Position>
    <Presentation>...</Presentation>
    <Extent>...</Extent>
    <!-- Graphical elements: Line, Circle, etc. -->
  </Equipment>

  <!-- More Equipment, Nozzle, Label elements -->
</Drawing>
```

### Drawing Element Structure (CORRECT)

**Required Children**:
1. **Presentation** (1..1) - Drawing-level presentation attributes

**Optional Children** (in sequence):
2. **Extent** (0..1) - Drawing extent/bounding box

**Repeating Children** (0..unbounded, xsd:choice):
3. **Component** - Abstract base for Equipment, Nozzle, PipingNetworkSystem, etc.
4. **Curve** - Graphical curve elements (Line, Polyline, Arc, etc.)
5. **Surface** - Graphical surface elements
6. **Text** - Text annotations
7. **DrawingBorder** - Drawing border with title block
8. **Symbol** - Symbol instances
9. **Label** - Label instances
10. **GenericAttributes** - Generic attribute sets

**Drawing Attributes**:
- `Name` (required) - Drawing identifier
- `Type` (required, fixed="PID") - Drawing type
- `Revision` (optional) - Revision identifier
- `Title` (optional) - Drawing title
- `Size` (optional) - Paper size (e.g., "A1", "A0")
- `Orientation` (optional) - "Portrait" | "Landscape"

### Equipment Export Implications

**OLD Approach (WRONG)**:
```python
drawing = etree.SubElement(root, "Drawing")
plant_design = etree.SubElement(drawing, "PlantDesignItem")  # ❌ Doesn't exist!
self._export_equipment(plant_design, model.conceptualModel.taggedPlantItems)
```

**NEW Approach (CORRECT)**:
```python
drawing = etree.SubElement(root, "Drawing")
drawing.set("Name", model.drawingName or "PID-001")
drawing.set("Type", "PID")

# Add required Presentation child
presentation = etree.SubElement(drawing, "Presentation")
# Set default presentation attributes

# Export components directly under Drawing
self._export_equipment(drawing, model.conceptualModel.taggedPlantItems)
self._export_piping(drawing, model.conceptualModel.pipingNetworkSystems)
self._export_instrumentation(drawing, model)
```

## Next Steps

1. ✅ Fix documentation and code based on findings above
2. ✅ Complete XSD analysis for Drawing structure
3. ⏳ Investigate Component element hierarchy (Equipment, Nozzle, PipingNetworkSystem)
4. ⏳ Map pyDEXPI classes to Proteus ComponentClass values
5. ⏳ Document Equipment/Nozzle/Piping element structures from XSD
6. ⏳ Document edge cases and validation rules

---

**Last Updated**: 2025-11-14
**Progress**: 50% (Drawing structure analyzed, PlantDesignItem myth debunked)
