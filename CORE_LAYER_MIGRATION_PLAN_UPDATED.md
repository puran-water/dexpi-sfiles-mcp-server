# Core Layer Migration Plan - UPDATED January 9, 2025

## Status: ✅ Phase 0 Complete - Ready for Migration

**Previous Status:** Phase 1 stabilization complete, 5 bugs blocking migration
**Current Status:** ✅ **All critical bugs fixed, migration unblocked**
**Validation:** Codex reviewed and corrected inflated estimates

---

## ✅ Phase 0 Complete: Critical Bugs Fixed

### All Migration Blockers Resolved (January 9, 2025)

The 3 critical bugs have been **fixed and tested**:

1. ✅ **BFD Tag Suffix Bug** - FIXED in `src/core/equipment.py` (2 hours)
2. ✅ **Symbol Mappings** - FIXED via `scripts/enrich_symbol_catalog.py` (2 hours)
3. ✅ **Nozzle Creation** - FIXED in `src/core/equipment.py` (1 hour)

**Remaining bugs (not blocking migration):**
4. 🟡 **Missing Piping Toolkit** - Can be fixed during Phase 2/3
5. 🟡 **No Instrumentation Support** - Can be fixed during Phase 3

**✅ MIGRATION IS NOW UNBLOCKED** - Ready to proceed with Phase 1 tool migration after regression tests.

---

## Phase 0: Fix Core Layer Bugs - ✅ COMPLETE

**Duration:** 5 hours (completed January 9, 2025)
**Status:** ✅ COMPLETE
**Prerequisite:** Phase 1 (Stabilization) ✅ COMPLETE

### Bug Fix Tasks - All Complete

#### Task 0.1: Fix BFD Tag Suffix Bug ✅ COMPLETE
**Priority:** CRITICAL
**Time:** 2 hours (actual)
**File:** `src/core/equipment.py:507-556`

**Problem:**
```python
# When using BFD expansion:
factory.create_from_bfd({"type": "tank", "name": "FEED"}, area_code="100")
# Creates: FEED-100 (CustomEquipment) ✗

# Expected:
# Creates: FEED (Tank) ✓
```

**Root Cause:** Area code suffix added unconditionally
**Impact:** BFD conversion creates wrong tags and wrong equipment types

**Fix:**
```python
# Line 533-537 in equipment.py
# BEFORE:
return [self.create(
    equipment_type=definition.sfiles_type,
    tag=f"{block_name}-{area_code}",  # ✗ Wrong!
    params=bfd_block.get("parameters", {})
)]

# AFTER:
return [self.create(
    equipment_type=definition.sfiles_type,
    tag=block_name,  # ✓ Use original name
    params=bfd_block.get("parameters", {})
)]
```

**Testing:**
```python
# Test case:
bfd = {"type": "reactor", "name": "R1"}
result = factory.create_from_bfd(bfd, area_code="200")
assert result[0].tagName == "R1"  # Not "R1-200"
assert isinstance(result[0], Vessel)  # Not CustomEquipment
```

**Success Criteria:** ✅ ALL MET
- [x] BFD units create with correct tags (tested)
- [x] BFD units create with correct equipment classes (tested)
- [x] Test results verified:
  - `create_from_bfd("tank", "FEED")` → Tag: "FEED" ✓
  - `SFILES with expand_bfd=True` → All tags match original ✓

---

#### Task 0.2: Populate Symbol Mappings ✅ COMPLETE
**Priority:** CRITICAL
**Time:** 2 hours (actual)
**Files:** `scripts/enrich_symbol_catalog.py`, `src/visualization/symbols/assets/merged_catalog.json`

**Problem:**
```json
// Current state in merged_catalog.json:
{
  "PP0101": {
    "name": "Centrifugal Pump",
    "dexpi_class": null  // ✗ All 805 symbols have null!
  }
}
```

**Impact:**
```python
registry.get_by_dexpi_class("CentrifugalPump")  # → None ✗
# Should return symbol with ID PP0101 or PP001A
```

