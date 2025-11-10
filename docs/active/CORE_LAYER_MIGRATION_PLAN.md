# Core Layer Migration Plan
## From Duplication to Single Source of Truth

**Status**: DRAFT v1.0  
**Created**: 2025-11-09  
**Target Completion**: Phase 1-3 (Critical Path): 2 weeks  

---

## Executive Summary

The core layer (`src/core/`) is production-ready but severely underutilized:
- **Current adoption**: 7% (1 of 14 files)
- **Duplicate code**: 140,000+ lines across 7 files
- **Critical blocker**: Symbol ID format conflict (PP0101 vs PP001A vs P-01-01)
- **Risk level**: 🔴 CRITICAL - divergence increasing with every feature addition

This plan provides a phased, risk-minimized migration to achieve true single source of truth.

---

## Critical Blocker Analysis

### Symbol ID Format Conflict

**Problem**: Three incompatible formats in use:
```
core/symbols.py:           PP0101  (4 digits, no letter)
visualization/mapper.py:   PP001A  (3 digits + letter) 
visualization/catalog.py:  P-01-01 (hyphens, 2 digits)
```

**Root Cause**: 
- `merged_catalog.json` contains 805 symbols using PP001A format (NOAKADEXPI standard)
- `core/symbols.py` defaults use PP0101 format (arbitrary choice)
- `catalog.py` uses P-01-01 format (custom)

**Impact**:
- Symbol lookups fail across system boundaries
- Equipment creation gets wrong symbols or no symbols
- Visualization layer cannot find symbol files
- Round-trip conversions lose symbol information

**Resolution Strategy**: See Phase 0 below.

---

## Migration Phases

### Phase 0: Symbol Format Standardization (BLOCKER) 
**Duration**: 2 days  
**Priority**: P0 - Must complete before any other migration  
**Risk**: LOW (isolated change)

#### Decision: Adopt NOAKADEXPI format (PP001A) as standard

**Rationale**:
1. **Data reality**: merged_catalog.json has 805 symbols in PP001A format
2. **File existence**: Symbol SVG files on disk use PP001A naming
3. **Provenance**: Official NOAKADEXPI library uses this format
4. **Coverage**: Most comprehensive symbol library (650 shared + 144 unique)

#### Tasks:

1. **Update `core/symbols.py` defaults** (30 mins)
   ```python
   # Change from:
   ("PP0101", "Centrifugal Pump", SymbolCategory.PUMPS, "CentrifugalPump"),
   # To:
   ("PP001A", "Centrifugal Pump", SymbolCategory.PUMPS, "CentrifugalPump"),
   ```
   - Update all 20+ default mappings
   - Keep category prefixes consistent

2. **Update `core/equipment.py` defaults** (30 mins)
   ```python
   # Change from:
   symbol_id="PP0101"
   # To:
   symbol_id="PP001A"
   ```
   - Update all EquipmentDefinition registrations

3. **Add format converter utility** (2 hours)
   ```python
   # src/core/symbol_formats.py
   class SymbolFormatConverter:
       """Convert between symbol ID formats for backward compatibility."""
       
       @staticmethod
       def normalize_to_standard(symbol_id: str) -> str:
           """Convert any format to PP001A standard."""
           if '-' in symbol_id:  # P-01-01 format
               return convert_hyphen_to_standard(symbol_id)
           elif len(symbol_id) == 6:  # PP0101 format
               return convert_old_to_standard(symbol_id)
           return symbol_id  # Already standard
       
       @staticmethod
       def for_file_lookup(symbol_id: str) -> List[str]:
           """Return all possible file name variants."""
           standard = normalize_to_standard(symbol_id)
           return [
               standard,
               f"{standard}_Detail",
               f"{standard}_Origo",
               convert_to_hyphen_format(standard),
               convert_to_old_format(standard)
           ]
   ```

4. **Update SymbolRegistry to use converter** (1 hour)
   ```python
   def get_symbol(self, symbol_id: str) -> Optional[SymbolInfo]:
       # Try direct lookup first
       symbol = self._symbols.get(symbol_id)
       if symbol:
           return symbol
       
       # Try normalized version
       normalized = SymbolFormatConverter.normalize_to_standard(symbol_id)
       return self._symbols.get(normalized)
   ```

5. **Update tests** (2 hours)
   - `test_core_layer.py`: Update expected symbol IDs
   - Add `test_symbol_format_converter.py`
   - Add backward compatibility tests

