# Current Task: Phase 2.2 - Update MCP Tools for All 272 Classes

**Week:** Phase 5 Week 2b (Nov 11, 2025)
**Priority:** HIGH
**Impact:** Expose all 272 pyDEXPI classes to Claude AI users
**Status:** APPROVED TO PROCEED (Codex review complete)

## Background

**Phase 1 (COMPLETE)**: Auto-generated registrations for ALL 272 pyDEXPI classes
- Equipment: 159/159 classes ✅
- Piping: 79/79 classes ✅
- Instrumentation: 34/34 classes ✅
- 27 families with 1:Many mappings
- Duration: <2 hours

**Phase 2.1 (COMPLETE)**: Core Layer Integration
- Created `src/core/components.py` with unified ComponentRegistry (519 lines)
- All 272 classes imported and registered
- Integrated with EquipmentFactory for backward compatibility
- **CODEX REVIEW COMPLETE**: All 5 critical issues fixed
  - CSV packaging fixed (moved to src/core/data/)
  - Import paths corrected (relative imports)
  - DEXPI class name support added
  - Category metadata preserved
  - Fail-fast CSV loading
- Test coverage: 22 unit tests + 10 integration tests (32/32 passing)
- Duration: ~4 hours (including Codex review fixes)

## Current Task: Phase 2.2 - MCP Tool Schema Updates

### Objective
Update MCP tool schemas to expose all 272 classes to Claude AI users via the engineering-mcp-server interface.

### Scope
Update 4 MCP tool schemas:
1. `dexpi_add_equipment` - expose all 159 equipment types
2. `dexpi_add_valve` - expose all 22 valve types
3. `dexpi_add_piping` - expose all 79 piping types (or create new tool)
4. `dexpi_add_instrumentation` - expose all 34 instrumentation types

### Implementation Plan

#### Step 1: Update Equipment Tool (30-45 min)
**File**: `src/tools/dexpi_tools.py` (method at line ~370)

**Changes**:
- Use `ComponentRegistry.list_all_aliases(ComponentType.EQUIPMENT)` to build enum dynamically
- Update tool schema description with examples
- Include both SFILES aliases and DEXPI class names in documentation
- Test with sample equipment types (pump, boiler, conveyor, crusher)

**Example schema update**:
```python
from src.core.components import get_registry, ComponentType

# In tool schema definition:
equipment_registry = get_registry()
equipment_types = equipment_registry.list_all_aliases(ComponentType.EQUIPMENT)

# Schema parameter:
{
    "name": "equipment_type",
    "description": "Equipment type (SFILES alias or DEXPI class name). "
                  "Examples: 'pump' (CentrifugalPump), 'boiler' (Boiler), "
                  "'conveyor' (Conveyor), 'steam_generator' (SteamGenerator). "
                  f"Available: {', '.join(sorted(equipment_types)[:20])}...",
    "type": "string",
    "enum": sorted(equipment_types)
}
```

#### Step 2: Update Valve Tool (30-45 min)
**File**: `src/tools/dexpi_tools.py` (method at line ~995)

**Changes**:
- Filter piping components by `category == ComponentCategory.VALVE`
- OR use family-based filtering for valve families
- Update examples (ball_valve, butterfly_valve, safety_valve, needle_valve)

**Example**:
```python
from src.core.components import ComponentCategory

valve_components = equipment_registry.get_all_by_category(ComponentCategory.VALVE)
valve_types = [c.sfiles_alias for c in valve_components]
```

#### Step 3: Create/Update Piping Tool (30-45 min)
**File**: `src/tools/dexpi_tools.py` (method at line ~422)

**Changes**:
- Expose all 79 piping types (not just valves)
- Include flow measurement, connections, fittings, etc.
- Update examples (electromagnetic_flow_meter, flange, orifice_plate)

#### Step 4: Update Instrumentation Tool (30-45 min)
**File**: `src/tools/dexpi_tools.py` (method at line ~475)

