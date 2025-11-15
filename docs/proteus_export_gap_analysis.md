# Proteus XML Export Gap Analysis

## Methodology

- **Schema sweep.** Reviewed `docs/schemas/ProteusPIDSchema_4.2.xsd` in full with emphasis on the `PlantItem`, `Equipment`, `Nozzle`, `PipingNetworkSystem`, `PipingNetworkSegment`, `PipingComponent`, and instrumentation-related complex types (`ProcessInstrumentationFunction`, `ProcessSignalGeneratingFunction`, `InformationFlow`, `ActuatingFunction*`, `ProcessSignalGeneratingSystem`). Key references are `docs/schemas/ProteusPIDSchema_4.2.xsd:1333-1521` for the `PlantItem` attribute set, `1673-1780` for equipment/nozzles, `1783-1912` for piping, and `1912-2090` for instrumentation.
- **pyDEXPI model introspection.** Loaded `/tmp/pyDEXPI` inside the project virtual environment and enumerated Pydantic `model_fields` for all relevant classes. Examples: `equipment.Equipment`/`Nozzle` (`pydexpi/dexpi_classes/pydantic_classes.py:2038-3890`), `piping.PipingNetworkSystem`/`PipingNetworkSegment` (`pydexpi/dexpi_classes/pydantic_classes.py:2357-2412` / `2271-2346`), and instrumentation classes (`pydexpi/dexpi_classes/pydantic_classes.py:2633-2820`).
- **Exporter review.** Audited `src/exporters/proteus_xml_exporter.py` to capture the exact attributes, child elements, and helper methods currently emitted (`_export_equipment` at `src/exporters/proteus_xml_exporter.py:376-436`, `_export_piping_*` at `513-809`, `_export_instrumentation_*` at `810-1114`).
- **Importer reference.** Inspected `/tmp/pyDEXPI/pydexpi/loaders/proteus_serializer.py:1000-1240` to understand how GenericAttributes names/units are mapped back into pyDEXPI fields during import. This confirmed that every pyDEXPI data attribute must round-trip through `<GenericAttributes>` blocks with precise naming, format, and units metadata.

## Coverage Summary

| Domain | Current Coverage | Key Missing Items | Priority |
| --- | --- | --- | --- |
| PlantItem baseline | `ID`, `ComponentClass`, `ComponentName`, partial `TagName` | ComponentClassURI for equipment, Specification/Revision/Status family, Presentation/Position/Label/Association metadata | High |
| Equipment & Nozzles | Tag structure + nozzle IDs | All equipment-specific data (e.g., `equipmentDescription`, design loads), nozzle ratings, nozzle connection points, nested equipment associations | Critical |
| Piping Network System | IDs + 5 GenericAttributes (fluid + nominal diameter + line number) | 12 additional schema/pyDEXPI data points (heat tracing, insulation, jackets, onHold, etc.) | Critical |
| Piping Network Segment | IDs + nominal diameter + segmentNumber + connections | 16 data attributes, CenterLine geometry, FlowIn/FlowOut on connection points | Critical |
| Piping Components/Valves | ID + class + `pipingComponentName` and limited GenericAttributes | Component-specific data (operation, numberOfPorts, set pressures, insulation info), `Standard`/`StandardURI`, node metadata | Critical |
| ConnectionPoints/Nodes | Node IDs + Type | FlowIn/FlowOut counts, node Name/Function/Flow, diameter/rating blocks, nozzle nodes | High |
| Instrumentation Functions | Function IDs + 3 attributes + simple associations | 11 additional data attributes, ActuatingFunction/ActuatingElectricalFunction trees, signal connectors, panel metadata | Critical |
| Sensors & Signal Flow | Sensor IDs + number/type; information flow IDs + associations | Sensor location associations to equipment, signal conveying data (`portStatus`, etc.), MeasuringSystem/ProcessSignalGeneratingSystem hierarchy | High |
| Custom & Generic Attributes | Tag/sub-tag + a few piping/instrumentation fields stored as strings | All other pyDEXPI fields (enumerations, physical quantities, multilingual strings), CustomAttribute sets, Format/Units metadata | Critical |
| Actuating/Measuring systems & loops | Not exported | `ActuatingSystem`, `ActuatingElectricalSystem`, `ProcessSignalGeneratingSystem`/`MeasuringSystem`, `InstrumentationLoopFunction`, `InstrumentLoop`, `ProcessInstrument`, `Note` | High |

Priority definition: **Critical** – present pyDEXPI data is silently dropped so round-trip fidelity fails. **High** – optional schema items commonly populated or required for downstream graphics/validation. **Medium** – nice-to-have metadata. **Low** – rarely populated schema affordances.

