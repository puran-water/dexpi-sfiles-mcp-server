# MCP Tool Usage Examples

Comprehensive examples for using all 4 updated MCP tools with Phase 2 complete coverage (272 classes).

---

## Table of Contents

1. [Equipment Tool](#1-equipment-tool-dexpi_add_equipment)
2. [Piping Tool](#2-piping-tool-dexpi_add_piping)
3. [Instrumentation Tool](#3-instrumentation-tool-dexpi_add_instrumentation)
4. [Valve Tools](#4-valve-tools)
5. [Complete System Examples](#5-complete-system-examples)

---

## 1. Equipment Tool (dexpi_add_equipment)

**Capabilities**:
- **159 equipment types** available
- Accepts both SFILES aliases and DEXPI class names
- Auto-creates appropriate nozzles based on equipment type

### Basic Usage

```python
# Using SFILES alias (lowercase)
dexpi_add_equipment(
    model_id="model_001",
    equipment_type="pump",
    tag_name="P-001"
)

# Using DEXPI class name (CamelCase)
dexpi_add_equipment(
    model_id="model_001",
    equipment_type="CentrifugalPump",
    tag_name="P-002"
)

# Both create CentrifugalPump instances - they're equivalent!
```

### Equipment with Specifications

```python
# Boiler with specifications
dexpi_add_equipment(
    model_id="model_001",
    equipment_type="boiler",
    tag_name="B-001",
    specifications={
        "nominalPressure": "150 psig",
        "designTemperature": "350 °F",
        "steamCapacity": "10000 lb/hr"
    }
)

# Heat exchanger with specifications
dexpi_add_equipment(
    model_id="model_001",
    equipment_type="PlateHeatExchanger",  # Class name
    tag_name="E-101",
    specifications={
        "heatDuty": "1000000 BTU/hr",
        "area": "500 ft²"
    }
)
```

### Equipment with Custom Nozzles

```python
# Tank with 4 custom nozzles
dexpi_add_equipment(
    model_id="model_001",
    equipment_type="tank",
    tag_name="T-001",
    nozzles=[
        {"subTagName": "N1", "nominalDiameter": "DN100", "nominalPressure": "PN16"},
        {"subTagName": "N2", "nominalDiameter": "DN50", "nominalPressure": "PN16"},
        {"subTagName": "N3", "nominalDiameter": "DN25", "nominalPressure": "PN16"},
        {"subTagName": "N4", "nominalDiameter": "DN150", "nominalPressure": "PN16"}
    ]
)
```

### Power Generation Equipment (NEW)

```python
# Complete power generation train
dexpi_add_equipment(model_id="m1", equipment_type="boiler", tag_name="B-001")
dexpi_add_equipment(model_id="m1", equipment_type="steam_generator", tag_name="SG-001")
dexpi_add_equipment(model_id="m1", equipment_type="turbine_steam", tag_name="ST-001")
dexpi_add_equipment(model_id="m1", equipment_type="generator_ac", tag_name="G-001")
dexpi_add_equipment(model_id="m1", equipment_type="condenser", tag_name="C-001")
```

### Material Handling Equipment (NEW)

```python
# Material handling system
dexpi_add_equipment(model_id="m1", equipment_type="conveyor", tag_name="CV-001")
dexpi_add_equipment(model_id="m1", equipment_type="crusher", tag_name="CR-001")
dexpi_add_equipment(model_id="m1", equipment_type="silo", tag_name="SI-001")
dexpi_add_equipment(model_id="m1", equipment_type="weigher_batch", tag_name="W-001")
```

### Separation Equipment (NEW)

```python
# Separation train
dexpi_add_equipment(model_id="m1", equipment_type="centrifuge", tag_name="CF-001")
dexpi_add_equipment(model_id="m1", equipment_type="filter", tag_name="F-001")
dexpi_add_equipment(model_id="m1", equipment_type="separator", tag_name="S-001")
dexpi_add_equipment(model_id="m1", equipment_type="dryer", tag_name="D-001")
```

---

## 2. Piping Tool (dexpi_add_piping)

**Capabilities**:
- **79 piping types** available (NEW in Phase 2.2)
- Supports pipes, flow meters, fittings, connections, etc.
- Accepts both SFILES aliases and DEXPI class names

### Basic Pipe Segment

```python
# Simple pipe segment (default)
dexpi_add_piping(
    model_id="model_001",
    segment_id="LINE-001",
    pipe_class="CS150",
    nominal_diameter=50,
    material="Carbon Steel"
)

# Explicitly specify pipe type
dexpi_add_piping(
    model_id="model_001",
    segment_id="LINE-002",
    piping_type="pipe",  # Default, can be omitted
    pipe_class="SS316",
    nominal_diameter=25,
    material="Stainless Steel 316"
)
```

### Flow Measurement (NEW)

```python
# Electromagnetic flow meter
dexpi_add_piping(
    model_id="model_001",
    segment_id="FI-001",
    piping_type="electromagnetic_flow_meter",
    pipe_class="CS150",
    nominal_diameter=50
)

# Orifice flow meter
dexpi_add_piping(
    model_id="model_001",
    segment_id="FO-001",
    piping_type="orifice_flow_meter",
    pipe_class="CS150",
    nominal_diameter=100
)

# Using DEXPI class name
dexpi_add_piping(
    model_id="model_001",
    segment_id="FI-002",
    piping_type="ElectromagneticFlowMeter",  # Class name
    pipe_class="SS316"
)
```

### Piping Fittings & Connections (NEW)

```python
# Flange connection
dexpi_add_piping(
    model_id="model_001",
    segment_id="FL-001",
    piping_type="flange",
    nominal_diameter=100
)

# Reducer
dexpi_add_piping(
    model_id="model_001",
    segment_id="RED-001",
    piping_type="reducer",
    nominal_diameter=50
)

# Tee fitting
dexpi_add_piping(
    model_id="model_001",
    segment_id="TEE-001",
    piping_type="tee",
    nominal_diameter=50
)
```

### Complete Piping Run

```python
# Pump discharge line with flow measurement
dexpi_add_piping(model_id="m1", segment_id="LINE-001", piping_type="pipe")
dexpi_add_piping(model_id="m1", segment_id="FI-001", piping_type="electromagnetic_flow_meter")
dexpi_add_piping(model_id="m1", segment_id="LINE-002", piping_type="pipe")
dexpi_add_piping(model_id="m1", segment_id="FL-001", piping_type="flange")
dexpi_add_piping(model_id="m1", segment_id="LINE-003", piping_type="pipe")
```

---

## 3. Instrumentation Tool (dexpi_add_instrumentation)

**Capabilities**:
- **34 instrumentation types** available
- Creates actual specific pyDEXPI classes (Transmitter, Positioner, etc.)
- Accepts both SFILES aliases and DEXPI class names

### Transmitters

```python
# Using SFILES alias
dexpi_add_instrumentation(
    model_id="model_001",
    instrument_type="transmitter",
    tag_name="TT-001",
    connected_equipment="T-001"
)

# Using DEXPI class name
dexpi_add_instrumentation(
    model_id="model_001",
    instrument_type="Transmitter",  # Class name
    tag_name="TT-002",
    connected_equipment="T-002"
)
```

### Positioners & Actuators

```python
# Positioner
dexpi_add_instrumentation(
    model_id="model_001",
    instrument_type="positioner",
    tag_name="POS-001"
)

# Controlled actuator
dexpi_add_instrumentation(
    model_id="model_001",
    instrument_type="ControlledActuator",  # Class name
    tag_name="ACT-001"
)
```

### Signal Functions

```python
# Signal conveying function
dexpi_add_instrumentation(
    model_id="model_001",
    instrument_type="signal_conveying_function",
    tag_name="SIG-001"
)

# Process signal generating function
dexpi_add_instrumentation(
    model_id="model_001",
    instrument_type="ProcessSignalGeneratingFunction",  # Class name
    tag_name="PSG-001"
)
```

### Complete Instrumentation Example

```python
# Temperature measurement and control
dexpi_add_instrumentation(
    model_id="m1",
    instrument_type="transmitter",
    tag_name="TT-101",
    connected_equipment="R-001"  # Reactor
)

dexpi_add_instrumentation(
    model_id="m1",
    instrument_type="positioner",
    tag_name="TV-101"
)

dexpi_add_instrumentation(
    model_id="m1",
    instrument_type="ControlledActuator",
    tag_name="TCV-101"
)
```

---

## 4. Valve Tools

**Capabilities**:
- **22 valve types** available
- 3 tools: deprecated `dexpi_add_valve`, `dexpi_add_valve_between_components`, `dexpi_insert_valve_in_segment`
- Accepts both SFILES aliases and DEXPI class names

### Add Valve Between Components (Recommended)

```python
# Ball valve using alias
dexpi_add_valve_between_components(
    model_id="model_001",
    from_component="P-001",
    to_component="T-001",
    valve_type="ball_valve",
    valve_tag="V-001",
    pipe_class="CS150"
)

# Butterfly valve using class name
dexpi_add_valve_between_components(
    model_id="model_001",
    from_component="T-001",
    to_component="E-101",
    valve_type="ButterflyValve",  # Class name
    valve_tag="V-002",
    pipe_class="CS150"
)

# Check valve
dexpi_add_valve_between_components(
    model_id="model_001",
    from_component="P-001",
    to_component="LINE-001",
    valve_type="check_valve",
    valve_tag="CV-001"
)
```

### Insert Valve in Existing Segment

```python
# Insert isolation valve in existing line
dexpi_insert_valve_in_segment(
    model_id="model_001",
    segment_id="LINE-001",
    valve_type="gate_valve",
    tag_name="V-003",
    at_position=0.5  # Middle of segment
)

# Insert safety valve
dexpi_insert_valve_in_segment(
    model_id="model_001",
    segment_id="LINE-002",
    valve_type="SpringLoadedGlobeSafetyValve",  # Class name
    tag_name="PSV-001",
    at_position=0.3
)
```

### Multiple Valves

```python
# Pump isolation valves
dexpi_add_valve_between_components(
    from_component="LINE-001",
    to_component="P-001",
    valve_type="gate_valve",
    valve_tag="V-101A"  # Suction isolation
)

dexpi_add_valve_between_components(
    from_component="P-001",
    to_component="LINE-002",
    valve_type="check_valve",
    valve_tag="CV-101"  # Pump check valve
)

dexpi_add_valve_between_components(
    from_component="LINE-002",
    to_component="LINE-003",
    valve_type="gate_valve",
    valve_tag="V-101B"  # Discharge isolation
)
```

---

## 5. Complete System Examples

### Example 1: Simple Process Unit

```python
# Create model
model_id = "process_unit_001"

# Feed tank
dexpi_add_equipment(
    model_id=model_id,
    equipment_type="tank",
    tag_name="T-001"
)

# Feed pump
dexpi_add_equipment(
    model_id=model_id,
    equipment_type="pump",
    tag_name="P-001"
)

# Reactor
dexpi_add_equipment(
    model_id=model_id,
    equipment_type="vessel_pressure",
    tag_name="R-001"
)

# Product separator
dexpi_add_equipment(
    model_id=model_id,
    equipment_type="separator",
    tag_name="S-001"
)

# Connect with piping
dexpi_connect_components(
    model_id=model_id,
    from_component="T-001",
    to_component="P-001",
    line_number="001"
)

# Add valve between pump and reactor
dexpi_add_valve_between_components(
    model_id=model_id,
    from_component="P-001",
    to_component="R-001",
    valve_type="ball_valve",
    valve_tag="V-001"
)

# Add flow measurement
dexpi_add_piping(
    model_id=model_id,
    segment_id="FI-001",
    piping_type="electromagnetic_flow_meter"
)

# Add temperature measurement on reactor
dexpi_add_instrumentation(
    model_id=model_id,
    instrument_type="transmitter",
    tag_name="TT-001",
    connected_equipment="R-001"
)
```

### Example 2: Power Generation (NEW Equipment Types)

```python
model_id = "power_plant_001"

# Boiler system
dexpi_add_equipment(model_id=model_id, equipment_type="boiler", tag_name="B-001")
dexpi_add_equipment(model_id=model_id, equipment_type="burner", tag_name="BU-001")
dexpi_add_equipment(model_id=model_id, equipment_type="chimney", tag_name="ST-001")

# Steam generation
dexpi_add_equipment(model_id=model_id, equipment_type="steam_generator", tag_name="SG-001")

# Turbine system
dexpi_add_equipment(model_id=model_id, equipment_type="turbine_steam", tag_name="ST-001")
dexpi_add_equipment(model_id=model_id, equipment_type="generator_ac", tag_name="G-001")

# Condensing system
dexpi_add_equipment(model_id=model_id, equipment_type="heat_exchanger", tag_name="C-001")
dexpi_add_equipment(model_id=model_id, equipment_type="cooling_tower", tag_name="CT-001")

# Control valves
dexpi_add_valve_between_components(
    model_id=model_id,
    from_component="SG-001",
    to_component="ST-001",
    valve_type="globe_valve",
    valve_tag="TV-001"  # Turbine steam control
)

# Instrumentation
dexpi_add_instrumentation(
    model_id=model_id,
    instrument_type="transmitter",
    tag_name="PT-001",  # Steam pressure
    connected_equipment="SG-001"
)

dexpi_add_instrumentation(
    model_id=model_id,
    instrument_type="transmitter",
    tag_name="TT-001",  # Steam temperature
    connected_equipment="SG-001"
)
```

### Example 3: Material Handling (NEW Equipment Types)

```python
model_id = "material_handling_001"

# Receiving
dexpi_add_equipment(model_id=model_id, equipment_type="weigher_batch", tag_name="W-001")

# Crushing
dexpi_add_equipment(model_id=model_id, equipment_type="crusher", tag_name="CR-001")

# Conveying
dexpi_add_equipment(model_id=model_id, equipment_type="conveyor", tag_name="CV-001")
dexpi_add_equipment(model_id=model_id, equipment_type="conveyor", tag_name="CV-002")

# Storage
dexpi_add_equipment(model_id=model_id, equipment_type="silo", tag_name="SI-001")

# Packaging
dexpi_add_equipment(model_id=model_id, equipment_type="packaging_system", tag_name="PKG-001")

# Instrumentation for level monitoring
dexpi_add_instrumentation(
    model_id=model_id,
    instrument_type="transmitter",
    tag_name="LT-001",
    connected_equipment="SI-001"
)
```

### Example 4: Using DEXPI Class Names Throughout

```python
model_id = "class_names_example"

# All using DEXPI class names for documentation clarity
dexpi_add_equipment(
    model_id=model_id,
    equipment_type="CentrifugalPump",
    tag_name="P-001"
)

dexpi_add_equipment(
    model_id=model_id,
    equipment_type="PlateHeatExchanger",
    tag_name="E-101"
)

dexpi_add_valve_between_components(
    model_id=model_id,
    from_component="P-001",
    to_component="E-101",
    valve_type="BallValve",
    valve_tag="V-001"
)

dexpi_add_piping(
    model_id=model_id,
    segment_id="FI-001",
    piping_type="ElectromagneticFlowMeter"
)

dexpi_add_instrumentation(
    model_id=model_id,
    instrument_type="Transmitter",
    tag_name="TT-001",
    connected_equipment="E-101"
)
```

---

## Type Reference Quick Links

- **Equipment**: [EQUIPMENT_CATALOG.md](./EQUIPMENT_CATALOG.md) - All 159 equipment types
- **Piping**: 79 types (pipes, flow meters, fittings, connections, valves)
- **Instrumentation**: 34 types (transmitters, positioners, actuators, signal functions)
- **Valves**: 22 types (ball, butterfly, gate, globe, check, safety, etc.)

---

## Common Patterns

### Pattern 1: Pump with Isolation & Check Valves

```python
# Suction isolation
dexpi_add_valve_between_components(
    from_component="T-001",
    to_component="P-001",
    valve_type="gate_valve",
    valve_tag="V-101A"
)

# Pump
dexpi_add_equipment(equipment_type="pump", tag_name="P-001")

# Discharge check valve
dexpi_add_valve_between_components(
    from_component="P-001",
    to_component="LINE-001",
    valve_type="check_valve",
    valve_tag="CV-101"
)

# Discharge isolation
dexpi_add_valve_between_components(
    from_component="LINE-001",
    to_component="HEADER-001",
    valve_type="gate_valve",
    valve_tag="V-101B"
)
```

### Pattern 2: Heat Exchanger with Control

```python
# Heat exchanger
dexpi_add_equipment(
    equipment_type="PlateHeatExchanger",
    tag_name="E-101"
)

# Temperature control valve
dexpi_add_valve_between_components(
    from_component="STEAM-HEADER",
    to_component="E-101",
    valve_type="globe_valve",
    valve_tag="TCV-101"
)

# Temperature measurement
dexpi_add_instrumentation(
    instrument_type="transmitter",
    tag_name="TT-101",
    connected_equipment="E-101"
)

# Control positioner
dexpi_add_instrumentation(
    instrument_type="positioner",
    tag_name="POS-101"
)
```

### Pattern 3: Flow Measurement with Isolation

```python
# Upstream isolation
dexpi_add_valve_between_components(
    from_component="LINE-001",
    to_component="FI-001",
    valve_type="ball_valve",
    valve_tag="V-001A"
)

# Flow meter
dexpi_add_piping(
    segment_id="FI-001",
    piping_type="electromagnetic_flow_meter"
)

# Downstream isolation
dexpi_add_valve_between_components(
    from_component="FI-001",
    to_component="LINE-002",
    valve_type="ball_valve",
    valve_tag="V-001B"
)
```

---

**Last Updated**: November 11, 2025
**Phase**: 2.2 Complete - All 272 classes accessible via MCP tools
