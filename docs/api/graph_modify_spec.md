# graph_modify API Specification

**Version:** 1.0.0-draft
**Status:** Phase 0.5 Design (Specification Only)
**Last Updated:** 2025-11-06
**Codex Approved:** ✅

---

## Overview

> **NOTE:** This document captures a future design. The `graph_modify` MCP tool has not been implemented in the repository yet.

The proposed `graph_modify` tool provides **tactical-level operations** for targeted modifications to engineering diagrams. It bridges the gap between low-level primitive operations (`model_tx_apply`) and high-level pattern deployment (`area_deploy`).

**Design Philosophy**: Thin wrappers over upstream pyDEXPI and SFILES2 toolkits, not custom implementations.

### Design Goals

- Cover 80%+ of "point change" use cases
- Provide self-documenting actions visible in MCP schema
- Leverage upstream toolkits (pyDEXPI piping_toolkit, SFILES2 Flowsheet methods)
- Offer single-call operations with transaction safety
- Maintain DEXPI/SFILES parity with explicit error handling

---

## Tool Signature

```python
def graph_modify(
    model_id: str,
    action: GraphAction,
    target: TargetSelector,
    payload: ActionPayload,
    options: Optional[ModifyOptions] = None
) -> GraphModifyResponse:
    """
    Apply a tactical graph modification to a model.

    Args:
        model_id: Model identifier
        action: Action type from GraphAction enum
        target: Component/segment/stream selector
        payload: Action-specific parameters
        options: Modification options (transaction, validation, etc.)

    Returns:
        GraphModifyResponse with mutated entities and diff
    """
```

---

## Action Enum (10 Core Actions)

### Component Operations

#### 1. `insert_component`

**Purpose**: Add a new standalone component to the model

**DEXPI**: Creates equipment with auto-generated nozzles
**SFILES**: Creates unit operation node

**Payload Schema**:
```typescript
{
  component_type: string,        // "CentrifugalPump", "Tank", "reactor"
  tag: string,                   // "P-101", "TK-201", "R-01"
  attributes?: {                 // Component-specific attributes
    nominalDiameter?: string,
    capacity?: number,
    material?: string,
    temperature?: number,
    pressure?: number,
    [key: string]: any
  },
  nozzles?: Array<{              // DEXPI only: custom nozzle config
    subTagName: string,
    nominalDiameter: string,
    nominalPressure?: string
  }>,
  position?: {x: number, y: number}  // Optional layout hint
}
```

**Implementation**: Direct call to `dexpi_tools.add_equipment()` or `sfiles_tools.add_unit()`

**Example**:
```json
{
  "model_id": "dexpi-plant-01",
  "action": "insert_component",
  "target": {"kind": "model", "identifier": "dexpi-plant-01"},
  "payload": {
    "component_type": "CentrifugalPump",
    "tag": "P-101",
    "attributes": {
      "nominalDiameter": "DN100",
      "flow_rate": 150
    }
  }
}
```

---

#### 2. `remove_component`

**Purpose**: Delete a component from the model

**DEXPI**: Removes equipment, optionally disconnects/reroutes piping
**SFILES**: Removes unit, optionally reroutes streams

**Payload Schema**:
```typescript
{
  cascade?: boolean,              // Delete connected components? (default: false)
  reroute_connections?: boolean,  // Try to reconnect around deleted (default: true)
  preserve_topology?: boolean     // Maintain connectivity (default: true)
}
```

**Implementation**:
- Resolve target component
- If `reroute_connections`, use `connect_piping_network_segment()` to reconnect
- Delete component and orphaned segments

**Example**:
```json
{
  "action": "remove_component",
  "target": {"kind": "component", "identifier": "P-102"},
  "payload": {
    "reroute_connections": true,
    "cascade": false
  }
}
```

---

#### 3. `update_component`

**Purpose**: Modify attributes of an existing component

**DEXPI**: Updates equipment attributes
**SFILES**: Updates unit parameters