## Detailed Findings

### 1. PlantItem Baseline & Metadata

- **Schema context.** `PlantItem` (`docs/schemas/ProteusPIDSchema_4.2.xsd:1333-1393`) contributes global child elements (`Presentation`, `Extent`, `Position`, `Scale`, `Label`, `ConnectionPoints`, `GenericAttributes`, etc.) and attributes (`Specification`, `ComponentClassURI`, `ComponentName`, `ComponentType`, `Revision`, `Status`, etc.).
- **pyDEXPI data.** `TaggedPlantItem` (`pydexpi/dexpi_classes/pydantic_classes.py:2157-2180`) exposes `tagName` + prefix/suffix/sequence as data fields inherited by all equipment. Many classes also set `customAttributes`.
- **Exporter gaps.**
  - `ComponentClassURI` is emitted for piping/instrumentation but *omitted* for equipment even though every class provides a `uri` string (Critical for RDL traceability).
  - No support for `Specification`, `ComponentType`, `Revision`, `Status`, `SpecificationURI`, or `StockNumber` even though they may exist on future pyDEXPI items (High—schema compliance).
  - No serialization of child blocks like `Presentation`, `Extent`, `Position`, `Scale`, `Label`, or `Text` from pyDEXPI graphics primitives (`pydexpi/dexpi_classes/graphics.py`). Current exporter ignores all layout metadata, preventing GraphicBuilder fidelity (High).
  - Associations between equipment and parent structures (`TechnicalItem.parentStructure`, `pydexpi/dexpi_classes/pydantic_classes.py:201-214`) are not emitted (`Association` support limited to instrumentation only) (High).

### 2. Equipment & Nozzles

- **Schema context.** `Equipment` extends `PlantItem` and allows design pressure/temperature child elements plus nested Equipment/Nozzle lists and attributes `ProcessArea`/`Purpose` (`docs/schemas/ProteusPIDSchema_4.2.xsd:1673-1708`). `Nozzle` adds `NozzleType`, `NominalDiameter`, `Rating` child elements (`1709-1730`).
- **pyDEXPI fields.** Base equipment adds `equipmentDescription` while derived classes add dozens of process data points (e.g., `CentrifugalPump.designVolumeFlowRate`, `PlateHeatExchanger.designHeatTransferArea`, `PressureVessel.nominalCapacityVolume`, etc.) as seen in `pydexpi/dexpi_classes/pydantic_classes.py:3574-4200`.
- **Exporter coverage.** `_export_equipment` only writes `ID`, `ComponentClass`, `ComponentName`, `TagName`, `ProcessArea`, `Purpose`, and limited generic attributes for tag structure (`src/exporters/proteus_xml_exporter.py:388-426`). `_export_nozzle` writes only `ID`, optional `ComponentName`, and subTag generic attribute (`426-461`).
- **Missing items (all Critical unless noted).**
  - Every equipment-specific data attribute (flow rates, capacities, design conditions, etc.) is discarded. Need generic exporter over all Pydantic data fields, including derived classes. Many of these are `Nullable*` physical quantities requiring `<GenericAttribute Units="...">`. Current Format is hardcoded to `"string"`. (Critical)
  - `equipmentDescription` (MultiLanguageString) is not exported and requires emitting separate `<GenericAttribute Name="EquipmentDescriptionAssignmentClass" Language="...">` entries (High).
  - No nozzle metadata: `nominalPressure*` fields, rating/diameter children, or nozzle `nodes` (`PipingNodeOwner`) are exported. Without `ConnectionPoints` for nozzles, piping cannot attach directly to nozzle nodes (Critical).
  - Nested equipment and subcomponents (embedded `<Equipment>`/`<Component>` per schema) never exported—the exporter iterates only top-level `taggedPlantItems` and does not recurse (High).
  - Equipment `Association` relationships (e.g., `is located in` referencing plant structure items) are not emitted (High).

### 3. PipingNetworkSystem

