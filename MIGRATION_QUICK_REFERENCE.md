# Core Layer Migration - Quick Reference Card

## 🚨 Critical Blocker

**Symbol ID Format Conflict**: PP0101 vs PP001A vs P-01-01

**Solution**: Standardize on PP001A (NOAKADEXPI format)  
**Why**: 805 symbols in merged_catalog.json use this format  
**When**: Phase 0 (MUST DO FIRST)

---

## 📋 Migration Checklist

### Phase 0: Symbol Format Fix (2 days) ⚠️ BLOCKER
- [ ] Update core/symbols.py defaults to PP001A
- [ ] Update core/equipment.py symbol_ids to PP001A  
- [ ] Create SymbolFormatConverter utility
- [ ] Add backward compatibility tests
- [ ] Validate with merged_catalog.json

### Phase 1: Quick Wins (3 days)
- [ ] Migrate dexpi_tools.py equipment creation (-145 lines)
- [ ] Migrate sfiles_dexpi_mapper.py conversion (-155 lines)
- [ ] Add deprecation warnings to old code

### Phase 2: Medium Impact (4 days)
- [ ] Migrate model_service.py with feature flags (-100 lines)
- [ ] Migrate pfd_expansion_engine.py type mapping (-70 lines)

### Phase 3: Visualization (3 days)
- [ ] Deprecate mapper.py and catalog.py (-746 lines)
- [ ] Update visualization layer to use core
- [ ] Create wrapper compatibility layer

### Phase 4: Cleanup (2 days, optional)
- [ ] Remove deprecated code after 2-week wait
- [ ] Run performance validation
- [ ] Update all documentation

---

## 🎯 Migration Targets

| File | Lines | Migration | Impact |
|------|-------|-----------|--------|
| dexpi_tools.py | 1,578 | Equipment factory | -145 lines |
| sfiles_dexpi_mapper.py | 588 | Conversion engine | -155 lines |
| model_service.py | 499 | Factory + registry | -100 lines |
| pfd_expansion_engine.py | 551 | BFD type mapping | -70 lines |
| mapper.py | 283 | Replace with wrapper | -283 lines |
| catalog.py | 463 | Replace with wrapper | -463 lines |
| **TOTAL** | **3,962** | | **-1,216** ✅ |

---

## 🔧 Migration Patterns

### Before → After Examples

**Equipment Creation**:
```python
# BEFORE (145 lines)
if equipment_type == "CentrifugalPump":
    dexpi_class = CentrifugalPump
    symbol = "PP001A"
elif equipment_type == "Tank":
    dexpi_class = Tank
    symbol = "PT001A"
# ... 30+ more conditions

# AFTER (1 line)
equipment = get_equipment_factory().create(equipment_type, tag, params)
```

**SFILES Conversion**:
```python
# BEFORE (155 lines, 9 types)
TYPE_MAP = {'pump': 'CentrifugalPump', ...}
def parse_sfiles(...): # 80 lines
def convert(...): # 75 lines

# AFTER (1 line, 30+ types)
return get_conversion_engine().sfiles_to_dexpi(sfiles_string)
```

**Symbol Lookup**:
```python
# BEFORE (50 lines, 4 types)
EQUIPMENT_TYPES = {'pump': 'PP001A', ...}
symbol = EQUIPMENT_TYPES.get(eq_type, 'UNKNOWN')

# AFTER (3 lines, 30+ types)
definition = get_equipment_factory().registry.get_by_sfiles_type(eq_type)
symbol = definition.symbol_id if definition else None
```

---

## 🧪 Testing Commands

### Run Core Layer Tests
```bash
# Unit tests
pytest tests/test_core_equipment.py -v
pytest tests/test_core_symbols.py -v
pytest tests/test_core_conversion.py -v

# Full test suite
python test_core_layer.py
```

### Create Regression Baseline
```bash
python tests/create_regression_baseline.py
```

### Validate After Each Phase
```bash
pytest tests/test_regression_baseline.py --baseline=tests/baseline/
```

---

## 🔄 Import Changes

### Old Imports → New Imports

```python
# OLD: Scattered imports
from tools.dexpi_tools import add_equipment
from converters.sfiles_dexpi_mapper import SfilesDexpiMapper
from visualization.symbols.mapper import DexpiSymbolMapper

# NEW: Core layer imports
from core import (
    get_equipment_factory,
    get_equipment_registry,
    get_symbol_registry,
    get_conversion_engine
)
```

---

## 📊 Success Metrics

### Code Quality
- [x] Core layer exists (★★★★★)
- [ ] Single source of truth (0% → 100%)
- [ ] Zero duplicate implementations
- [ ] -1,216 lines removed

### Feature Coverage
- Equipment types: 9 → 30+ (+333%)
- Symbol mappings: 190 → 805 (+423%)
- BFD blocks: 21 → 30 (+43%)

### Performance
- Equipment creation: < 1ms ✅
- Symbol lookup: < 0.1ms ✅
- SFILES conversion: < 10ms (50 units) ✅

---

## 🚦 Risk Levels

| Phase | Risk | Reason |
|-------|------|--------|
| Phase 0 | 🟢 LOW | Isolated to core layer |
| Phase 1 | 🟢 LOW | New code path, old unchanged |
| Phase 2 | 🟡 MEDIUM | Shared code, has feature flags |
| Phase 3 | 🟡 MEDIUM | User-facing, has wrappers |
| Phase 4 | 🟢 LOW | Optional cleanup |

---

## ⚡ Rollback Options

### Emergency Rollback
```bash
git checkout v2.0-pre-migration
git reset --hard
```

### Feature Flag Rollback (No deployment)
```python
# config.py
FEATURE_FLAGS = {
    'use_core_equipment_factory': False,  # ← Flip here
}
```

### Partial Rollback
```bash
git revert <phase-commits>
```

---

## 📅 Timeline

```
Week 1: P0 + P1 (Symbol fix + Quick wins)
Week 2: P2 (Medium impact + feature flags)  
Week 3: P3 (Visualization layer)
Week 4: P4 (Optional cleanup)
```

**Critical Path**: 2-3 weeks  
**Total Duration**: 3-4 weeks (with cleanup)

---

## 🎓 Key Learnings

### What Went Wrong
1. Core layer built but not integrated
2. No migration documentation
3. No deprecation warnings
4. Symbol format not standardized upfront
5. 7% adoption = architecture failure

### What We're Fixing
1. ✅ Phased migration plan
2. ✅ Comprehensive testing strategy
3. ✅ Feature flags for safety
4. ✅ Deprecation warnings
5. ✅ Clear documentation
6. ✅ Rollback options at every step

---

## 📞 Support

**Documentation**:
- Full plan: `CORE_LAYER_MIGRATION_PLAN.md`
- Summary: `MIGRATION_SUMMARY.md`
- Findings: `CORE_LAYER_FINDINGS.txt`

**Files to watch**:
- `src/core/symbols.py` - Symbol registry
- `src/core/equipment.py` - Equipment registry
- `src/core/conversion.py` - SFILES conversion
- `src/tools/dexpi_tools_v2.py` - Reference implementation

---

**Version**: 1.0  
**Status**: READY FOR USE  
**Last Updated**: 2025-11-09