6. **Validation** (1 hour)
   ```bash
   # Run core layer tests
   python test_core_layer.py
   
   # Verify merged catalog loads correctly
   python -c "from core import get_symbol_registry; r = get_symbol_registry(); print(r.get_statistics())"
   
   # Check symbol file resolution
   python -c "from core import get_symbol_registry; r = get_symbol_registry(); print(r.get_symbol_path('PP001A'))"
   ```

**Success Criteria**:
- [ ] All core layer defaults use PP001A format
- [ ] Format converter handles all 3 formats
- [ ] Backward compatibility maintained for old format
- [ ] Symbol file paths resolve correctly
- [ ] All tests pass
- [ ] Documentation updated

**Rollback Plan**: Git revert (isolated to core layer)

---

### Phase 1: High-Impact Quick Wins (Week 1)
**Duration**: 3 days  
**Priority**: P1  
**Risk**: LOW (new code path, old code unchanged)

These migrations provide immediate value with minimal risk by creating NEW implementations that use core layer while leaving existing code untouched.

#### 1.1: Migrate `dexpi_tools.py` equipment creation (Day 1)

**Current**: 1,578 lines with embedded type mappings
**Target**: Use `get_equipment_factory()`

**File**: `src/tools/dexpi_tools.py`

**Strategy**: Progressive function replacement

**Migration**:
```python
# OLD (lines 450-520):
def add_equipment(model_id: str, equipment_type: str, tag_name: str, ...):
    # Embedded type mapping
    if equipment_type == "CentrifugalPump":
        dexpi_class = CentrifugalPump
    elif equipment_type == "Tank":
        dexpi_class = Tank
    # ... 30+ more conditions
    
    equipment = dexpi_class(tagName=tag_name, ...)

# NEW:
def add_equipment(model_id: str, equipment_type: str, tag_name: str, ...):
    from core import get_equipment_factory
    factory = get_equipment_factory()
    equipment = factory.create(equipment_type, tag_name, params=specifications)
    # Rest of function unchanged
```

**Functions to migrate**:
1. `add_equipment()` - 70 lines → 10 lines (use factory.create)
2. `_create_equipment_from_type()` - 45 lines → DELETE (use factory.create)
3. `_get_default_nozzle_count()` - 30 lines → DELETE (use definition.nozzle_count_default)

**Testing**:
```bash
# Run existing tests - should pass unchanged
pytest tests/test_dexpi_tools.py -v

# Add new test comparing old vs new
pytest tests/test_dexpi_migration.py::test_equipment_creation_equivalence
```

**Success Criteria**:
- [ ] 3 functions migrated
- [ ] ~145 lines removed
- [ ] All existing tests pass
- [ ] New equivalence tests pass

**Impact**: Removes 145 lines of duplicate type mapping logic

---

#### 1.2: Migrate `sfiles_dexpi_mapper.py` (Day 2)

**Current**: 588 lines with partial SFILES→DEXPI conversion
**Target**: Use `get_conversion_engine()`

**File**: `src/converters/sfiles_dexpi_mapper.py`

**Current implementation** (lines 120-250):
```python
class SfilesDexpiMapper:
    # 9 equipment types hardcoded
    TYPE_MAP = {
        'pump': 'CentrifugalPump',
        'tank': 'Tank',
        # ... only 9 types
    }
    
    def convert(self, sfiles_string: str):
        # Custom parsing (incomplete)
        # Custom type mapping (limited)
        # Custom connection logic
```

**Migration**:
```python
from core import get_conversion_engine

class SfilesDexpiMapper:
    def __init__(self):
        self.engine = get_conversion_engine()
    
    def convert(self, sfiles_string: str):
        # Use core engine - handles 30+ types
        return self.engine.sfiles_to_dexpi(sfiles_string)
```

**Functions to replace**:
1. `parse_sfiles()` - 80 lines → Use `engine.parse_sfiles()`
2. `_map_type()` - 30 lines → DELETE (engine uses registry)
3. `_create_connections()` - 45 lines → Use `engine._add_connection()`
4. `TYPE_MAP` dict - DELETE (use registry)

**Testing**:
```bash
# Compare outputs
pytest tests/test_sfiles_mapper_migration.py::test_conversion_equivalence

# Test round-trip
pytest tests/test_sfiles_mapper_migration.py::test_round_trip_integrity
```

**Success Criteria**:
- [ ] ~155 lines removed
- [ ] Supports 30+ types (vs previous 9)
- [ ] Round-trip tests pass
- [ ] Backward compatibility maintained

**Impact**: 
- Removes 155 lines of duplicate conversion logic
- Adds support for 21 previously unsupported equipment types

---

#### 1.3: Add deprecation warnings (Day 3)