- **Schema context.** Systems can include numerous design/operating property elements (`NominalDiameter`, design pressures/temperatures, wall thickness) plus child `PipingNetworkSegment`s (`docs/schemas/ProteusPIDSchema_4.2.xsd:1783-1824`).
- **pyDEXPI data.** `PipingNetworkSystem` exposes 17 data fields such as `heatTracingType`, `insulationThickness`, `jacketLineNumber`, `pipingNetworkSystemGroupNumber`, etc. (`pydexpi/dexpi_classes/pydantic_classes.py:2357-2395`).
- **Exporter coverage.** `_export_piping` registers ID/class/URI, adds GenericAttributes for `fluidCode`, `lineNumber`, `pipingClassCode`, and the nominal diameter trio, then exports segments (`src/exporters/proteus_xml_exporter.py:513-561`).
- **Missing attributes (Critical).** Heat tracing, insulation, jackets, onHold, piping class info, and system grouping numbers never leave the model. Need to serialize all 17 data fields and any custom attributes. Additionally, schema-provided child elements for design pressures/temperatures are not mapped (Medium—pyDEXPI currently models these as data types rather than explicit schema elements).

### 4. PipingNetworkSegment

- **Schema context.** Segments add more child content—`Connection`, `CenterLine`, `Equipment`, `ProcessInstrument`, `PipeOffPageConnector`, etc. (`docs/schemas/ProteusPIDSchema_4.2.xsd:1825-1899`).
- **pyDEXPI data.** `PipingNetworkSegment` has 22 data fields (color codes, slopes, siphon flags, operating temperatures, etc.) plus references (`sourceItem/sourceNode/targetItem/targetNode`) (`pydexpi/dexpi_classes/pydantic_classes.py:2271-2346`).
- **Exporter coverage.** `_export_piping_network_segment` writes IDs, class, URI, limited GenericAttributes (nominal diameter + segmentNumber + fluidCode), exports segment items, omits `CenterLine`, and emits `Connection` elements (`src/exporters/proteus_xml_exporter.py:561-644`).
- **Missing items.**
  - 16 data attributes (heat tracing info, pipeline classification, slope, siphon, pressureTestCircuitNumber, etc.) are not exported (Critical).
  - `CenterLine` geometry is not built even though schema expects it for visualizing pipe runs. Need to translate pyDEXPI `Curve`/`PolyLine` objects when available (High).
  - Segment-level `ProcessInstrument`, `Equipment`, or `PipeOffPageConnector` entries are only exported if the objects appear inside `segment.items`. However, pyDEXPI tracks `processInstruments` separately via `segment.items`? Need to confirm but currently there is no handling for `segment.equipment` or `segment.processInstruments` lists (Medium).
  - No serialization of property breaks at the segment level even though schema relocated `<PropertyBreak>` here (`docs/schemas/ProteusPIDSchema_4.2.xsd:1864-1875`). Items exist in pyDEXPI (`pydexpi/dexpi_classes/pydantic_classes.py:2412-2449`) but exporter relies on them being in `segment.items`. Need explicit support (High).

### 5. Piping Components & Valves

- **pyDEXPI data.** Base `PipingComponent` offers `fluidCode`, `onHold`, `pipingClassArtefact`, `pressureTestCircuitNumber` while valve subclasses add `numberOfPorts`, `operation`, `setPressureHigh/Low`, etc. (see `pydexpi/dexpi_classes/pydantic_classes.py:2246-2575`).
- **Exporter coverage.** `_export_piping_segment_item` only emits ID/class/name and then funnels into `_export_piping_generic_attributes`, which does not know about `onHold`, `pipingClassArtefact`, `pressureTestCircuitNumber`, `operation`, etc. (`src/exporters/proteus_xml_exporter.py:599-681`).
- **Missing items.**
  - All component-specific fields (valve operation, numberOfPorts, safety valve settings, insulation/tracing) vanish (Critical).
  - `Standard` and `StandardURI` attributes mandated by schema for `PipingComponent` (`docs/schemas/ProteusPIDSchema_4.2.xsd:1741-1755`) are never filled even when pyDEXPI provides `standard`-like data (High).
  - Many components carry their own `nodes` but exporter only sets `Node` IDs and default Type without Flow/Function metadata; any `nominalDiameterRepresentation` stored on nodes is ignored (High).
  - `ProcessInstrument` piping items (instrument bubbles inside segments) are not recognized separately (High).

### 6. ConnectionPoints & Nodes

- **Schema requirements.** `ConnectionPoints` can contain `Presentation`, `Extent`, and multiple `Node`s with FlowIn/FlowOut attributes (`docs/schemas/ProteusPIDSchema_4.2.xsd:916-1240`).
- **Exporter coverage.** `_export_connection_points` registers nodes and emits `<Node ID="..." Type="{process|signal}">` entries with no additional metadata and leaves FlowIn/FlowOut unset (`src/exporters/proteus_xml_exporter.py:630-681`).
- **Missing items (High).**
  - FlowIn/FlowOut defaults and node ordering meta. Schema no longer sets defaults, so we must infer main flow indices to keep Proteus happy.
  - Node-level child elements (`NominalDiameter`, `ConnectionType`, `Rating`, `ScheduleThickness`, etc.) and attributes (`Name`, `Function`, `Flow`) are never exported despite pyDEXPI `PipingNode` containing diameter representations (`pydexpi/dexpi_classes/pydantic_classes.py:2396-2410`).
  - No nozzle connection points: `_export_nozzle` never calls `_export_connection_points`, so nozzle-to-segment node references cannot be reconstituted (Critical).

