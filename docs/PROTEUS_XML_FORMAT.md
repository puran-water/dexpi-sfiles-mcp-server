# Proteus XML Export Format Specification

**Version**: 4.2
**Status**: Implementation Guide (Day 1 - In Progress)
**Last Updated**: 2025-11-14

## Overview

This document serves as the implementation guide for exporting pyDEXPI `DexpiModel` instances to Proteus XML 4.2 format, enabling rendering via GraphicBuilder and other Proteus-compliant tools.

## Source Documents

- **XSD Schema**: `docs/schemas/ProteusPIDSchema_4.2.xsd` (93KB)
- **P&ID Profile**: `docs/schemas/PID_Profile_Spec_3.3.3.doc` (1.9MB)
- **DEXPI Specification**: `docs/schemas/DEXPI_Specification_1.2.pdf` (11MB)
- **Training Examples**: DEXPI TrainingTestCases repository (65 component patterns)

## Document Structure

Proteus XML files follow this hierarchical structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PlantModel xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:noNamespaceSchemaLocation="ProteusPIDSchema_4.2.xsd">
  <PlantInformation SchemaVersion="4.2"
                    OriginatingSystem="pyDEXPI"
                    Date="2025-11-14"
                    Time="12:00:00.000000+00:00"
                    Is3D="no"
                    Units="Metre"
                    Discipline="PID">
    <UnitsOfMeasure Distance="Metre" />
  </PlantInformation>

  <!-- PlantStructureItem and Extent are optional per XSD -->

  <Drawing Name="..." Type="PID" Title="..." Size="A1">
    <!-- Required: Presentation element -->
    <Presentation Layer="Default" Color="Black" LineType="Solid" LineWeight="0.00035" R="0" G="0" B="0" />

    <!-- Optional: Extent element -->
    <Extent>
      <Min X="0" Y="0" />
      <Max X="1.0" Y="1.0" />
    </Extent>

    <!-- Equipment (direct children of Drawing, NOT wrapped in PlantDesignItem) -->
    <Equipment ComponentClass="Tank" ID="..." ComponentName="..." TagName="...">
      <Presentation ... />
      <Position><Location X="..." Y="..." Z="..." />...</Position>
      <Extent>...</Extent>
      <Nozzle ID="..." />
      ...
    </Equipment>

    <!-- Piping Network Systems -->
    <PipingNetworkSystem ID="...">
      <PipingNetworkSegment ID="..." />
      ...
    </PipingNetworkSystem>

    <!-- Instrumentation -->
    <ProcessInstrumentationFunction ID="..." ComponentClass="..." />
    ...
  </Drawing>