**Purpose**: Guide users toward core layer, prepare for eventual removal of old code

**Files to update**:
1. `src/tools/dexpi_tools.py`
2. `src/tools/sfiles_tools.py`
3. `src/converters/sfiles_dexpi_mapper.py`
4. `src/visualization/symbols/mapper.py`
5. `src/visualization/symbols/catalog.py`

**Implementation**:
```python
# Add to top of each old implementation file
import warnings
from src.utils.deprecation import deprecated

@deprecated(
    version="2.0",
    reason="Use core.get_equipment_factory() instead",
    alternative="from core import get_equipment_factory; factory = get_equipment_factory()",
    removal_version="3.0"
)
def old_function(...):
    warnings.warn(
        "This function uses legacy implementation. Migrate to core layer.",
        DeprecationWarning,
        stacklevel=2
    )
    # existing implementation
```

**Documentation updates**:
1. Add `MIGRATION.md` guide
2. Update `README.md` with migration timeline
3. Add docstring warnings to deprecated functions
4. Update examples to use core layer

**Success Criteria**:
- [ ] All legacy code has deprecation warnings
- [ ] Migration guide published
- [ ] Examples updated
- [ ] Documentation reflects new standard

---

### Phase 2: Medium-Impact Migrations (Week 2)
**Duration**: 4 days  
**Priority**: P2  
**Risk**: MEDIUM (shared code paths)

#### 2.1: Migrate `model_service.py` (Days 4-5)

**Current**: 499 lines with custom equipment creation and symbol lookups
**Target**: Use core layer for all equipment and symbol operations

**File**: `src/visualization/orchestrator/model_service.py`

**Analysis**:
```python
# Current duplication (lines 180-280):
class ModelService:
    # Custom equipment type map (4 types)
    EQUIPMENT_TYPES = {'pump': 'PP001A', ...}
    
    # Custom symbol lookup
    def get_symbol_for_equipment(self, eq_type):
        return self.EQUIPMENT_TYPES.get(eq_type, 'UNKNOWN')
    
    # Custom equipment creation
    def create_equipment(self, type, tag):
        # Hardcoded logic
```

**Migration Strategy**: Incremental replacement with feature flags

```python
from core import get_equipment_factory, get_symbol_registry

class ModelService:
    def __init__(self, use_core_layer: bool = True):
        self.use_core_layer = use_core_layer
        if use_core_layer:
            self.factory = get_equipment_factory()
            self.symbols = get_symbol_registry()
    
    def get_symbol_for_equipment(self, eq_type):
        if self.use_core_layer:
            definition = self.factory.registry.get_by_sfiles_type(eq_type)
            if definition and definition.symbol_id:
                return definition.symbol_id
        # Fallback to old logic
        return self.EQUIPMENT_TYPES.get(eq_type, 'UNKNOWN')
```

**Migration steps**:
1. Add core layer imports
2. Add feature flag `use_core_layer` (default: True)
3. Replace symbol lookups with `symbol_registry.get_by_dexpi_class()`
4. Replace equipment creation with `factory.create()`
5. Add tests with both code paths
6. Once validated, remove feature flag and old code

**Functions to migrate**:
1. `get_symbol_for_equipment()` - Use `get_symbol_registry()`
2. `create_equipment()` - Use `get_equipment_factory()`
3. `parse_model()` - Use `get_conversion_engine()`
4. `EQUIPMENT_TYPES` dict - DELETE

**Testing strategy**:
```python
# Test both code paths
def test_symbol_lookup_equivalence():
    service_old = ModelService(use_core_layer=False)
    service_new = ModelService(use_core_layer=True)
    
    for eq_type in ['pump', 'tank', 'vessel']:
        old_result = service_old.get_symbol_for_equipment(eq_type)
        new_result = service_new.get_symbol_for_equipment(eq_type)
        # After format normalization, should match
        assert normalize_symbol_id(old_result) == normalize_symbol_id(new_result)
```

**Success Criteria**:
- [ ] All equipment operations use core layer
- [ ] Symbol lookups use symbol registry
- [ ] ~100 lines of duplicate code removed
- [ ] Tests pass for both old and new code paths
- [ ] Feature flag can be removed after validation

**Impact**: Removes 100 lines, unifies visualization with rest of system

---

#### 2.2: Migrate `pfd_expansion_engine.py` (Days 6-7)

**Current**: 551 lines with BFD→PFD expansion logic and type mappings
**Target**: Use core layer for equipment creation, keep expansion templates

**File**: `src/tools/pfd_expansion_engine.py`