**Payload Schema**:
```typescript
{
  attributes: {                   // Attributes to update
    [key: string]: any
  },
  merge: boolean                  // Merge (true) vs replace all (false), default: true
}
```

**Implementation**: Direct attribute update on component object

**Example**:
```json
{
  "action": "update_component",
  "target": {"kind": "component", "identifier": "R-01"},
  "payload": {
    "attributes": {
      "capacity": 5000,
      "temperature": 85
    },
    "merge": true
  }
}
```

---

#### 4. `insert_inline_component`

**Purpose**: Insert component into existing piping segment or stream

**DEXPI (planned approach):** Uses `insert_item_to_segment()` from `pydexpi/toolkits/piping_toolkit.py:532-707`
**SFILES:** Not applicable (streams are edges, not segmented)

**Payload Schema**:
```typescript
{
  component_type: string,         // "CheckValve", "BallValve", "FlowMeter"
  tag: string,
  position: number,               // 0.0-1.0 along segment (0=start, 1=end)
  attributes?: {
    nominalDiameter?: string,
    nominalPressure?: string,
    [key: string]: any
  }
}
```

**Implementation** (DEXPI):
```python
from pydexpi.toolkits.piping_toolkit import (
    insert_item_to_segment,
    piping_network_segment_validity_check
)

# 1. Resolve target segment
segment = resolve_segment(target.identifier)

# 2. Create PipingNetworkSegmentItem
item = create_piping_item(payload.component_type, payload.tag, payload.attributes)

# 3. Call upstream toolkit
result = insert_item_to_segment(
    model=model,
    segment=segment,
    item=item,
    position=payload.position
)

# 4. Validate post-operation
validity = piping_network_segment_validity_check(model, new_segments)

# 5. Return diff
return build_response(mutated=[segment.id, item.id], diff=calculate_diff(before, after))
```

**Example**:
```json
{
  "action": "insert_inline_component",
  "target": {"kind": "segment", "identifier": "SEG-outlet-42"},
  "payload": {
    "component_type": "CheckValve",
    "tag": "CV-101",
    "position": 0.3,
    "attributes": {"nominalDiameter": "DN100"}
  }
}
```

---

### Segment Operations (DEXPI Only)

#### 5. `split_segment`

**Purpose**: Split a piping segment at a specific position

**DEXPI (planned approach):** Custom logic using pyDEXPI utilities
**SFILES:** Not applicable

**Payload Schema**:
```typescript
{
  split_point: number,            // 0.0-1.0 position along segment
  insert?: {                      // Optional: insert component at split
    component_type: string,
    tag: string,
    attributes?: object
  }
}
```

**Implementation** (DEXPI):
```python
from pydexpi.toolkits.piping_toolkit import (
    find_final_connection,
    construct_new_segment,
    piping_network_segment_validity_check
)

# 1. Resolve segment
segment = resolve_segment(target.identifier)

# 2. Calculate split point
split_connections = calculate_split_point(segment, payload.split_point)

# 3. Create two new segments
segment_1 = construct_new_segment(
    start=segment.start,
    end=split_connections.midpoint,
    properties=segment.properties
)
segment_2 = construct_new_segment(
    start=split_connections.midpoint,
    end=segment.end,
    properties=segment.properties
)

# 4. Optional: Insert component at split point
if payload.insert:
    component = create_component(payload.insert)
    connect(segment_1.end, component.inlet)
    connect(component.outlet, segment_2.start)

# 5. Validate
validity = piping_network_segment_validity_check(model, [segment_1, segment_2])

# 6. Remove old segment, add new
model.remove(segment)
model.add(segment_1, segment_2)
```

**Example**:
```json
{
  "action": "split_segment",
  "target": {"kind": "segment", "identifier": "SEG-42"},
  "payload": {
    "split_point": 0.5,
    "insert": {
      "component_type": "GateValve",
      "tag": "V-201"
    }
  }
}
```

---

#### 6. `merge_segments`