</PlantModel>
```

## Core Element Mapping

### PlantInformation (Required)

Maps from: `DexpiModel` metadata

**Based on TrainingTestCases analysis and XSD validation**:

| Attribute | Source | Type | Required | Notes |
|-----------|--------|------|----------|-------|
| SchemaVersion | Fixed value | string | Yes | "4.2" for Proteus XML 4.2 |
| OriginatingSystem | `originatingSystemName` | string | Yes | Default: "pyDEXPI" if not set |
| Date | `exportDateTime.date()` | ISO date | Yes | Format: YYYY-MM-DD |
| Time | `exportDateTime.time()` | ISO time | Yes | Format: HH:MM:SS.ffffff+TZ:TZ |
| Is3D | Fixed value | string | Yes | "no" for P&ID, "yes" for 3D models |
| Units | Unit system | string | Yes | "Metre" (default per TrainingTestCases) |
| Discipline | Engineering discipline | string | Yes | "PID", "PFD", etc. |
| OriginatingSystemVendor | `originatingSystemVendorName` | string | No | Optional vendor information |
| OriginatingSystemVersion | `originatingSystemVersion` | string | No | Optional version information |

**Child Elements**:
- **UnitsOfMeasure** (required): Child element with `Distance` attribute (typically "Metre")

### Equipment Export

Maps from: `ConceptualModel.taggedPlantItems` → `<Equipment>`

#### Required Attributes

| Attribute | Source | Type | Required | Notes |
|-----------|--------|------|----------|-------|
| ID | `Component.id` | string | Yes | Must be unique across document |
| ComponentClass | `type(Component).__name__` | string | Yes | e.g., "Tank", "CentrifugalPump" |
| ComponentName | `Component.componentName` | string | Yes | Human-readable name |
| TagName | `Component.componentTag` | string | No | Process tag (e.g., "P-101") |

#### pyDEXPI Class → ComponentClass Mapping

Based on TrainingTestCases analysis (65 unique ComponentClass values):

| pyDEXPI Class | Proteus ComponentClass | Frequency | Notes |
|---------------|------------------------|-----------|-------|
| `Tank` | `Tank` | Common (9 instances) | Direct mapping |
| `CentrifugalPump` | `CentrifugalPump` | Common (8 instances) | Direct mapping |
| `PlateHeatExchanger` | `PlateHeatExchanger` | Common (9 instances) | Direct mapping |
| `PressureVessel` | `PressureVessel` | Medium | Direct mapping |
| `ProcessColumn` | `ProcessColumn` | Medium | Direct mapping |
| ... | ... | ... | See ComponentRegistry for full mapping |

**Strategy**: Use `Component.__class__.__name__` directly, as pyDEXPI class names match Proteus ComponentClass values (per DEXPI 1.2 spec).

#### Nozzles (Equipment Connection Points)

Maps from: `Equipment.nozzles` → `<Nozzle>`

| Attribute | Source | Type | Required | Notes |
|-----------|--------|------|----------|-------|
| ID | `Nozzle.id` | string | Yes | Must reference from PipingNetworkSystem |
| ComponentName | `Nozzle.componentName` | string | No | Optional nozzle label |

**Connectivity**: Nozzles link equipment to piping via `PipingNetworkSegment.fromNode`/`toNode` references.

### Piping Export

Maps from: `ConceptualModel.pipingNetworkSystems` → `<PipingNetworkSystem>`

#### PipingNetworkSystem

| Attribute | Source | Type | Required | Notes |
|-----------|--------|------|----------|-------|
| ID | `PipingNetworkSystem.id` | string | Yes | Unique system ID |
| ComponentClass | `"PipingNetworkSystem"` | string | Yes | Fixed value |

#### PipingNetworkSegment

Maps from: `PipingNetworkSystem.segments`

| Attribute | Source | Type | Required | Notes |
|-----------|--------|------|----------|-------|
| ID | `Segment.id` | string | Yes | Unique segment ID |
| ComponentClass | `type(Segment).__name__` | string | Yes | e.g., "PipingNetworkSegment" |
| fromNode | `Segment.fromNode.id` | ID reference | Yes | Start point (Nozzle/Node ID) |
| toNode | `Segment.toNode.id` | ID reference | Yes | End point (Nozzle/Node ID) |

**TrainingTestCases Pattern**: Most common segment type is `PipingNetworkSegment` (61 instances).

### Instrumentation Export

Maps from: `ConceptualModel.processInstrumentationFunctions` → `<ProcessInstrumentationFunction>`

#### ProcessInstrumentationFunction

| Attribute | Source | Type | Required | Notes |
|-----------|--------|------|----------|-------|
| ID | `Instrumentation.id` | string | Yes | Unique function ID |
| ComponentClass | `type(Instrumentation).__name__` | string | Yes | e.g., "FlowTransmitter", "PressureIndicator" |
| TagName | `Instrumentation.componentTag` | string | No | Instrument tag (e.g., "FIT-101") |

#### Signal Lines

Maps from: `SignalLine` relationships (measuring/actuating)

**TODO**: Document signal line export patterns from TrainingTestCases (Phase 1 Day 1 task).

## ID Management Strategy

### Requirements

1. **Uniqueness**: Every exported object must have a unique ID
2. **Consistency**: IDs must be consistent across import/export round-trips
3. **References**: IDs must match exactly when used in `fromNode`/`toNode` attributes

### Implementation Approach

Central `IDRegistry` class with enhanced features (implemented in `src/exporters/proteus_xml_exporter.py`):

**Key Features**:
- **Prefix mapping**: Maps component class names to unique 3-letter prefixes (avoids collisions)
- **Sequential counters**: Maintains per-prefix counters for deterministic ID generation
- **UUID normalization**: Automatically converts UUIDs and other types to strings
- **Pre-seeding**: `reserve()` method for importing existing IDs from round-trip scenarios

**Core API**:
```python
class IDRegistry:
    """Manages ID generation and validation for Proteus XML export."""

    # 16 common component prefixes pre-configured
    DEFAULT_PREFIX_MAP = {
        'Tank': 'TNK', 'CentrifugalPump': 'PMP', 'PlateHeatExchanger': 'HEX',
        'ProcessColumn': 'COL', 'PressureVessel': 'VES', 'Valve': 'VLV',
        # ... see code for complete list
    }

    def register(self, obj, preferred_id=None) -> str:
        """Register object and return its unique ID (normalizes to string)."""

    def reserve(self, obj_id: str) -> None:
        """Reserve an ID without associating it with an object."""

    def get_id(self, obj) -> Optional[str]:
        """Lookup existing ID without registering."""

    def validate_reference(self, ref_id: str) -> bool:
        """Check if reference ID exists in registry."""