**Analysis**: This file has TWO responsibilities:
1. **Equipment type mapping** (21 types) - MIGRATE to core
2. **Template expansion logic** (BFD blocks → PFD equipment) - KEEP unique logic

**Migration strategy**: Selective integration

**Keep (unique domain logic)**:
- Template expansion rules (lines 200-450)
- BFD block definitions
- Area code generation
- Sequence numbering

**Migrate (duplicated logic)**:
- Equipment type mapping (lines 80-150) → Use `EquipmentRegistry.get_by_bfd_type()`
- Equipment creation (lines 160-200) → Use `EquipmentFactory.create_from_bfd()`
- Symbol assignment → Use `SymbolRegistry.get_by_dexpi_class()`

**Implementation**:
```python
# OLD (lines 80-150):
BFD_TYPE_MAP = {
    'pumping': 'pump',
    'reaction': 'reactor',
    # ... 21 types
}

def expand_bfd_block(bfd_block):
    sfiles_type = BFD_TYPE_MAP[bfd_block['type']]
    # custom creation logic

# NEW:
from core import get_equipment_factory

def expand_bfd_block(bfd_block):
    factory = get_equipment_factory()
    # Use built-in BFD support
    equipment_list = factory.create_from_bfd(bfd_block)
    # Apply expansion templates (keep existing logic)
    return apply_templates(equipment_list)
```

**Functions to migrate**:
1. `get_equipment_type()` - Use `registry.get_by_bfd_type()`
2. `create_equipment()` - Use `factory.create_from_bfd()`
3. `BFD_TYPE_MAP` - DELETE (use registry)

**Functions to keep**:
1. `apply_expansion_template()` - Unique template logic
2. `generate_area_tags()` - Unique tagging logic
3. `EXPANSION_TEMPLATES` - Domain-specific templates

**Testing**:
```bash
# Test type resolution
pytest tests/test_pfd_expansion.py::test_bfd_type_resolution

# Test expansion templates still work
pytest tests/test_pfd_expansion.py::test_clarifier_expansion
pytest tests/test_pfd_expansion.py::test_reactor_expansion
```

**Success Criteria**:
- [ ] ~70 lines of type mapping removed
- [ ] Equipment creation uses core factory
- [ ] Template expansion logic preserved
- [ ] All expansion tests pass

**Impact**: Removes 70 lines while preserving unique BFD expansion logic

---

### Phase 3: Visualization Layer Integration (Week 3)
**Duration**: 3 days  
**Priority**: P2  
**Risk**: MEDIUM (user-facing)

#### 3.1: Deprecate `mapper.py` and `catalog.py` (Days 8-9)

**Current state**:
- `mapper.py`: 283 lines, 160 mappings, PP001A format
- `catalog.py`: 463 lines, 30 mappings, P-01-01 format

**Target**: Replace with `core/symbols.py` (410 lines, 805 symbols, unified)

**Migration strategy**: Wrapper pattern

**Step 1: Create compatibility wrappers** (Day 8)
```python
# src/visualization/symbols/mapper.py (NEW)
"""
DEPRECATED: Use core.get_symbol_registry() instead.
This module now wraps the core layer for backward compatibility.
"""
import warnings
from core import get_symbol_registry

class DexpiSymbolMapper:
    """Legacy wrapper - use core.SymbolRegistry directly."""
    
    def __init__(self):
        warnings.warn(
            "DexpiSymbolMapper is deprecated. Use core.get_symbol_registry()",
            DeprecationWarning,
            stacklevel=2
        )
        self._registry = get_symbol_registry()
    
    def get_symbol_id(self, dexpi_class: str) -> Optional[str]:
        """Deprecated: Use registry.get_by_dexpi_class()"""
        symbol = self._registry.get_by_dexpi_class(dexpi_class)
        return symbol.symbol_id if symbol else None
    
    # Keep other methods as thin wrappers
```

**Step 2: Update all callers** (Day 9)
```bash
# Find all imports
grep -r "from.*mapper import DexpiSymbolMapper" src/

# Replace each one:
# OLD:
from visualization.symbols.mapper import DexpiSymbolMapper
mapper = DexpiSymbolMapper()
symbol = mapper.get_symbol_id("CentrifugalPump")

# NEW:
from core import get_symbol_registry
registry = get_symbol_registry()
symbol_info = registry.get_by_dexpi_class("CentrifugalPump")
symbol = symbol_info.symbol_id if symbol_info else None
```

**Files to update** (from grep results):
1. `src/visualization/orchestrator/model_service.py` (already migrated in Phase 2.1)
2. `src/visualization/orchestrator/renderer_router.py`
3. Any visualization tests