### 7. Instrumentation (Functions, Sensors, Signals, Actuators)

- **Schema context.** `ProcessInstrumentationFunction` extends `PlantItem` with child lists for actuating functions, signal generators, information flows, signal connectors, and actuating electrical functions (`docs/schemas/ProteusPIDSchema_4.2.xsd:1926-1980`). `ProcessSignalGeneratingFunction` and `InformationFlow` extend `PlantItem` themselves.
- **pyDEXPI data.** `ProcessInstrumentationFunction` has 14 data attributes (location, GMP relevance, panel ID, modifiers, vendor info, etc.), plus lists `actuatingFunctions`, `actuatingElectricalFunctions`, `processSignalGeneratingFunctions`, `signalConveyingFunctions`, and `signalConnectors` (`pydexpi/dexpi_classes/pydantic_classes.py:2682-2767`). Actuating functions and systems expose their own identifier fields (`pydexpi/dexpi_classes/pydantic_classes.py:2633-2670` & `2772-2816`).
- **Exporter coverage.** `_export_process_instrumentation_function` writes IDs/URIs, optional `componentName`, limited GenericAttributes (number/category/deviceInformation), connection points if available, associations (but before signal functions are registered), and exports sensors plus `InformationFlow` nodes. There is no support for `ActuatingFunction*`, `ActuatingSystem*`, or signal connectors (`src/exporters/proteus_xml_exporter.py:810-1010`).
- **Missing items.**
  - 11 data attributes remain unset (Critical): `location`, `panelIdentificationCode`, `processInstrumentationFunctionModifier`, `processInstrumentationFunctions`, `qualityRelevance`, `safetyRelevanceClass`, `typicalInformation`, `vendorCompanyName`, `votingSystemRepresentation`, `gmpRelevance`, `guaranteedSupplyFunction`.
  - Actuating functions and actuating electrical functions lists are ignored entirely; these need to be serialized as child elements with IDs and associations to the host PIF and piping equipment (Critical).
  - Signal connectors (`SignalOffPageConnector`) are not exported, and there is no `SignalOffPageConnectorReference` support (High).
  - Association timing bug: `_export_instrumentation_associations` runs before `_export_information_flow`, so instrumentation functions never get the `is logical end of` relationships because the signal conveying functions are not registered yet; same issue for sensors as logical starts (Critical bug).
  - `ProcessSignalGeneratingFunction.sensingLocation` is converted to `is located in` only if the location object has been exported earlier; no such export path exists for piping nodes/equipment reference objects, so associations usually fail (High).
  - `ProcessSignalGeneratingSystem`/`MeasuringSystem` and `ActuatingSystem`/`ActuatingElectricalSystem` collections in `DexpiModel.ConceptualModel` (`pydexpi/dexpi_classes/pydantic_classes.py:26-58`) are never exported (High). That also means nested `Transmitter`, `PrimaryElement`, and custom components drop all metadata.
  - `SignalConveyingFunction` data (`portStatus`, `signalConveyingType`, `signalPointNumber`, `signalProcessControlFunctions`) is never stored. Need GenericAttributes on the `<InformationFlow>` nodes (Critical for loop definition).
  - Instrument loops (`InstrumentationLoopFunction`, `InstrumentLoop`, `InformationFlow` at root) are missing entirely (High).

### 8. GenericAttributes & CustomAttributes Handling