**Changes**:
- Use `ComponentRegistry.list_all_aliases(ComponentType.INSTRUMENTATION)`
- Update examples (transmitter, positioner, actuator, signal_conveying_function)

#### Step 5: Add Smoke Test (15-30 min)
**File**: `tests/tools/test_dexpi_tool_schemas.py` (new)

**Create test to verify**:
- Equipment tool schema has 159 types
- Valve tool schema has 22 types
- Piping tool schema has 79 types
- Instrumentation tool schema has 34 types

```python
def test_equipment_tool_schema_coverage():
    """Verify dexpi_add_equipment exposes all 159 equipment types."""
    from src.tools.dexpi_tools import DexpiTools
    from src.core.components import get_registry, ComponentType

    tools = DexpiTools({}, {})
    schema = tools.get_tools()  # Get tool schemas

    equipment_tool = next(t for t in schema if t['name'] == 'dexpi_add_equipment')
    enum_values = equipment_tool['inputSchema']['properties']['equipment_type']['enum']

    registry = get_registry()
    expected_count = len(registry.get_all_by_type(ComponentType.EQUIPMENT))

    assert len(enum_values) == expected_count, \
        f"Expected {expected_count} equipment types, got {len(enum_values)}"
```

#### Step 6: Update Tool Documentation (15-30 min)
**Files**:
- Tool docstrings in `src/tools/dexpi_tools.py`
- MCP server tool descriptions

**Add to each tool**:
- Count of available types
- Examples with both aliases and class names
- Link to component registry documentation

### Files to Modify

1. **`src/tools/dexpi_tools.py`** (~200 lines of changes)
   - Update 4 tool method schemas
   - Add dynamic enum generation from ComponentRegistry
   - Update docstrings and examples

2. **`tests/tools/test_dexpi_tool_schemas.py`** (NEW, ~100 lines)
   - Add smoke tests for schema coverage
   - Verify 159/79/34 counts

3. **Tool descriptions** (inline in dexpi_tools.py)
   - Update with current type counts
   - Add usage examples

### Success Criteria

- [x] ComponentRegistry integration complete (Phase 2.1)
- [x] All critical issues fixed (Codex review)
- [x] 22 unit tests + 10 integration tests passing
- [x] `dexpi_add_equipment` schema has 159 equipment types
- [x] `dexpi_add_valve` schema has 22 valve types
- [x] `dexpi_add_piping` schema has 79 piping types
- [x] `dexpi_add_instrumentation` schema has 34 instrumentation types
- [x] Smoke tests verify schema coverage (12 tests passing)
- [x] Tool documentation updated with examples
- [x] All tests passing (46 total: 22 registry + 12 schema + 12 other)

### Testing Strategy

```bash
# 1. Run ComponentRegistry tests
source .venv/bin/activate
python -m pytest tests/core/test_component_registry.py -v

# 2. Run tool schema tests
python -m pytest tests/tools/test_dexpi_tool_schemas.py -v

# 3. Test creating equipment with new types
python -c "
from src.core.equipment import get_factory
factory = get_factory()
boiler = factory.create('boiler', 'B-001')
print(f'Created: {boiler.__class__.__name__}')
"

# 4. Integration tests
python -m pytest tests/visualization/test_orchestrator_integration.py -v
```

### Timeline

- **Estimated effort**: 2-3 hours
- **Priority**: HIGH
- **Dependencies**: Phase 2.1 complete ✅
- **Blockers**: None (Codex approved)

### Codex Recommendations

From Codex review:
> "Proceeding to Phase 2.2 to wire the MCP schemas directly to `ComponentRegistry.list_all_aliases()` is the right next move. Make sure each tool description surfaces both the alias and (when different) the pyDEXPI class name so users understand what to supply."

Additional recommendation:
> "Consider adding a lightweight smoke test that ensures `dexpi_tools.DexpiTools.get_tools()` reflects the 159/79/34 counts once the schemas are dynamic."

### Notes