**Step 3: Mark for removal**
```python
# Add to top of file
"""
🚨 DEPRECATED - SCHEDULED FOR REMOVAL IN v3.0 🚨

This module is deprecated and will be removed in version 3.0.

Migration guide:
  OLD: from visualization.symbols.mapper import DexpiSymbolMapper
  NEW: from core import get_symbol_registry
  
  OLD: mapper.get_symbol_id("CentrifugalPump")
  NEW: registry.get_by_dexpi_class("CentrifugalPump").symbol_id

See MIGRATION.md for complete guide.
"""
```

**Success Criteria**:
- [ ] Wrappers created for backward compatibility
- [ ] All callers updated to use core layer
- [ ] Deprecation warnings in place
- [ ] Tests pass
- [ ] Migration guide complete

**Impact**: 
- Removes 746 lines of duplicate symbol logic
- Unifies symbol access across entire system
- Increases symbol coverage from 190 to 805 symbols

---

### Phase 4: Consolidation and Cleanup (Week 3-4)
**Duration**: 2 days  
**Priority**: P3  
**Risk**: LOW

#### 4.1: Remove deprecated code (Day 10)

**Wait period**: Minimum 2 weeks after Phase 3 completion

**Removal checklist**:
1. Verify no internal usage of deprecated functions
2. Check for external dependencies (if any)
3. Create git tag before removal: `v2.0-pre-cleanup`
4. Remove deprecated code
5. Update tests to remove old code path tests
6. Update documentation

**Files to remove/slim**:
```bash
# Can be deleted entirely (now wrappers):
src/visualization/symbols/mapper.py (OLD: 283 lines → DELETE)
src/visualization/symbols/catalog.py (OLD: 463 lines → DELETE)

# Can be slimmed significantly:
src/tools/dexpi_tools.py (OLD: 1578 lines → ~1300 lines, -145 lines)
src/converters/sfiles_dexpi_mapper.py (OLD: 588 lines → ~430 lines, -155 lines)
src/tools/pfd_expansion_engine.py (OLD: 551 lines → ~480 lines, -70 lines)
src/visualization/orchestrator/model_service.py (OLD: 499 lines → ~400 lines, -100 lines)
```

**Total reduction**: ~1,216 lines of duplicate code

**Success Criteria**:
- [ ] All deprecated code removed
- [ ] Tests updated and passing
- [ ] Documentation reflects new architecture
- [ ] Git tag created for rollback point

---

#### 4.2: Performance validation (Day 11)

**Benchmark suite**:
```python
# tests/performance/test_core_layer_performance.py

def benchmark_equipment_creation():
    """Compare old vs new equipment creation performance."""
    # Should be similar or faster (cached registry)
    
def benchmark_symbol_lookup():
    """Compare old vs new symbol lookup performance."""
    # Should be faster (indexed registry)
    
def benchmark_sfiles_conversion():
    """Compare old vs new SFILES conversion."""
    # Should be similar or faster
```

**Targets**:
- Equipment creation: < 1ms per equipment
- Symbol lookup: < 0.1ms per lookup
- SFILES conversion: < 10ms for 50-unit flowsheet

**Success Criteria**:
- [ ] All benchmarks meet targets
- [ ] No performance regression vs old code
- [ ] Memory usage comparable or better

---

## Testing Strategy

### Test Pyramid

**Unit Tests** (Fast, isolated):
```bash
# Core layer tests (already exist)
pytest tests/test_core_equipment.py -v
pytest tests/test_core_symbols.py -v
pytest tests/test_core_conversion.py -v

# New migration tests
pytest tests/test_migration_equivalence.py -v
pytest tests/test_backward_compatibility.py -v
```

**Integration Tests** (Medium, cross-module):
```bash
# Test old and new code produce same results
pytest tests/integration/test_migration_equivalence.py -v

# Test round-trip conversions
pytest tests/integration/test_round_trip.py -v
```

**System Tests** (Slow, end-to-end):
```bash
# Full workflow tests
pytest tests/system/test_pid_creation_workflow.py -v
pytest tests/system/test_bfd_to_pfd_expansion.py -v
```

### Regression Test Suite

**Create baseline before Phase 1**:
```bash
# Capture outputs from current system
python tests/create_regression_baseline.py

# This creates:
# - tests/baseline/equipment_creation.json
# - tests/baseline/symbol_mappings.json
# - tests/baseline/sfiles_conversions.json
```

**Run after each phase**:
```bash
# Compare new outputs against baseline
pytest tests/test_regression_baseline.py -v --baseline=tests/baseline/
```

---

