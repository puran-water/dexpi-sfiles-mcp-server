# Phase 1 Migration - Mapper Consumers

This document lists all files that consume `SfilesDexpiMapper` and need migration to the core layer.

## Migration Strategy

**User Decision**: No backward compatibility needed - direct replacement.

- ❌ No feature flags
- ❌ No dual code paths
- ✅ Direct replacement with core layer
- ✅ Cleaner, simpler migration

## Consumers Identified

### 1. src/converters/sfiles_dexpi_mapper.py
**Status**: THE MAPPER (to be replaced with thin wrapper)
- Line 31: Class definition
- **Action**: Delete internals, replace with deprecated wrapper calling `get_engine()`

### 2. src/tools/dexpi_tools.py
**Status**: ⏳ TO MIGRATE (Day 1)
- Line 1544: Import statement
- Line 1569: `mapper = SfilesDexpiMapper()`
- **Usage**: SFILES → DEXPI conversion for MCP tool
- **Action**: Replace with `engine = get_engine(); engine.sfiles_to_dexpi()`

### 3. src/tools/validation_tools.py
**Status**: ⏳ TO MIGRATE (Day 2)
- Line 16: Import statement
- Line 35: `self.mapper = SfilesDexpiMapper()`
- **Usage**: Round-trip validation (SFILES ↔ DEXPI)
- **Action**: Replace with `self.engine = get_engine()`

### 4. src/tools/sfiles_tools.py
**Status**: ⏳ TO MIGRATE (Day 2)
- Line 1057: Import statement
- Line 1078: `mapper = SfilesDexpiMapper()`
- **Usage**: DEXPI → SFILES conversion
- **Action**: Replace with `engine = get_engine(); engine.dexpi_to_sfiles()`
- **Note**: Handle `flowsheet.convert_to_sfiles()` API mismatch

### 5. examples/
**Status**: ✅ CLEAN
- No mapper usage found
- No action needed

## Migration Order

**Day 1 (Prep)**:
1. Freeze legacy behavior → `tests/fixtures/legacy_equipment.py`
2. Capture baseline → `tests/fixtures/baseline/*.json`
3. Create comparison tests → `tests/test_migration_equivalence.py`

**Day 2 (Core Migration)**:
1. Migrate `dexpi_tools.py` equipment creation (lines 370-461)
2. Migrate `dexpi_tools.py` SFILES conversion (line 1569)
3. Write 8 integration tests
4. Run full test suite

**Day 3 (Consumers + Cleanup)**:
1. Migrate `validation_tools.py` (line 35)
2. Migrate `sfiles_tools.py` (line 1078)
3. Check `model_service.py` for internal patterns
4. Delete mapper internals, create wrapper
5. Write 12 consumer tests
6. Final validation

## Success Criteria

- ✅ All 4 consumers migrated (dexpi_tools, validation_tools, sfiles_tools, model_service)
- ✅ 28 integration tests passing
- ✅ ~350 lines net reduction
- ✅ Equipment support: 9 → 30+ types
- ✅ No mapper usage except deprecated wrapper

## Verification Commands

```bash
# Check for remaining mapper imports (should only be in wrapper)
grep -r "SfilesDexpiMapper" src/ --include="*.py" | grep -v "sfiles_dexpi_mapper.py"

# Count lines saved
git diff --stat master..phase1-complete

# Run test suite
pytest tests/test_migration_equivalence.py -v
pytest tests/ -v
```

## Rollback

No feature flags needed - rollback via git:

```bash
# Revert all Phase 1 commits
git revert <commit-range>
```

## Timeline

- **Day 1**: Prep (baseline capture) - 4 hours
- **Day 2**: Core migration (dexpi_tools) - 8 hours
- **Day 3**: Consumers + cleanup - 8 hours

**Total**: 3 days (vs original 5-day plan with feature flags)
