# User Migration Guide: Phase 2 Complete Coverage

This guide helps you take advantage of the complete pyDEXPI coverage introduced in Phase 2 (272 classes: 159 equipment, 79 piping, 34 instrumentation).

---

## What's New in Phase 2

### Phase 2.1: ComponentRegistry (Backend)
- All 272 pyDEXPI classes are now registered in the system
- Unified component management with family mappings
- Category-based organization

### Phase 2.2: MCP Tool Updates (User-Facing)
- **ALL 272 classes** now accessible via MCP tools
- **Dual naming support**: Use either SFILES aliases OR DEXPI class names
- **New capabilities**: Piping type selection, complete instrumentation support

---

## Breaking Changes

**NONE** - Phase 2 is fully backward compatible.

All existing code continues to work exactly as before. The changes only ADD new capabilities.

---

## New Capabilities

### 1. 5.3x More Equipment Types (30 → 159)

**Before Phase 2**:
```python
# Only ~30 equipment types available
dexpi_add_equipment(equipment_type="pump", ...)        # ✅ Worked
dexpi_add_equipment(equipment_type="boiler", ...)      # ❌ Error
dexpi_add_equipment(equipment_type="conveyor", ...)    # ❌ Error
```

**After Phase 2**:
```python
# All 159 equipment types available
dexpi_add_equipment(equipment_type="pump", ...)        # ✅ Works
dexpi_add_equipment(equipment_type="boiler", ...)      # ✅ Works
dexpi_add_equipment(equipment_type="conveyor", ...)    # ✅ Works
dexpi_add_equipment(equipment_type="steam_generator", ...)  # ✅ Works
dexpi_add_equipment(equipment_type="crusher", ...)     # ✅ Works
```

**See**: [EQUIPMENT_CATALOG.md](./EQUIPMENT_CATALOG.md) for complete list

### 2. DEXPI Class Names Now Accepted

**Before Phase 2**:
```python
# Only SFILES aliases worked
dexpi_add_equipment(equipment_type="pump", ...)              # ✅ Worked
dexpi_add_equipment(equipment_type="CentrifugalPump", ...)   # ❌ Schema error
```

**After Phase 2**:
```python
# Both aliases AND class names work
dexpi_add_equipment(equipment_type="pump", ...)              # ✅ Works
dexpi_add_equipment(equipment_type="CentrifugalPump", ...)   # ✅ Works

# These are equivalent:
dexpi_add_equipment(equipment_type="boiler", ...)            # SFILES alias
dexpi_add_equipment(equipment_type="Boiler", ...)            # DEXPI class name
```

### 3. Piping Type Selection (NEW)

**Before Phase 2**:
```python
# Only created basic Pipe
dexpi_add_piping(segment_id="LINE-001", ...)
# → Always created Pipe class
```

**After Phase 2**:
```python
# Can specify 79 different piping types
dexpi_add_piping(
    segment_id="LINE-001",
    piping_type="pipe",  # Basic pipe (default)
    ...
)

dexpi_add_piping(
    segment_id="FI-001",
    piping_type="electromagnetic_flow_meter",  # Flow meter
    ...
)

dexpi_add_piping(
    segment_id="FL-001",
    piping_type="flange",  # Flange connection
    ...
)

# Also accepts class names:
dexpi_add_piping(
    segment_id="FI-001",
    piping_type="ElectromagneticFlowMeter",  # DEXPI class name
    ...
)
```

### 4. Complete Instrumentation Support

**Before Phase 2**:
```python
# Only created generic ProcessInstrumentationFunction
dexpi_add_instrumentation(instrument_type="transmitter", ...)
# → Always created ProcessInstrumentationFunction (wrong!)
```

**After Phase 2**:
```python
# Creates actual specific classes
dexpi_add_instrumentation(instrument_type="transmitter", ...)
# → Creates Transmitter instance

dexpi_add_instrumentation(instrument_type="positioner", ...)
# → Creates Positioner instance

dexpi_add_instrumentation(instrument_type="ControlledActuator", ...)
# → Creates ControlledActuator instance (class name works too!)
```

All 34 instrumentation types now instantiate the correct pyDEXPI classes.

---

## Migration Examples

### Example 1: Power Generation Plant