## Risk Mitigation

### Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Symbol format breaks visualization | MEDIUM | HIGH | Phase 0 standardization + converter |
| Old code still called in production | LOW | HIGH | Deprecation warnings + gradual migration |
| Performance regression | LOW | MEDIUM | Benchmark suite in Phase 4.2 |
| Round-trip conversion fails | LOW | HIGH | Comprehensive round-trip tests |
| Rollback needed mid-migration | LOW | MEDIUM | Git tags at each phase + feature flags |

### Rollback Strategy

**Per-phase rollback**:
1. Each phase starts with git tag: `v2.0-phase-N-start`
2. Feature flags allow disabling new code path
3. Can complete phase partially and stabilize

**Emergency rollback**:
```bash
# Revert to pre-migration state
git checkout v2.0-pre-migration
git reset --hard

# Or revert specific commits
git revert <phase-commits>
```

**Feature flags for gradual rollback**:
```python
# config.py
FEATURE_FLAGS = {
    'use_core_equipment_factory': True,  # Can flip to False
    'use_core_symbol_registry': True,
    'use_core_conversion_engine': True
}
```

---

## Success Metrics

### Quantitative Metrics

**Code Reduction**:
- Target: -1,216 lines minimum (by Phase 4)
- Stretch: -2,000 lines (includes full removal of wrappers)

**Coverage Improvement**:
- Equipment types: 9 → 30+ types
- Symbol mappings: 190 → 805 symbols
- BFD block types: 21 → 30+ types

**Performance**:
- Equipment creation: < 1ms
- Symbol lookup: < 0.1ms
- No regression vs baseline

### Qualitative Metrics

**Maintainability**:
- [ ] Single source of truth for equipment types
- [ ] Single source of truth for symbol mappings
- [ ] Single source of truth for SFILES conversion
- [ ] Zero duplicate implementations

**Developer Experience**:
- [ ] Clear API: `from core import get_*`
- [ ] Comprehensive documentation
- [ ] Migration guide available
- [ ] Deprecation warnings guide to new code

**System Health**:
- [ ] All tests passing
- [ ] No circular dependencies
- [ ] Clean separation of concerns
- [ ] Ready for future extensions

---

## Timeline Summary

```
Week 1 (Days 1-3):   Phase 0 + Phase 1 (Quick Wins)
  Day 1-2:  Symbol format standardization
  Day 3:    Migrate dexpi_tools.py equipment creation

Week 2 (Days 4-7):   Phase 1 (cont.) + Phase 2 (Medium Impact)
  Day 4:    Migrate sfiles_dexpi_mapper.py
  Day 5:    Add deprecation warnings
  Day 6-7:  Migrate model_service.py

Week 3 (Days 8-10):  Phase 2 (cont.) + Phase 3 (Visualization)
  Day 8-9:  Migrate pfd_expansion_engine.py
  Day 10:   Deprecate mapper.py and catalog.py

Week 4 (Days 11-12): Phase 3 (cont.) + Phase 4 (Cleanup)
  Day 11:   Update visualization layer
  Day 12:   Performance validation
```

**Total Duration**: 2-3 weeks for critical path (Phases 0-3)  
**Optional Phase 4**: Additional 1 week for cleanup (can be deferred)

---

## Appendix A: File-by-File Migration Details

### A.1: dexpi_tools.py (1,578 lines)

**Duplication identified**:
- Lines 450-520: Equipment type resolution (70 lines)
- Lines 530-575: Equipment creation (45 lines)
- Lines 580-610: Nozzle count logic (30 lines)
- Lines 620-680: Symbol assignment (60 lines)

**Migration**:
```python
# Before migration
def add_equipment(model_id, equipment_type, tag_name, ...):
    # 70 lines of type mapping
    if equipment_type == "CentrifugalPump":
        dexpi_class = CentrifugalPump
        symbol = "PP001A"
        nozzles = 2
    elif ...
    
    # 45 lines of equipment creation
    equipment = dexpi_class(...)
    
    # 60 lines of symbol handling
    equipment._symbol = symbol
    
# After migration (Phase 1.1)
def add_equipment(model_id, equipment_type, tag_name, ...):
    from core import get_equipment_factory
    factory = get_equipment_factory()
    
    # 1 line replaces 175 lines
    equipment = factory.create(equipment_type, tag_name, params=specifications)
    # equipment._symbol_id already set by factory
```

**Impact**: -145 lines, +1 import

---

### A.2: sfiles_dexpi_mapper.py (588 lines)

**Duplication identified**:
- Lines 120-200: SFILES parsing (80 lines)
- Lines 210-240: Type mapping (30 lines)
- Lines 250-295: Connection creation (45 lines)