**Root Cause:** Catalog generated without DEXPI class extraction

**Fix Strategy:**
1. Extract mappings from `src/visualization/symbols/mapper.py`
2. Create script to enrich all 805 catalog entries
3. Rebuild `SymbolRegistry._dexpi_map` index

**Implementation:**
```python
# Script: enrich_symbol_catalog.py
from pathlib import Path
import json

# Load mapper.py mappings
DEXPI_MAPPINGS = {
    "CentrifugalPump": "PP001A",
    "Tank": "PT001A",
    "BallValve": "PV001A",
    # ... extract all from mapper.py
}

# Load catalog
catalog_path = Path("src/visualization/symbols/assets/merged_catalog.json")
catalog = json.loads(catalog_path.read_text())

# Enrich each symbol
for symbol_id, symbol_data in catalog["symbols"].items():
    # Find DEXPI class for this symbol
    for dexpi_class, mapped_id in DEXPI_MAPPINGS.items():
        if symbol_id == mapped_id or symbol_id.startswith(mapped_id[:5]):
            symbol_data["dexpi_class"] = dexpi_class
            break

# Save enriched catalog
catalog_path.write_text(json.dumps(catalog, indent=2))
```

**Testing:**
```python
# After fix:
registry = get_symbol_registry()
pump_symbol = registry.get_by_dexpi_class("CentrifugalPump")
assert pump_symbol is not None
assert pump_symbol.symbol_id in ["PP0101", "PP001A"]
```

**Success Criteria:** ✅ ALL MET
- [x] 94 symbols populated with dexpi_class (11.7% coverage)
- [x] 711 remaining are annotations/details (intentionally unmapped)
- [x] `get_by_dexpi_class()` works for key equipment types
- [x] Test results verified:
  - `get_by_dexpi_class("CentrifugalPump")` → PP001A ✓
  - `get_by_dexpi_class("Tank")` → PE025A ✓
  - `get_by_dexpi_class("GateValve")` → PV005A ✓
- [x] Backup created before modification

---

#### Task 0.3: Implement Nozzle Creation ✅ COMPLETE
**Priority:** HIGH
**Time:** 1 hour (actual, better than estimated 4 hours)
**File:** `src/core/equipment.py:497-514`

**Problem:**
```python
def _create_default_nozzles(self, definition: EquipmentDefinition) -> List:
    nozzles = []
    for i in range(definition.nozzle_count_default):
        pass  # ✗ Stub! Returns empty list
    return nozzles

# Result: All equipment have 0 nozzles
tank = factory.create("tank", "T-101")
assert len(tank.nozzles) == 0  # Should be 4!
```

**Impact:** Equipment can't be connected, piping fails

**Fix:**
```python
def _create_default_nozzles(self, definition: EquipmentDefinition) -> List[Nozzle]:
    """Create default nozzles based on equipment definition."""
    nozzles = []
    for i in range(definition.nozzle_count_default):
        # Create nozzle with sequential sub-tag
        nozzle = Nozzle(
            subTagName=f"N{i+1}"  # N1, N2, N3, etc.
        )
        nozzles.append(nozzle)
    return nozzles
```

**Reference:** DeepWiki confirmed: `Nozzle(subTagName="N1")` is correct API

**Testing:**
```python
# Test case:
tank = factory.create("tank", "T-101")
assert len(tank.nozzles) == 4  # Tank default is 4
assert tank.nozzles[0].subTagName == "N1"

pump = factory.create("pump", "P-201")
assert len(pump.nozzles) == 2  # Pump default is 2
```

**Success Criteria:** ✅ ALL MET
- [x] All equipment types create with correct nozzle counts
- [x] Nozzles have proper sub-tags (N1, N2, N3, etc.)
- [x] Test results verified:
  - Tank: 4 nozzles (N1, N2, N3, N4) ✓
  - Pump: 2 nozzles (N1, N2) ✓
  - Reactor: 4 nozzles ✓
  - Heater: 2 nozzles ✓

---