**Old Code** (Before Phase 2):
```python
# Could only use limited equipment types
dexpi_add_equipment(equipment_type="pump", tag_name="P-001")
dexpi_add_equipment(equipment_type="tank", tag_name="T-001")
# boiler, steam_generator not available! ❌
```

**New Code** (After Phase 2):
```python
# Now can use complete power generation equipment
dexpi_add_equipment(equipment_type="pump", tag_name="P-001")
dexpi_add_equipment(equipment_type="boiler", tag_name="B-001")
dexpi_add_equipment(equipment_type="steam_generator", tag_name="SG-001")
dexpi_add_equipment(equipment_type="turbine_steam", tag_name="ST-001")
dexpi_add_equipment(equipment_type="generator_ac", tag_name="G-001")
dexpi_add_equipment(equipment_type="condenser", tag_name="C-001")
```

### Example 2: Material Handling System

**Old Code** (Before Phase 2):
```python
# Limited to basic equipment
# conveyor, crusher, silo not available! ❌
```

**New Code** (After Phase 2):
```python
# Complete material handling capabilities
dexpi_add_equipment(equipment_type="conveyor", tag_name="CV-001")
dexpi_add_equipment(equipment_type="crusher", tag_name="CR-001")
dexpi_add_equipment(equipment_type="silo", tag_name="SI-001")
dexpi_add_equipment(equipment_type="weigher_batch", tag_name="W-001")
dexpi_add_equipment(equipment_type="packaging_system", tag_name="PKG-001")
```

### Example 3: Using DEXPI Class Names

**New Capability** (Phase 2.2):
```python
# Can now use proper DEXPI class names from documentation
dexpi_add_equipment(
    equipment_type="CentrifugalPump",  # From pyDEXPI docs
    tag_name="P-001"
)

dexpi_add_equipment(
    equipment_type="PlateHeatExchanger",  # From pyDEXPI docs
    tag_name="E-101"
)

# Valves too:
dexpi_add_valve_between_components(
    from_component="P-001",
    to_component="E-101",
    valve_type="BallValve",  # DEXPI class name
    valve_tag="V-001"
)
```

### Example 4: Piping with Flow Measurement

**Old Code** (Before Phase 2):
```python
# Could only create basic pipe segments
dexpi_add_piping(segment_id="LINE-001")
# → Basic Pipe only
```

**New Code** (After Phase 2):
```python
# Can specify piping component types
dexpi_add_piping(
    segment_id="LINE-001",
    piping_type="pipe"  # Basic pipe
)

dexpi_add_piping(
    segment_id="FI-001",
    piping_type="electromagnetic_flow_meter"  # Flow meter inline
)

dexpi_add_piping(
    segment_id="FO-001",
    piping_type="orifice_flow_meter"  # Orifice plate
)

dexpi_add_piping(
    segment_id="FL-001",
    piping_type="flange"  # Flange connection
)
```

---

## Best Practices

### 1. Choose the Naming Style That Fits Your Use Case

**SFILES Aliases** (lowercase, underscore-separated):
- ✅ More concise
- ✅ Matches SFILES notation
- ✅ Good for scripting

```python
dexpi_add_equipment(equipment_type="pump", ...)
dexpi_add_equipment(equipment_type="heat_exchanger", ...)
```

**DEXPI Class Names** (CamelCase):
- ✅ Matches pyDEXPI documentation
- ✅ More explicit/self-documenting
- ✅ Good for collaborative projects

```python
dexpi_add_equipment(equipment_type="CentrifugalPump", ...)
dexpi_add_equipment(equipment_type="PlateHeatExchanger", ...)
```

**Both are equally valid** - choose based on your preference!

### 2. Use Equipment Families for Flexibility

When you don't need a specific type, use the family alias:

```python
# Generic pump - system chooses appropriate type
dexpi_add_equipment(equipment_type="pump", ...)

# Specific pump type when needed
dexpi_add_equipment(equipment_type="pump_reciprocating", ...)
dexpi_add_equipment(equipment_type="ReciprocatingPump", ...)  # Same thing
```

### 3. Leverage Type Counts in Tool Descriptions

All MCP tools now report how many types are available:

- `dexpi_add_equipment`: "159 types available"
- `dexpi_add_piping`: "79 types available"
- `dexpi_add_instrumentation`: "34 types available"
- `dexpi_add_valve_between_components`: "22 valve types available"

Check tool descriptions for examples and guidance.

### 4. Validate Equipment Types

If unsure whether a type exists, check the [EQUIPMENT_CATALOG.md](./EQUIPMENT_CATALOG.md) or let the tool validate:

```python
# Tool will return helpful error if type doesn't exist:
dexpi_add_equipment(equipment_type="invalid_type", ...)
# → Error: "Invalid equipment type 'invalid_type'. Use ComponentRegistry to see available types."
```

---

## Frequently Asked Questions

### Q: Do I need to update my existing code?

**A: No** - All existing code continues to work. Phase 2 only adds new capabilities.

### Q: Can I mix SFILES aliases and DEXPI class names in the same model?

**A: Yes** - They're completely interchangeable:

```python
dexpi_add_equipment(equipment_type="pump", tag_name="P-001")           # Alias
dexpi_add_equipment(equipment_type="CentrifugalPump", tag_name="P-002")  # Class name
# Both create CentrifugalPump instances
```

### Q: How do I know which class name corresponds to which alias?

**A: See [EQUIPMENT_CATALOG.md](./EQUIPMENT_CATALOG.md)** - Every entry shows both:

```
- `pump` / `CentrifugalPump` - Centrifugal pump
- `boiler` / `Boiler` - Boiler
- `heat_exchanger_plate` / `PlateHeatExchanger` - Plate heat exchanger
```

### Q: What if I specify a piping_type that doesn't exist?

**A: Tool validation** - The tool will return an error with guidance:

```python
dexpi_add_piping(piping_type="invalid_type", ...)
# → Error: "Invalid piping type 'invalid_type'. Use ComponentRegistry to see available types."
```

### Q: Are there performance implications with 5x more equipment types?

**A: No** - Component lookup is O(1) using hash maps. Performance is identical whether you use 30 types or 159 types.

### Q: Can I still use the old DexpiIntrospector?

**A: Not recommended** - It's been replaced by ComponentRegistry which is:
- More complete (272 vs ~50 classes)
- More accurate (CSV-driven, not introspection-based)
- Faster (cached lookups)
- Better tested (34 tests)

---

## Troubleshooting

### Issue: "Equipment type not found"

**Problem**: Type name misspelled or doesn't exist

**Solution**: Check [EQUIPMENT_CATALOG.md](./EQUIPMENT_CATALOG.md) for correct spelling

```python
# Wrong:
dexpi_add_equipment(equipment_type="pumps", ...)  # ❌ Plural

# Correct:
dexpi_add_equipment(equipment_type="pump", ...)   # ✅ Singular
```

### Issue: "Schema validation error"

**Problem**: Before Phase 2.2 Codex fixes, class names were rejected

**Solution**: Update to latest version (Phase 2.2 with Codex fixes)

```bash
git pull origin master
# Ensure you have commit 6c10fc0 or later
```

### Issue: "ProcessInstrumentationFunction instead of Transmitter"

**Problem**: Before Phase 2.2 Codex fixes, instrumentation didn't use ComponentRegistry

**Solution**: Update to latest version (Phase 2.2 with Codex fixes)

The fix ensures all 34 instrumentation types create the correct specific classes.

---

## Next Steps

1. **Explore the catalog**: Review [EQUIPMENT_CATALOG.md](./EQUIPMENT_CATALOG.md) to see all available types
2. **Try new equipment**: Start using the 129 newly-available equipment types
3. **Use class names**: Try using DEXPI class names for better documentation
4. **Specify piping types**: Use the new `piping_type` parameter for inline components
5. **Check examples**: See [MCP_TOOL_EXAMPLES.md](./MCP_TOOL_EXAMPLES.md) for complete usage examples

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| Phase 2.2 + Codex Fixes | Nov 11, 2025 | Complete coverage (272 classes), dual naming support |
| Phase 2.1 | Nov 11, 2025 | ComponentRegistry backend |
| Phase 1 | Nov 10, 2025 | Legacy registry (~30 equipment types) |

---

**Last Updated**: November 11, 2025
**Phase**: 2.2 Complete (with Codex fixes)
**Backward Compatibility**: 100% - No breaking changes
