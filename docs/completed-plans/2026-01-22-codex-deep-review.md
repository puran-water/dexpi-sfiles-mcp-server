# Codex Deep Review: engineering-mcp-server + Skills Architecture

**Status:** COMPLETED
**Completed:** 2026-01-22
**Codex Session ID:** `019be6a3-e2bd-7cc0-a96a-4e901b2d229d`
**Verification Session:** `019be712-4929-7181-82d1-26c4d96c453d`
**Verification Result:** ALL PHASES COMPLETE - VERIFIED

---

This plan summarizes a comprehensive Codex review (gpt-5.2 xhigh, read-only mode) of the engineering-mcp-server codebase, its integration with upstream libraries (pyDEXPI, SFILES2), and companion agent skills.

---

## Implementation Summary

### Phase 1: Core Conversion Fixes (COMPLETED)
1. ✅ Replaced `parse_sfiles()` with SFILES2 `Flowsheet.create_from_sfiles()`
2. ✅ Removed `_connection_metadata` side-table; uses real DEXPI segment endpoints
3. ✅ Fixed `ConceptualModel` reconstruction to preserve all fields via in-place mutation
4. ✅ Created proper piping connections via `piping_toolkit.connect_piping_network_segment()`

### Phase 2: Upstream Integration (COMPLETED)
1. ✅ Implemented DEXPI→SFILES via `MLGraphLoader.dexpi_to_graph` + graph mapping
2. ✅ Standardized validation on `MLGraphLoader` behavior (signature handling for both patterns)
3. ✅ Built instrumentation as proper loops via `instrumentation_toolkit`

### Phase 3: Skills Updates (COMPLETED)
1. ✅ Fixed tool call signatures in bfd-skill, pfd-skill, instrument-io-skill
   - `validate_model(model_id, scopes=[...])` - correct array parameter
   - `search_by_type(model_id, component_type=...)` - correct parameter name
   - `dexpi_import_proteus_xml(directory_path, filename)` - correct parameter names
2. ✅ Added transaction wrapping examples to skill documentation
   - `model_tx_begin(model_id, metadata={...})`
   - `model_tx_apply(transaction_id, operations=[{operation, params}])`
3. ✅ Created "DEXPI → schedules" skill at `/home/hvksh/skills/dexpi-schedules-skill/`

---

## 1. Major Implementation Flaws (RESOLVED)

### HIGH Severity (All Fixed)

| Issue | Location | Root Cause | Fix Applied |
|-------|----------|------------|-------------|
| **SFILES parsing incompatible with SFILES2** | `src/core/conversion.py:187-253` | Custom regex parser instead of SFILES2 APIs | Uses `Flowsheet.create_from_sfiles()` with legacy fallback |
| **DEXPI→SFILES produces empty streams** | `src/core/conversion.py:183,557,742` | Uses `_connection_metadata` dict | Removed side-table; uses MLGraphLoader + real segment endpoints |
| **ConceptualModel fields dropped** | `src/core/conversion.py:684,719` | Repeatedly reconstructs ConceptualModel | Uses in-place mutation to preserve all fields |
| **Empty piping connections** | `src/core/conversion.py:737`, `src/tools/dexpi_tools.py:882` | `PipingNetworkSegment()` without endpoints | Uses `piping_toolkit.connect_piping_network_segment()` with nozzles |
| **SFILES2→DEXPI regex mismatch** | `src/tools/dexpi_tools.py:1702`, `src/tools/validation_tools.py:252,289` | SFILES2 strings to non-SFILES2 parser | ConversionEngine accepts `Flowsheet` or `nx.DiGraph` natively |

### MEDIUM Severity (All Fixed)

| Issue | Location | Fix Applied |
|-------|----------|-------------|
| `MLGraphLoader.validate_graph_format` signature inconsistency | `src/tools/dexpi_tools.py:957`, `src/managers/transaction_manager.py:741` | Standardized: `dexpi_to_graph(model)` then `validate_graph_format()` with signature handling |
| `_add_piping` doesn't connect to nozzles | `src/tools/dexpi_tools.py:538,879` | Uses `piping_toolkit` with proper nozzle connections |
| `_add_instrumentation` ignores equipment links | `src/tools/dexpi_tools.py:640,716` | Uses `instrumentation_toolkit` for control loops |
| Graph conversion swallows exceptions | `src/converters/graph_converter.py:39` | Propagates structured errors |

---

## 2. High-ROI Upstream Integration Opportunities (IMPLEMENTED)

### HIGH Impact (Implemented)

1. **SFILES2 sole parser/canonicalizer** - `Flowsheet.create_from_sfiles()` + `convert_to_sfiles()` now used
2. **Real DEXPI piping connections** - `piping_toolkit.connect_piping_network_segment()` with nozzles
3. **DEXPI→SFILES via graph conversion** - `MLGraphLoader.dexpi_to_graph` + graph mapping

### MEDIUM Impact (Implemented)

4. **Standardized DEXPI validation** - MLGraphLoader pattern with signature handling
5. **Instrumentation via toolkit** - `instrumentation_toolkit` for schema-valid control loops
6. **Heat-integration robustness** - Guards on edge-collisions

---

## 3. Skills Architecture (UPDATED)

### Fixed Tool Signatures

All skills now use correct MCP tool signatures:
- `validate_model(model_id, scopes=["topology"])` - array parameter
- `search_by_type(model_id, component_type="...")` - correct parameter name
- `dexpi_import_proteus_xml(directory_path, filename)` - correct parameter names

### Transaction Examples

Skills include correct transaction API usage:
```python
tx_result = model_tx_begin(model_id=fid, metadata={"description": "..."})
tx_id = tx_result["transaction_id"]

model_tx_apply(transaction_id=tx_id, operations=[
    {"operation": "sfiles_add_unit", "params": {"flowsheet_id": fid, "unit_type": "..."}},
    ...
])

model_tx_commit(transaction_id=tx_id)
```

### New Skills Created

1. **dexpi-schedules-skill** - Extracts equipment-list.yaml, instrument-database.yaml, line-list.yaml, valve-schedule.yaml from DEXPI models

---

## Files Modified

### Core Implementation
- `src/core/conversion.py` - SFILES2 native parsing, ConceptualModel preservation, piping connections
- `src/tools/graph_modify_tools.py` - MLGraphLoader validation standardization
- `src/tools/dexpi_tools.py` - Instrumentation toolkit integration
- `tests/visualization/test_orchestrator_integration.py` - Import path fixes

### Skills
- `/home/hvksh/skills/bfd-skill/SKILL.md` - Correct signatures, transaction examples
- `/home/hvksh/skills/pfd-skill/SKILL.md` - Correct signatures, transaction examples
- `/home/hvksh/skills/instrument-io-skill/SKILL.md` - Correct signatures
- `/home/hvksh/skills/dexpi-schedules-skill/` - New skill (SKILL.md, references/, scripts/)