**Purpose**: Combine two adjacent segments into one

**DEXPI (planned approach):** Custom logic with validity checks
**SFILES:** Not applicable

**Payload Schema**:
```typescript
{
  second_segment_id: string,      // ID of segment to merge into target
  inherit_properties?: "first" | "second" | "merge"  // default: "first"
}
```

**Implementation** (DEXPI):
```python
# 1. Resolve both segments
segment_1 = resolve_segment(target.identifier)
segment_2 = resolve_segment(payload.second_segment_id)

# 2. Verify adjacency
if not are_adjacent(segment_1, segment_2):
    raise ValueError("Segments must share a connection point")

# 3. Create merged segment
merged = construct_new_segment(
    start=segment_1.start,
    end=segment_2.end,
    properties=inherit_properties(segment_1, segment_2, payload.inherit_properties)
)

# 4. Validate
validity = piping_network_segment_validity_check(model, [merged])

# 5. Replace
model.remove(segment_1, segment_2)
model.add(merged)
```

---

#### 7. `rewire_connection`

**Purpose**: Change routing of a connection

**DEXPI (planned approach):** Uses `connect_piping_network_segment()` from `pydexpi/toolkits/piping_toolkit.py:134-207`
**SFILES (planned approach):** Direct NetworkX edge manipulation + `convert_to_sfiles()` canonicalization

**Payload Schema**:
```typescript
{
  from: string | null,            // New source component/nozzle (null = keep current)
  to: string | null,              // New target component/nozzle (null = keep current)
  via?: string[],                 // Optional intermediate components
  preserve_properties?: boolean   // Keep segment properties (default: true)
}
```

**Implementation** (DEXPI):
```python
from pydexpi.toolkits.piping_toolkit import connect_piping_network_segment

# 1. Resolve current connection
current_segment = resolve_segment(target.identifier)

# 2. Resolve new endpoints
from_nozzle = resolve_nozzle(payload.from) if payload.from else current_segment.start
to_nozzle = resolve_nozzle(payload.to) if payload.to else current_segment.end

# 3. Call upstream toolkit
new_segment = connect_piping_network_segment(
    model=model,
    from_nozzle=from_nozzle,
    to_nozzle=to_nozzle,
    properties=current_segment.properties if payload.preserve_properties else {}
)

# 4. Remove old segment
model.remove(current_segment)
```

**Implementation** (SFILES):
```python
# 1. Resolve stream
stream = resolve_stream(target.identifier)

# 2. Update NetworkX graph
flowsheet.state.remove_edge(stream.from_unit, stream.to_unit)
flowsheet.state.add_edge(
    payload.from or stream.from_unit,
    payload.to or stream.to_unit,
    **stream.properties if payload.preserve_properties else {}
)

# 3. Re-canonicalize
flowsheet.convert_to_sfiles()
```

**Example** (DEXPI):
```json
{
  "action": "rewire_connection",
  "target": {"kind": "segment", "identifier": "SEG-42"},
  "payload": {
    "from": "P-101/outlet",
    "to": "V-201/inlet",
    "preserve_properties": true
  }
}
```

---

### Property Operations

#### 8. `set_tag_properties`

**Purpose**: Update tag name or metadata

**DEXPI**: Updates TagName, TagNameAssignmentClass
**SFILES**: Updates unit name/tag

**Payload Schema**:
```typescript
{
  new_tag?: string,               // New tag name
  metadata?: {                    // Additional tag metadata
    description?: string,
    area?: string,
    service?: string,
    sequence?: number,
    [key: string]: any
  }
}
```

**Implementation**:
```python
# 1. Resolve component
component = resolve_component(target.identifier)

# 2. Update tag
if payload.new_tag:
    component.tag = payload.new_tag

# 3. Update metadata
if payload.metadata:
    for key, value in payload.metadata.items():
        setattr(component, key, value)
```