- **Current approach.** `_export_generic_attributes`, `_export_piping_generic_attributes`, and `_export_instrumentation_generic_attributes` hard-code a tiny subset of names and always set `Format="string"` with no `Units`, `Language`, or `Specialization`.
- **Importer expectation.** `ProteusSerializer.parse_generic_attributes` (`/tmp/pyDEXPI/pydexpi/loaders/proteus_serializer.py:1070-1238`) derives pyDEXPI field names by stripping `AssignmentClass`, then inspects field annotations to parse ints, enums, or `Nullable*` physical quantities (requiring `Units` attribute). It also expects multi-language strings to be provided via repeated attributes with `Language`.
- **Gaps (Critical).**
  - Need a generic exporter that inspects each `model_field` tagged as `attribute_category="data"` and emits corresponding `<GenericAttribute>` entries under `Set="DexpiAttributes"`, preserving numeric formats, booleans, enumerations, and `Units`. Without this, hundreds of pyDEXPI attributes never leave the model.
  - Custom attributes (`customAttributes` on `CustomAttributeOwner`, `pydexpi/dexpi_classes/pydantic_classes.py:334-360`) are ignored. Must emit a `Set="CustomAttributes"` block that carries `attributeName`, `attributeURI`, and typed `value`.
  - Multi-language strings (e.g., `equipmentDescription`) require multiple `<GenericAttribute>` elements with `Language` set per string; exporter currently drops linguistic info.
  - Need consistent naming (`{FieldName[0].upper()+...}AssignmentClass`) to match importer expectations. Hard-coded names risk drift.

### 9. Missing Top-Level Collections

- **Actuating and Measuring systems.** Conceptual model surfaces `actuatingSystems` and `processSignalGeneratingSystems` but exporter only processes equipment/piping/instrumentation. Need dedicated exporters for `ActuatingSystem`, `ActuatingElectricalSystem`, `ProcessSignalGeneratingSystem`/`MeasuringSystem`, including nested components (`ActuatingSystemComponent`, `Transmitter`, `PrimaryElement`) (High).
- **Instrumentation loops, process instruments, notes, shapes.** Schema allows `InstrumentLoop`, `InstrumentationLoopFunction`, `ProcessInstrument`, `Note`, `SignalConnectorSymbol`, and `ShapeCatalogue` entries at the root (`docs/schemas/ProteusPIDSchema_4.2.xsd:1394-1630`). None are handled today (Medium to High depending on usage).
- **Plant structure.** `PlantStructureItem` and `metaData` nodes under `PlantModel` are ignored. Without them, location hierarchies referenced by equipment associations cannot be reconstructed (Medium).

### 10. Validation, Geometry, and Associations

- **CenterLine / Curve export.** Schema expects `CenterLine` under segments and actual `Curve` definitions for instrumentation `InformationFlow`. Current exporter emits neither, so Geometry-only validation and downstream visualization fail (High).
- **Associations beyond instrumentation.** Schema uses `Association` broadly (e.g., `is located in`, `has logical start`). Exporter only issues a few of them for instrumentation, leaving piping/equipment relationships absent (Medium).
- **XSD compliance.** Many required children/attributes (e.g., `Drawing`'s `Presentation` is present, but `PlantModel` may require `Extent` or `PlantInformation` order). Need to validate against full `docs/schemas/ProteusPIDSchema_4.2.xsd` after enhancements.

## Recommended Next Steps

1. **Generic attribute emission engine (Critical).** Build a reusable helper that walks pyDEXPI `model_fields` tagged as `attribute_category="data"` and writes `<GenericAttribute>` elements with accurate naming, Format, Units, and Language metadata. Handle enumerations, nullable physical quantities, multi-language strings, and custom attributes.
2. **Equipment/Nozzle enrichment (Critical).** Extend `_export_equipment`/`_export_nozzle` to:
   - Include `ComponentClassURI`, `equipmentDescription`, and any derived-class data fields.
   - Output nozzle connection points and pressure/diameter attributes.
   - Recurse into nested equipment/components and emit `Association` relationships to plant structure items.
3. **Piping coverage (Critical).** Expand `_export_piping_generic_attributes` or replace it with the generic helper so every system/segment/component field (heat tracing, insulation, operations, etc.) persists. Add node metadata, FlowIn/FlowOut, centerlines, and support for `PropertyBreak`/`PipeOffPageConnector`.
4. **Instrumentation completeness (Critical).** Serialize all ProcessInstrumentationFunction data attributes, actuating function trees, signal connectors, measuring/actuating systems, and signal conveying data. Fix association ordering so IDs exist before relationships are emitted.
5. **Top-level collections (High).** Add exporters for conceptual-model lists currently ignored (`actuatingSystems`, `processSignalGeneratingSystems`, `instrumentationLoopFunctions`, `instrumentLoop`, `notes`, etc.).
6. **Testing upgrades (Critical).** Create fixtures covering equipment/piping/instrumentation data fields (including enumerations, nullable physical quantities, and custom attributes), add round-trip tests via `/tmp/pyDEXPI/pydexpi/loaders/proteus_serializer.py`, and validate generated XML against `docs/schemas/ProteusPIDSchema_4.2.xsd`.

Addressing the above restores full attribute fidelity, aligns with pyDEXPI importer expectations, and enables true Proteus 4.2 compliance.