```

**ID Generation Strategy**:
- Uses `DEFAULT_PREFIX_MAP` for common components (e.g., `CentrifugalPump` → `PMP0001`)
- Falls back to `class[:3].upper()` for unmapped classes
- Maintains sequential counters per prefix (`PMP0001`, `PMP0002`, ...)
- Handles prefix collisions via counter tracking

## Attribute Normalization

### String Attributes

- **Encoding**: UTF-8
- **Escaping**: XML-escape special characters (`<`, `>`, `&`, `"`, `'`)
- **Empty values**: Omit attribute if None/empty string

### Date/Time Formatting

```python
from datetime import datetime

dt = model.exportDateTime or datetime.now()
date_str = dt.strftime("%Y-%m-%d")           # "2025-11-14"
time_str = dt.strftime("%H:%M:%S.%f")[:-3]   # "11:25:30.123"
```

## XSD Validation

### Automated Validation

Use `lxml` for schema validation:

```python
from lxml import etree

def validate_proteus_xml(xml_path: str, xsd_path: str) -> bool:
    """Validate Proteus XML against XSD schema."""
    schema = etree.XMLSchema(etree.parse(xsd_path))
    doc = etree.parse(xml_path)
    return schema.validate(doc)
```

### Validation Points

1. **Post-export**: Validate every generated XML file
2. **Unit tests**: Each test should include XSD validation
3. **CI/CD**: Automated validation in test suite

## Implementation Phases

### Phase 1: Equipment Export (Days 3-4)

**Target**: Export all TaggedPlantItems with nozzles

- [ ] Equipment XML generation
- [ ] Nozzle XML generation
- [ ] ID registry integration
- [ ] 5 unit tests (Tank, Pump, HeatExchanger, Vessel, Column)
- [ ] XSD validation

### Phase 2: Piping Export (Day 5)

**Target**: Export all PipingNetworkSystems with segments

- [ ] PipingNetworkSystem XML generation
- [ ] PipingNetworkSegment XML generation
- [ ] Node reference validation
- [ ] 5 unit tests (various segment types)
- [ ] XSD validation

### Phase 3: Instrumentation Export (Days 6-7)

**Target**: Export all ProcessInstrumentationFunctions with signal lines

- [ ] ProcessInstrumentationFunction XML generation
- [ ] Signal line XML generation
- [ ] Control loop support
- [ ] 5 unit tests (transmitters, controllers, valves)
- [ ] XSD validation

## TrainingTestCases Analysis

### Component Frequency (Top 15)

Based on Codex's analysis of TrainingTestCases DEXPI 1.3:

1. `Nozzle` - 70 instances
2. `PipingNetworkSegment` - 61 instances
3. `PipingNetworkSystem` - 41 instances
4. `PlateHeatExchanger` - 9 instances
5. `Tank` - 9 instances
6. `CentrifugalPump` - 8 instances
7. `FlowTransmitter` - 6 instances
8. ... (see full analysis in Codex output)

### Coverage Gap

- **Covered by examples**: 65 / 272 components (24%)
- **Mapped in Phase 3**: 185 / 272 components (68%)
- **Strategy**: Use examples as golden references, extrapolate patterns for unmapped components

## Next Steps

### Day 1 Completed Tasks ✅

- [x] Download XSD schema
- [x] Download P&ID Profile spec
- [x] Download DEXPI spec
- [x] Create this format documentation
- [x] Create exporter skeleton (`src/exporters/proteus_xml_exporter.py`)
- [x] Codex vetting and corrections applied

### Day 2 Tasks

- [ ] Analyze XSD schema structure in detail
- [ ] Extract all element/attribute definitions
- [ ] Map pyDEXPI classes to Proteus ComponentClass values
- [ ] Document edge cases and special handling

## References

- DEXPI Specification 1.2: Section 4 (Data Model)
- Proteus PID Schema 4.2: Root XSD schema
- P&ID Profile 3.3.3: Component-specific attributes
- pyDEXPI Documentation: `pydexpi.dexpi_classes` module
- TrainingTestCases: `/tmp/TrainingTestCases/dexpi 1.3/example pids/`

---

**Status**: Day 1 initial structure complete. Ready for detailed XSD analysis and implementation.
