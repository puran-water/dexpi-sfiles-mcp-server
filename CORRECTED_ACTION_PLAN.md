# Corrected Action Plan - Core Layer Stabilization

## Executive Summary

**Codex Review Findings**: The subagent audit reports significantly overstated the problem (claimed 140K duplicate lines, actual: ~5K) and missed critical issues with the core layer itself. The core layer is architecturally sound but **NOT production-ready**.

### Key Corrections

| Metric | Subagent Claim | Actual Reality | Delta |
|--------|---------------|----------------|-------|
| Duplicate lines | 140,000+ | ~5,100 | **-96%** |
| dexpi_tools.py size | 71,023 lines | 1,578 lines | **-98%** |
| Code reduction potential | 80% (140K→20K) | ~20% (5K→4K) | **Off by 4x** |
| Critical blockers | Symbol format conflict | pyDEXPI imports, null mappings, stubs | Wrong issue |

## Real Blockers Identified by Codex

### 🔴 Blocker 1: Broken pyDEXPI Imports
**Location**: `src/core/equipment.py:18-65`
**Issue**: Tries to import `pyDEXPI` (doesn't exist), falls back to dummy classes
**Impact**: Factory creates generic Equipment objects with no nozzles
**Fix**: Change to `PyDEXPI` (capital P)

### 🔴 Blocker 2: Null Symbol Mappings
**Location**: `src/visualization/symbols/assets/merged_catalog.json`
**Issue**: All 805 symbols have `dexpi_class: null`
**Impact**: `SymbolRegistry.get_by_dexpi_class()` always returns None
**Fix**: Populate DEXPI class mappings from mapper.py

### 🔴 Blocker 3: Stub Implementations
**Locations**:
- Nozzle creation: `src/core/equipment.py:512-520`
- Instrumentation: `src/core/conversion.py` missing control loops
**Impact**: Core layer has less functionality than legacy code
**Fix**: Implement missing features

### 🔴 Blocker 4: Conversion Engine Incomplete
**Location**: `src/core/conversion.py:103-205`
**Issue**: Simple regex parsing, missing NetworkX-based logic from SfilesDexpiMapper
**Impact**: Round-trip tests already show mismatches
**Fix**: Port instrumentation/piping richness from legacy converters

## Corrected Priorities

### Phase 1: Stabilize Core Layer (2-3 weeks)
**Goal**: Make core layer actually production-ready

#### Week 1: Fix Fundamentals
- [ ] Fix pyDEXPI import casing (`pyDEXPI` → `PyDEXPI`)
- [ ] Verify real pyDEXPI classes instantiate correctly
- [ ] Implement nozzle creation (not stubs)
- [ ] Add unit tests for equipment factory

#### Week 2: Populate Symbol Mappings
- [ ] Extract DEXPI class mappings from `mapper.py`
- [ ] Enrich `merged_catalog.json` with `dexpi_class` data
- [ ] Rebuild `SymbolRegistry._dexpi_map` index
- [ ] Verify `get_by_dexpi_class()` works for all equipment types

#### Week 3: Complete Conversion Engine
- [ ] Port instrumentation logic from `SfilesDexpiMapper`
- [ ] Add control loop handling
- [ ] Implement piping attributes
- [ ] Create regression test corpus (compare core vs legacy outputs)
- [ ] Fix round-trip mismatches identified in tests

### Phase 2: Regression Testing (1 week)
**Goal**: Prove core layer matches or exceeds legacy behavior

- [ ] Generate test corpus from existing tools:
  - dexpi_tools.py equipment creation
  - sfiles_dexpi_mapper.py conversion
  - pfd_expansion_engine.py expansion
- [ ] Side-by-side comparison tests
- [ ] Document any behavioral differences
- [ ] Fix or justify any regressions

### Phase 3: Gradual Adoption (2-3 weeks)
**Goal**: Migrate one tool at a time with feature flags

#### Pilot: dexpi_tools_v2.py
- [ ] Wire into MCP server registration
- [ ] Add feature flag for A/B testing
- [ ] Monitor production usage
- [ ] Fix any issues found

#### Second: model_service.py
- [ ] Smallest migration target (499 lines)
- [ ] Replace inline factories with `get_equipment_factory()`
- [ ] Keep legacy fallback for 1 sprint
- [ ] Validate visualization still works

#### Third: sfiles_dexpi_mapper.py
- [ ] Replace with `get_conversion_engine()`
- [ ] Regression test all conversions
- [ ] Deprecate but keep for 1 release

### Phase 4: Cleanup (1 week)
**Goal**: Remove duplicates after core is proven

- [ ] Delete duplicate equipment type maps
- [ ] Consolidate symbol lookups
- [ ] Add deprecation warnings
- [ ] Update documentation

## Symbol Format Resolution

**Codex Recommendation**: NOT a blocker
- Keep PP001A format (what's in merged_catalog.json)
- Add alias layer to normalize PP0101 and P-01-01
- Don't force format changes across all files

```python
# Add to SymbolRegistry
def normalize_symbol_id(self, symbol_id: str) -> str:
    """Normalize various formats to canonical PP001A style."""
    # PP0101 → PP001A
    # P-01-01 → PP001A
    # etc.
```

## Realistic Timeline

| Phase | Duration | Parallel Work Possible? |
|-------|----------|------------------------|
| Phase 1: Stabilize Core | 3 weeks | No - foundation must be solid |
| Phase 2: Regression Tests | 1 week | Can start during Phase 1 Week 3 |
| Phase 3: Gradual Adoption | 3 weeks | One tool at a time |
| Phase 4: Cleanup | 1 week | Low priority, can defer |
| **Total Critical Path** | **6-7 weeks** | Single developer |

## Success Metrics (Revised)

### Phase 1 Success
- [ ] All equipment types create real pyDEXPI instances (not Equipment)
- [ ] All equipment have proper nozzles
- [ ] `SymbolRegistry.get_by_dexpi_class()` returns results for 30+ types
- [ ] Conversion engine passes round-trip tests
- [ ] No warnings in test_core_layer.py output

### Phase 2 Success
- [ ] 100% of test corpus conversions match legacy behavior
- [ ] OR: All differences documented and justified
- [ ] Regression test suite runs in CI

### Phase 3 Success
- [ ] At least 1 production tool using core layer
- [ ] No user-reported regressions
- [ ] Code reduction: ~1,000-1,500 lines (realistic, not 140K)

### Phase 4 Success
- [ ] All duplicate maps removed
- [ ] Documentation updated
- [ ] Deprecation warnings in place

## Risk Mitigation

### Risk: Core layer still has bugs after Phase 1
**Mitigation**: Don't proceed to Phase 3 until Phase 2 regression tests pass

### Risk: Migration breaks production tools
**Mitigation**: Feature flags, gradual rollout, keep legacy code for 1 release

### Risk: Single developer bandwidth
**Mitigation**: Focus on Phase 1 first, defer Phase 4 indefinitely if needed

## What Changed from Subagent Plan

| Aspect | Subagent Plan | Corrected Plan |
|--------|--------------|----------------|
| Starting point | Assume core is ready | Fix core layer first |
| Timeline | 2 weeks | 6-7 weeks |
| First priority | Symbol format | pyDEXPI imports |
| Code reduction | 80% (140K→20K) | 20% (5K→4K) |
| Migration strategy | Big-bang phases | Gradual with feature flags |
| Testing | Added after migration | Required before migration |

## Immediate Next Steps

1. **This Sprint**: Fix pyDEXPI imports and test equipment creation
2. **Next Sprint**: Populate symbol mappings from mapper.py
3. **Third Sprint**: Complete conversion engine parity
4. **Then**: Start regression testing

## Files to Fix (Priority Order)

1. `src/core/equipment.py` (lines 18-65, 512-520) - Import fixes, nozzle creation
2. `src/visualization/symbols/assets/merged_catalog.json` - Add dexpi_class data
3. `src/core/symbols.py` (lines 79-138, 222-239) - Rebuild mappings after catalog fix
4. `src/core/conversion.py` (lines 103-205) - Add instrumentation/control logic
5. `test_core_layer.py` - Update to catch regressions

## Conclusion

The core layer architecture is solid, but implementation is incomplete. The real work is:
1. **Finishing the core layer** (not migrating to it)
2. **Proving it works** (regression tests)
3. **Gradual adoption** (not big-bang)

**Estimated effort**: 6-7 weeks critical path for single developer, focusing on quality over speed.

The subagent reports were well-intentioned but overstated the problem by 2 orders of magnitude and missed the real blockers. This corrected plan is based on Codex's line-by-line code review.