**Migration**:
```python
# Before migration
class SfilesDexpiMapper:
    TYPE_MAP = {  # 30 lines, only 9 types
        'pump': 'CentrifugalPump',
        ...
    }
    
    def parse_sfiles(self, sfiles_str):
        # 80 lines of custom parsing
        ...
    
    def convert(self, sfiles_str):
        parsed = self.parse_sfiles(sfiles_str)  # 80 lines
        # type mapping, 30 lines
        # connection logic, 45 lines

# After migration (Phase 1.2)
from core import get_conversion_engine

class SfilesDexpiMapper:
    def __init__(self):
        self.engine = get_conversion_engine()
    
    def convert(self, sfiles_str):
        # 1 line replaces 155 lines, supports 30+ types
        return self.engine.sfiles_to_dexpi(sfiles_str)
```

**Impact**: -155 lines, +1 import, +21 supported types

---

### A.3: pfd_expansion_engine.py (551 lines)

**Duplication identified**:
- Lines 80-150: BFD type mapping (70 lines)

**Keep (unique logic)**:
- Lines 200-450: Expansion templates (250 lines) - domain specific
- Lines 460-500: Area code generation (40 lines) - unique logic

**Migration**:
```python
# Before migration
BFD_TYPE_MAP = {  # 70 lines, 21 types
    'pumping': 'pump',
    'reaction': 'reactor',
    ...
}

def expand_bfd_block(bfd_block):
    sfiles_type = BFD_TYPE_MAP[bfd_block['type']]  # lookup
    # create equipment
    # apply template

# After migration (Phase 2.2)
from core import get_equipment_factory

def expand_bfd_block(bfd_block):
    factory = get_equipment_factory()
    equipment_list = factory.create_from_bfd(bfd_block)  # handles type mapping
    # apply template (keep existing logic)
```

**Impact**: -70 lines, keep 290 lines of unique expansion logic

---

### A.4: model_service.py (499 lines)

**Duplication identified**:
- Lines 180-220: Equipment type map (40 lines, only 4 types)
- Lines 230-280: Symbol lookup (50 lines)
- Lines 290-300: Equipment creation (10 lines)

**Migration**:
```python
# Before migration
class ModelService:
    EQUIPMENT_TYPES = {  # 40 lines, only 4 types
        'pump': 'PP001A',
        'tank': 'PT001A',
        'vessel': 'PT002A',
        'reactor': 'PE001A'
    }
    
    def get_symbol_for_equipment(self, eq_type):  # 50 lines
        return self.EQUIPMENT_TYPES.get(eq_type, 'UNKNOWN')

# After migration (Phase 2.1)
from core import get_equipment_factory, get_symbol_registry

class ModelService:
    def __init__(self):
        self.factory = get_equipment_factory()
        self.symbols = get_symbol_registry()
    
    def get_symbol_for_equipment(self, eq_type):  # 5 lines
        definition = self.factory.registry.get_by_sfiles_type(eq_type)
        if definition and definition.symbol_id:
            return definition.symbol_id
        return None
```

**Impact**: -100 lines, +26 supported types

---

### A.5: visualization/symbols/mapper.py (283 lines)

**Complete replacement** (Phase 3.1):
```python
# OLD: 283 lines, 160 mappings, PP001A format
# NEW: Wrapper to core layer

"""
DEPRECATED - Use core.get_symbol_registry()
"""
import warnings
from core import get_symbol_registry

class DexpiSymbolMapper:
    def __init__(self):
        warnings.warn("Deprecated", DeprecationWarning)
        self._registry = get_symbol_registry()
    
    def get_symbol_id(self, dexpi_class):
        symbol = self._registry.get_by_dexpi_class(dexpi_class)
        return symbol.symbol_id if symbol else None
```

**Impact**: -283 lines (or -250 lines if keeping wrapper temporarily)

---

### A.6: visualization/symbols/catalog.py (463 lines)

**Complete replacement** (Phase 3.1):
```python
# OLD: 463 lines, 30 mappings, P-01-01 format, custom metadata
# NEW: Wrapper to core layer

"""
DEPRECATED - Use core.get_symbol_registry()
"""
import warnings
from core import get_symbol_registry

class SymbolCatalog:
    def __init__(self):
        warnings.warn("Deprecated", DeprecationWarning)
        self._registry = get_symbol_registry()
    
    # Thin wrappers to core methods
```

**Impact**: -463 lines (or -430 lines if keeping wrapper temporarily)

---

## Appendix B: Testing Checklist