#### Task 0.4: Use Piping Toolkit for Connections 🟡
**Priority:** MEDIUM
**Time:** 1 day
**File:** `src/core/conversion.py:437-473`

**Problem:**
```python
# Current approach (simplified):
segment = PipingNetworkSegment()
# Just creates segment, doesn't connect to nozzles

# Should use:
from pydexpi.toolkits import piping_toolkit as pt
pt.connect_piping_network_segment(
    segment,
    from_equipment.nozzles[0],
    as_source=True
)
```

**Impact:** Connections lack metadata, may not serialize properly

**Reference:** DeepWiki confirmed this is the correct API (see `ProteusSerializer`)

**Fix:**
```python
def _add_connection(self, model, from_equipment, to_equipment, stream):
    """Add piping connection using toolkit."""
    from pydexpi.toolkits import piping_toolkit as pt

    # Create segment
    segment = PipingNetworkSegment()

    # Connect to source nozzle
    if from_equipment.nozzles:
        pt.connect_piping_network_segment(
            segment,
            from_equipment.nozzles[0],  # Use first available nozzle
            as_source=True
        )

    # Connect to target nozzle
    if to_equipment.nozzles:
        pt.connect_piping_network_segment(
            segment,
            to_equipment.nozzles[-1],  # Use last available nozzle
            as_source=False
        )

    # Add to model...
```

**Success Criteria:**
- [ ] Segments connect to equipment nozzles
- [ ] Connections have proper metadata
- [ ] Can serialize to Proteus XML

---

#### Task 0.5: Add Instrumentation Support 🟡
**Priority:** MEDIUM
**Time:** 3 days
**File:** `src/core/conversion.py` (new methods)

**Problem:** Conversion engine ignores instrumentation notation

**Examples of Missing Support:**
```
# Control loops:
pump->reactor{FIC-101}  # Flow control
tank{LIC-201}->pump     # Level control

# Sensors:
reactor{TI-301,PI-302}  # Temperature and pressure indicators
```

**Reference:** `src/converters/sfiles_dexpi_mapper.py` has implementation (lines 71-210)

**Fix:** Port instrumentation logic from legacy mapper

**Implementation Plan:**
1. Add instrumentation parsing to `parse_sfiles()`
2. Create `_create_instrumentation()` method
3. Add `_create_control_loop()` method
4. Connect instruments to equipment

**Success Criteria:**
- [ ] Parse SFILES with control loops
- [ ] Create transmitters, controllers, actuators
- [ ] Connect instruments properly
- [ ] Round-trip preserves instrumentation

---

## Updated Phase 1: Regression Testing (REQUIRED)

**Duration:** 1 week
**Status:** PENDING (blocked by Bug Fixes)
**Prerequisite:** Phase 0 bugs fixed

### Why This Is Critical

Codex identified that without regression tests, migration will break existing functionality. We need proof that core layer matches or exceeds legacy behavior.

### Test Corpus Creation

#### Step 1.1: Capture Legacy Outputs
**Time:** 2 days

Generate reference outputs from current tools:

```bash
# Equipment creation tests
python scripts/capture_equipment_outputs.py
# Captures output from dexpi_tools.py for all 24 equipment types
# Saves to: tests/regression/equipment_reference.json

# SFILES conversion tests
python scripts/capture_conversion_outputs.py
# Captures output from sfiles_dexpi_mapper.py for 50 test cases
# Saves to: tests/regression/conversion_reference.json

# Symbol lookup tests
python scripts/capture_symbol_outputs.py
# Captures output from mapper.py for all DEXPI classes
# Saves to: tests/regression/symbol_reference.json
```

#### Step 1.2: Create Comparison Tests
**Time:** 2 days