**Example**:
```json
{
  "action": "set_tag_properties",
  "target": {"kind": "component", "identifier": "P-101"},
  "payload": {
    "new_tag": "P-101A",
    "metadata": {
      "description": "Primary feed pump",
      "area": "Feed Section"
    }
  }
}
```

---

#### 9. `update_stream_properties`

**Purpose**: Modify stream attributes (SFILES only)

**DEXPI:** Not applicable (use `update_component` for piping properties)
**SFILES (planned approach):** Updates stream properties + re-canonicalization

**Payload Schema**:
```typescript
{
  properties: {
    flow?: number,
    temperature?: number,
    pressure?: number,
    composition?: object,
    [key: string]: any
  },
  merge: boolean                  // Merge vs replace, default: true
}
```

**Implementation** (SFILES):
```python
# 1. Resolve stream
stream = resolve_stream(target.identifier)

# 2. Update properties
if payload.merge:
    stream.properties.update(payload.properties)
else:
    stream.properties = payload.properties

# 3. Update NetworkX edge
flowsheet.state[stream.from_unit][stream.to_unit].update(stream.properties)

# 4. Re-canonicalize
flowsheet.convert_to_sfiles()
```

**Example**:
```json
{
  "action": "update_stream_properties",
  "target": {"kind": "stream", "identifier": "feed-stream"},
  "payload": {
    "properties": {
      "flow": 150,
      "temperature": 25,
      "pressure": 2.5
    },
    "merge": true
  }
}
```

---

### Instrumentation Operations

#### 10. `toggle_instrumentation`

**Purpose**: Add or remove instrumentation

**DEXPI**: Adds/removes instruments and signal lines
**SFILES**: Adds/removes control tags

**Payload Schema**:
```typescript
{
  operation: "add" | "remove",
  instrument_type: string,        // "FlowTransmitter", "FC", "LC", "TC", "PC"
  tag: string,
  sensing_location?: string,      // Where instrument measures (for add)
  actuating_location?: string,    // Where instrument acts (for add)
  control_params?: {              // Control parameters (for add)
    setpoint?: number,
    units?: string,
    control_mode?: string,
    [key: string]: any
  }
}
```

**Implementation** (DEXPI - add):
```python
# 1. Create instrument
instrument = create_instrument(payload.instrument_type, payload.tag)

# 2. Resolve locations
sensing = resolve_component(payload.sensing_location)
actuating = resolve_component(payload.actuating_location)

# 3. Add signal lines
signal_line_1 = create_signal_line(sensing, instrument)
signal_line_2 = create_signal_line(instrument, actuating)

# 4. Add to model
model.add(instrument, signal_line_1, signal_line_2)
```

**Implementation** (SFILES - add):
```python
# 1. Resolve unit
unit = resolve_unit(payload.sensing_location)

# 2. Add control tag
flowsheet.add_control(
    control_type=payload.instrument_type,
    control_name=payload.tag,
    connected_unit=unit.name,
    signal_to=payload.actuating_location
)
```

**Example**:
```json
{
  "action": "toggle_instrumentation",
  "target": {"kind": "component", "identifier": "V-101"},
  "payload": {
    "operation": "add",
    "instrument_type": "FlowController",
    "tag": "FC-101",
    "sensing_location": "SEG-outlet",
    "actuating_location": "V-101",
    "control_params": {
      "setpoint": 150,
      "units": "m3/h"
    }
  }
}
```

---

## Target Selector Schema

```typescript
{
  kind: "component" | "segment" | "stream" | "port" | "model",
  identifier: string,             // Tag name, GUID, or wildcard pattern
  selector?: {                    // Optional filters for ambiguous targets
    class?: string,               // Component class filter
    service?: string,             // Service type filter
    area?: string,                // Area filter
    attributes?: {                // Attribute-based filters
      [key: string]: any
    }
  }
}
```

**Resolution Logic**:
1. Try exact match on `identifier`
2. If wildcard (`*`), apply `selector` filters
3. If multiple matches, return error with candidate list
4. Fall back to `search_execute` for complex queries