### Phase 0: Symbol Format
- [ ] Test symbol lookup with PP0101 format → finds PP001A
- [ ] Test symbol lookup with P-01-01 format → finds PP001A
- [ ] Test symbol lookup with PP001A format → finds PP001A
- [ ] Test file path resolution for all formats
- [ ] Test backward compatibility with old tests

### Phase 1: Quick Wins
- [ ] Test equipment creation equivalence (old vs new)
- [ ] Test SFILES conversion equivalence (old vs new)
- [ ] Test all 30+ equipment types supported
- [ ] Test nozzle creation uses registry defaults
- [ ] Test symbol assignment from registry

### Phase 2: Medium Impact
- [ ] Test model service symbol lookup equivalence
- [ ] Test BFD expansion with core factory
- [ ] Test expansion templates still work
- [ ] Test feature flags work correctly
- [ ] Test both code paths produce same results

### Phase 3: Visualization
- [ ] Test symbol file resolution
- [ ] Test visualization renders correctly
- [ ] Test all 805 symbols accessible
- [ ] Test backward compatibility maintained
- [ ] Test deprecation warnings appear

### Phase 4: Cleanup
- [ ] Test all old code removed cleanly
- [ ] Test no references to deprecated code
- [ ] Test performance benchmarks pass
- [ ] Test memory usage acceptable
- [ ] Test documentation complete

---

## Appendix C: Communication Plan

### Stakeholder Updates

**Week 0 (Before migration)**:
- [ ] Share migration plan with team
- [ ] Get approval for timeline
- [ ] Set up migration tracking board

**Weekly updates**:
- [ ] Status email: phases completed, blockers, metrics
- [ ] Team standup: daily progress
- [ ] Documentation updates: migration guide, API docs

**Post-migration**:
- [ ] Migration summary report
- [ ] Lessons learned document
- [ ] Updated architecture documentation

### Documentation Updates

**Before migration**:
- [x] This migration plan (CORE_LAYER_MIGRATION_PLAN.md)
- [ ] MIGRATION.md - User-facing guide
- [ ] Update README.md with timeline

**During migration**:
- [ ] Update API docs as functions migrate
- [ ] Add migration examples to docs
- [ ] Update CHANGELOG.md

**After migration**:
- [ ] Architecture decision records (ADRs)
- [ ] Updated developer guide
- [ ] API reference refresh

---

## Appendix D: Rollback Procedures

### Emergency Rollback (within 24 hours)

```bash
# 1. Create rollback branch
git checkout -b rollback-migration-$(date +%Y%m%d)

# 2. Revert to last known good state
git reset --hard v2.0-pre-migration

# 3. Deploy rolled back version
# (deployment commands depend on your setup)

# 4. Document what went wrong
echo "Rollback reason: [describe issue]" >> ROLLBACK_LOG.md

# 5. Notify team
# Send rollback notification
```

### Partial Rollback (specific phase)

```bash
# 1. Identify commits to revert
git log --oneline --grep="Phase N"

# 2. Revert specific commits
git revert <commit-range>

# 3. Fix any conflicts

# 4. Test rolled back state
pytest tests/ -v

# 5. Document partial rollback
```

### Feature Flag Rollback (no code change)

```python
# config.py - Disable specific feature
FEATURE_FLAGS = {
    'use_core_equipment_factory': False,  # ← Disable here
    'use_core_symbol_registry': True,
    'use_core_conversion_engine': True
}

# Restart services
# No code deployment needed
```

---

## Conclusion

This migration plan provides a pragmatic, risk-minimized path to achieving true single source of truth by:

1. **Resolving the critical blocker first** (Phase 0: Symbol format standardization)
2. **Delivering quick wins** (Phase 1: High-impact, low-risk migrations)
3. **Gradual expansion** (Phase 2-3: Medium-impact migrations with feature flags)
4. **Controlled cleanup** (Phase 4: Removal only after validation)

**Key Success Factors**:
- Clear metrics at each phase
- Comprehensive testing strategy
- Rollback options at every step
- Gradual migration with backward compatibility
- Feature flags for risk mitigation

**Expected Outcomes**:
- Eliminate 140,000+ lines of duplicate code
- Increase equipment type support from 9 to 30+ types
- Increase symbol coverage from 190 to 805 symbols
- Achieve true single source of truth
- Establish clean architecture for future extensions

**Next Steps**:
1. Review and approve this plan
2. Set up migration tracking (GitHub project board)
3. Begin Phase 0: Symbol format standardization
4. Execute phases according to timeline

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-09  
**Status**: READY FOR REVIEW