- **All critical issues fixed**: CSV packaging, imports, class name support, category preservation, fail-fast loading
- **Test coverage**: 32/32 tests passing (22 unit + 10 integration)
- **Codex approval**: Green light to proceed with Phase 2.2
- **Documentation**: Complete with CODEX_REVIEW_FIXES.md

### Next Steps After Phase 2.2

**Phase 2.3**: Comprehensive regression test suite (if needed beyond 22 existing tests)
**Phase 2.4**: Update user-facing documentation
- Equipment catalog
- User migration guide
- MCP tool usage examples
- CHANGELOG update

**Phase 3**: Symbol mapping for placeholders (133 equipment, all piping/instrumentation)
- Can be deferred - doesn't block functionality
- Prioritize high-usage equipment types first

---

## Phase 2.2 COMPLETE ✅

**Completion Date**: November 11, 2025
**Duration**: ~2.5 hours (within estimated 2-3 hours)

### Accomplishments

1. **Updated all 4 MCP tool schemas** (`src/tools/dexpi_tools.py`):
   - `dexpi_add_equipment`: Now exposes 159 equipment types (was ~30)
   - `dexpi_add_valve_between_components`: Now exposes 22 valve types
   - `dexpi_add_piping`: Now exposes 79 piping types (new parameter)
   - `dexpi_add_instrumentation`: Now exposes 34 instrumentation types

2. **Replaced DexpiIntrospector with ComponentRegistry**:
   - All tool schemas now use `ComponentRegistry.list_all_aliases()`
   - Dynamic enum generation from CSV-driven registry
   - Full coverage of all 272 pyDEXPI classes

3. **Enhanced tool descriptions**:
   - Added type counts (159, 79, 34, 22)
   - Included examples with both SFILES aliases and DEXPI class names
   - Updated method docstrings for all 4 tools

4. **Updated piping implementation**:
   - Added `piping_type` parameter to `_add_piping` method
   - Uses ComponentRegistry for component creation
   - Supports all 79 piping types (not just basic Pipe)

5. **Created comprehensive smoke tests** (`tests/tools/test_dexpi_tool_schemas.py`):
   - 12 tests verifying schema coverage
   - Tests for all 4 tool types
   - Validates examples are real component types
   - Ensures enums are sorted and descriptions are accurate

### Test Results

**All tests passing (46 total)**:
- ✅ 22 ComponentRegistry tests (Phase 2.1)
- ✅ 12 Tool schema tests (Phase 2.2)
- ✅ 10 Orchestrator integration tests
- ✅ 2 Other tests

### Files Modified

**Created**:
- `tests/tools/test_dexpi_tool_schemas.py` (313 lines)
- `tests/tools/__init__.py`

**Modified**:
- `src/tools/dexpi_tools.py`:
  - Lines 39-56: Replaced DexpiIntrospector with ComponentRegistry
  - Lines 70-88: Updated equipment tool schema
  - Lines 113-140: Updated piping tool schema (added piping_type)
  - Lines 125-143: Updated instrumentation tool schema
  - Lines 255-270, 279-299, 308-323: Updated valve tool schemas
  - Lines 430-436: Updated `_add_equipment` docstring
  - Lines 482-529: Updated `_add_piping` implementation
  - Lines 562-568: Updated `_add_instrumentation` docstring

### Impact

**Before Phase 2.2**:
- MCP tools exposed limited subset via DexpiIntrospector
- ~30 equipment types, limited valves/instrumentation
- No piping type selection

**After Phase 2.2**:
- ✅ **ALL 272 pyDEXPI classes** now accessible to Claude AI users
- ✅ Both SFILES aliases and DEXPI class names supported
- ✅ Comprehensive documentation with examples
- ✅ Smoke tests prevent regression

---

**Status**: Phase 2.2 COMPLETE ✅ - Ready for Phase 2.3 or Phase 3
**Last Updated**: November 11, 2025
**Approved By**: Codex MCP (Phase 2.2 implementation)