**Examples**:
```json
// Simple: Target by tag
{"kind": "component", "identifier": "P-101"}

// Wildcard with filter
{"kind": "component", "identifier": "P-*", "selector": {"class": "CentrifugalPump"}}

// Target segment by ID
{"kind": "segment", "identifier": "SEG-42"}

// Target stream
{"kind": "stream", "identifier": "feed-stream"}

// Model-level (for insert_component)
{"kind": "model", "identifier": "dexpi-plant-01"}
```

---

## Response Format

```typescript
{
  ok: boolean,
  data?: {
    mutated_entities: string[],      // IDs/tags of changed components
    diff: {
      added: string[],                // IDs of added components
      removed: string[],              // IDs of removed components
      updated: string[]               // IDs of modified components
    },
    validation: {                     // Validation results
      errors: ValidationError[],
      warnings: ValidationWarning[]
    },
    new_tags?: {                      // Tag mappings for renamed components
      [old_tag: string]: string       // -> new_tag
    },
    transaction_id?: string           // If auto-transaction enabled
  },
  error?: {
    code: ErrorCode,
    message: string,
    details?: object
  }
}
```

---

## Modify Options

```typescript
{
  create_transaction?: boolean,       // Auto-wrap in transaction (default: true)
  idempotency_key?: string,          // Prevent duplicate operations
  validate_before?: boolean,         // Run validation before modify (default: true)
  validate_after?: boolean,          // Run validation after modify (default: true)
  dry_run?: boolean,                 // Preview changes without applying (default: false)
  diff_format?: "summary" | "detailed"  // Diff detail level (default: "summary")
}
```

**Default Behavior**:
- Modifications wrapped in auto-transaction (begin → apply → commit)
- Pre-validation enabled (fails fast on invalid payloads)
- Post-validation disabled (user can enable for safety)
- Full diff returned in response

---

## DEXPI/SFILES Parity Matrix (Planned)

| Action | DEXPI (planned) | SFILES (planned) | Implementation Outline |
|--------|-----------------|------------------|-----------------------|
| `insert_component` | Yes | Yes | Direct toolkit calls |
| `remove_component` | Yes | Yes | Custom with reroute logic |
| `update_component` | Yes | Yes | Direct attribute update |
| `insert_inline_component` | Yes | N/A | `insert_item_to_segment()` |
| `split_segment` | Yes | N/A | Custom using utilities |
| `merge_segments` | Yes | N/A | Custom with validity check |
| `rewire_connection` | Yes | Yes | `connect_piping_network_segment()` / NetworkX |
| `set_tag_properties` | Yes | Yes | Direct property update |
| `update_stream_properties` | N/A | Yes | NetworkX + canonicalize |
| `toggle_instrumentation` | Yes | Yes | Different instrument models |

**Error Handling**: Actions not applicable return:
```json
{
  "ok": false,
  "error": {
    "code": "ACTION_NOT_APPLICABLE",
    "message": "Action 'split_segment' not applicable to SFILES models",
    "details": {"model_type": "sfiles", "action": "split_segment"}
  }
}
```

---

## Validation Rules

Each action performs pre-validation:

1. **Target existence**: Target must exist in model
2. **Type compatibility**: Component type valid for model standard
3. **Connection validity**: Connections respect port types/directions (via `piping_network_segment_validity_check`)
4. **Tag uniqueness**: New tags must be unique
5. **Attribute schema**: Attributes match component schema
6. **Geometric validity**: Positions in valid range (0.0-1.0)

**Validation Integration**:
- **DEXPI**: `piping_network_segment_validity_check()` post-operation
- **DEXPI**: `MLGraphLoader.validate_graph_format()` for full model (if enabled)
- **SFILES**: `convert_to_sfiles()` validates canonicalization

---

## Performance Requirements

| Action | Target Latency | Notes |
|--------|---------------|-------|
| Simple operations | <100ms | insert_component, update_component, set_tag_properties |
| Complex operations | <200ms | insert_inline_component, split_segment, toggle_instrumentation |
| Validation overhead | +50ms | When validate_after=true |