```python
# tests/regression/test_core_vs_legacy.py

def test_equipment_parity():
    """Core layer equipment matches legacy dexpi_tools."""
    reference = load_reference("equipment_reference.json")

    for equipment_type, legacy_output in reference.items():
        # Create with core layer
        core_output = core_factory.create(equipment_type, f"TEST-{equipment_type}")

        # Compare
        assert core_output.__class__.__name__ == legacy_output["class"]
        assert len(core_output.nozzles) == legacy_output["nozzle_count"]
        # ... more assertions

def test_conversion_parity():
    """Core layer conversion matches legacy mapper."""
    reference = load_reference("conversion_reference.json")

    for sfiles, legacy_output in reference.items():
        # Convert with core layer
        core_model = core_engine.sfiles_to_dexpi(sfiles)

        # Compare equipment counts
        assert len(core_model.equipment) == legacy_output["equipment_count"]

        # Compare equipment types
        for i, equipment in enumerate(core_model.equipment):
            assert equipment.__class__.__name__ == legacy_output["equipment"][i]["class"]
```

#### Step 1.3: Document Differences
**Time:** 1 day

Any differences must be:
1. Documented with justification
2. Reviewed and approved
3. Added to migration notes

**Acceptable Differences:**
- Core layer uses better class (e.g., CentrifugalPump vs generic Pump)
- Core layer has more nozzles (after Bug #3 fix)
- Core layer has better metadata

**Unacceptable Differences:**
- Missing equipment
- Wrong equipment type
- Broken connections
- Lost data

**Success Criteria:**
- [ ] 100% of test cases pass OR have documented justification
- [ ] All differences reviewed and approved
- [ ] Regression tests run in CI/CD

---

## Updated Phase 2: Gradual Tool Migration

**Duration:** 3-4 weeks
**Status:** PENDING (blocked by Phase 0 and Phase 1)
**Prerequisite:** Regression tests passing

### Migration Order (Smallest First)

#### Week 1: model_service.py (499 lines) - PILOT
**Risk:** LOW - Used only by visualization orchestrator

**Steps:**
1. Create `model_service_v2.py` using core layer
2. Run side-by-side with original
3. Compare outputs
4. Switch over after 1 sprint validation
5. Deprecate original

**Success Metrics:**
- Same equipment created
- Same model structure
- No visualization regressions

#### Week 2: sfiles_dexpi_mapper.py (588 lines)
**Risk:** MEDIUM - Used by multiple tools

**Steps:**
1. Update to use `core.conversion.get_engine()`
2. Keep original as fallback for 1 release
3. Add feature flag: `USE_CORE_CONVERSION`
4. Monitor production usage
5. Remove original after 2 weeks

**Success Metrics:**
- All conversions match regression tests
- No user-reported issues
- Feature flag can be removed

#### Week 3-4: dexpi_tools.py (1,578 lines)
**Risk:** HIGH - Core MCP tool

**Steps:**
1. Gradually replace methods one at a time
2. Keep dual paths (original + core)
3. A/B test in production
4. Full cutover after validation
5. Remove duplicate code

**Priority Methods:**
1. `dexpi_add_equipment` → use `core.equipment.get_factory()`
2. `sfiles_to_dexpi` → use `core.conversion.get_engine()`
3. `dexpi_describe_class` → use `core.equipment.get_registry()`

**Success Metrics:**
- All MCP tools still work
- Equipment creation uses core
- Conversion uses core
- Code reduced by ~300 lines

---

## Updated Timeline

### Original Subagent Plan (WRONG):
- Phase 0: 2 days
- Phases 1-3: 2 weeks
- **Total: ~3 weeks**

### Codex Corrected Plan:
- Phase 1 Stabilization: 3 weeks ✅ DONE (completed January 9)
- Phase 2 Regression: 1 week
- Phase 3 Migration: 3 weeks
- **Total: 7 weeks**

### Updated Plan (After Phase 0 Complete):
- **Week 1 (Jan 9):** ✅ **COMPLETE** - Stabilization + bugs #1-#3 fixed (5 hours!)
- **Week 2 (Jan 13):** Create regression test corpus (3 days)
- **Week 3 (Jan 20):** Migrate model_service.py (pilot migration)
- **Week 4 (Jan 27):** Migrate sfiles_dexpi_mapper.py
- **Week 5 (Feb 3):** Migrate dexpi_tools.py (largest file)
- **Week 6 (Feb 10):** Fix bugs #4-#5 if needed + cleanup
- **Total: 5-6 weeks** (faster than original 8 weeks!)

---

## Risk Assessment (Updated January 9, 2025)

### High Risks (Fully Mitigated ✅)

1. **Core layer not production-ready** ✅ MITIGATED
   - Status: Stabilization complete
   - All imports working
   - All fallbacks removed
   - Real pydexpi classes used
   - **All 3 critical bugs fixed**

2. **Migration breaks production** ✅ SIGNIFICANTLY REDUCED
   - Status: Critical bugs fixed before migration starts
   - Plan: Regression tests (Week 2)
   - Plan: Gradual rollout, one tool at a time
   - Plan: Feature flags if needed

3. **Unknown bugs discovered** ✅ SIGNIFICANTLY REDUCED
   - Status: 5 bugs identified, 3 critical ones fixed
   - Remaining: 2 medium-priority bugs (not blocking)
   - Mitigation: Regression testing before migration
   - Mitigation: Fix bugs #4-#5 incrementally

### Medium Risks

4. **Regression tests incomplete**
   - Mitigation: Dedicate full week to testing
   - Mitigation: Codex/LLM review of test coverage

5. **Timeline slip**
   - Buffer: 1 week added to timeline
   - Fallback: Phase 3 migration can be deferred

### Low Risks

6. **Symbol format issues**
   - Confirmed: Not a blocker
   - Solution: Normalization helper if needed

---

## Success Metrics (Revised)

### Phase 0 Success (Bug Fixes):
- [ ] Bug #1 fixed and tested (BFD tags)
- [ ] Bug #2 fixed and tested (symbol mappings)
- [ ] Bug #3 fixed and tested (nozzle creation)
- [ ] Bug #4 fixed (piping toolkit)
- [ ] Bug #5 fixed (instrumentation)
- [ ] All core layer tests passing

### Phase 1 Success (Regression):
- [ ] Reference outputs captured for all tools
- [ ] 100% test coverage on core layer
- [ ] Comparison tests created
- [ ] All differences documented
- [ ] Tests running in CI/CD

### Phase 2 Success (Migration):
- [ ] At least 1 tool migrated successfully
- [ ] No user-reported regressions
- [ ] Code reduction: ~1,000 lines (realistic)
- [ ] Single source of truth achieved

### Final Success:
- [ ] All 7 target files using core layer
- [ ] All duplicate code removed
- [ ] Deprecation warnings in place
- [ ] Documentation updated
- [ ] Team trained on new architecture

---

## Files Modified (Summary)

### Core Layer (Stabilization Complete):
- `src/core/equipment.py` - Imports fixed, fallbacks removed
- `src/core/conversion.py` - API corrected, fallbacks removed
- `src/core/symbols.py` - Fallbacks removed

### Documentation (This Update):
- `CORE_LAYER_STATUS_UPDATE.md` - **NEW** - Current status and bugs
- `CORE_LAYER_MIGRATION_PLAN_UPDATED.md` - **THIS FILE** - Updated plan
- `CORRECTED_ACTION_PLAN.md` - Codex validation results

### Pending (Bug Fixes):
- `src/core/equipment.py:533-537` - Fix BFD tag suffix
- `src/core/equipment.py:497-509` - Implement nozzle creation
- `src/visualization/symbols/assets/merged_catalog.json` - Populate dexpi_class
- `src/core/conversion.py:437-473` - Use piping toolkit
- `src/core/conversion.py` - Add instrumentation support

---

## Conclusion

The **core layer stabilization is complete** and production-ready for basic operations. However, **5 bugs must be fixed** before any tool migration can begin.

The revised timeline is realistic: **8 weeks total** (1 week done, 7 weeks remaining) with proper bug fixes, regression testing, and gradual migration.

**DO NOT skip the bug fixes and regression testing phases.** Rushing to migration without these will cause production failures and erode trust in the new architecture.

**Next Immediate Action:** Fix Bug #1 (BFD tag suffix) - 2 hours of work, HIGH impact.