**Atomicity**: All changes committed or rolled back together (via TransactionManager integration)

**Idempotency**: Same operation with same `idempotency_key` produces identical result

---

## Error Codes

| Code | Description |
|------|-------------|
| `TARGET_NOT_FOUND` | Target selector matched no components |
| `TARGET_AMBIGUOUS` | Target selector matched multiple components |
| `ACTION_NOT_APPLICABLE` | Action not supported for model type |
| `INVALID_PAYLOAD` | Payload schema validation failed |
| `VALIDATION_FAILED` | Pre/post-validation checks failed |
| `COMPONENT_TYPE_UNKNOWN` | Unknown component type for model standard |
| `TAG_CONFLICT` | Tag already exists in model |
| `CONNECTION_INVALID` | Connection violates port constraints |
| `POSITION_OUT_OF_RANGE` | Position not in 0.0-1.0 range |
| `SEGMENTS_NOT_ADJACENT` | Segments don't share connection point (merge_segments) |
| `TRANSACTION_FAILED` | Transaction rollback occurred |
| `TOOLKIT_ERROR` | Upstream toolkit function failed |

---

## Integration Points

### With TransactionManager

```python
# Auto-transaction wrapping (default)
response = graph_modify(
    model_id="dexpi-01",
    action="insert_inline_component",
    target={"kind": "segment", "identifier": "SEG-42"},
    payload={...},
    options={"create_transaction": True}  # default
)

# Manual transaction control
tx_id = transaction_manager.begin("dexpi-01")
try:
    response = graph_modify(..., options={"create_transaction": False})
    transaction_manager.commit(tx_id)
except Exception:
    transaction_manager.rollback(tx_id)
```

### With Operation Registry

```python
# graph_modify operations exposed in registry
registry.register(OperationDescriptor(
    name="graph_modify_insert_component",
    category="tactical",
    handler=graph_modify_handler,
    inputSchema=insert_component_schema,
    ...
))

# model_tx_apply can delegate to graph_modify
model_tx_apply(
    model_id="dexpi-01",
    operations=[{
        "tool": "graph_modify",
        "params": {
            "action": "insert_inline_component",
            ...
        }
    }]
)
```

### With Validation Tools

```python
# Post-operation validation
from pydexpi.toolkits.piping_toolkit import piping_network_segment_validity_check
from pydexpi.loaders.ml_graph_loader import MLGraphLoader

# After graph_modify
if options.validate_after:
    # Segment-level validation
    validity = piping_network_segment_validity_check(model, affected_segments)

    # Full model validation
    loader = MLGraphLoader()
    validation_result = loader.validate_graph_format(model)
```

---

## Future Extensions

Potential actions for v2.0:

- `copy_component` - Duplicate component with new tag
- `mirror_pattern` - Mirror components across axis
- `cascade_update` - Update component and connected components
- `optimize_layout` - Auto-arrange components
- `apply_mini_template` - Inline pattern instantiation
- `replicate_section` - Copy entire process section

---

## Success Criteria

This API satisfies "if well designed" qualifier:

- Planned coverage of 80%+ of point-change use cases (10 core actions)
- Self-documenting action enums in MCP schema (design goal)
- Clear payload contracts for each action
- Leverages upstream toolkits (`insert_item_to_segment`, `connect_piping_network_segment`)
- Documents DEXPI/SFILES parity with explicit N/A handling
- Targets single-call operations (no multi-step coordination)
- Designs for transaction safety (atomic, rollback on error)
- Performance targets: <100 ms simple actions, <200 ms complex ones
- Thin wrappers over upstream code to minimize maintenance

---

**Next Steps:**
1. Implementation in Phase 1 (after Operation Registry and TransactionManager specs)
2. Integration testing with pyDEXPI toolkit functions
3. Performance benchmarking against targets
4. User acceptance testing with real engineering workflows
