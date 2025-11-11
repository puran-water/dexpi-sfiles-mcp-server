# Codex Analysis: Equipment Coverage Gap Investigation

**Date**: November 11, 2025
**Analysis Tool**: Codex MCP with DeepWiki + GitHub CLI
**Repositories Analyzed**:
- https://github.com/process-intelligence-research/pyDEXPI
- https://github.com/process-intelligence-research/SFILES2

## Executive Summary

Codex investigation confirms **no deliberate design decision** caused the 12% equipment coverage (19/159 classes). The gap resulted from technical debt: SFILES-centric shortcuts, manual registration overhead, missing regression tests, and documentation drift.

**Critical Finding**: We misunderstood SFILES design - it expects **1:Many expansion** to DEXPI specializations, not 1:1 mappings.

## Historical Context

### What Codex Found in Repository History

1. **No architectural decision documents** explaining 19-class limitation
2. **Documentation drift**: Tools claim "159 types" but deliver 24 shortcuts
3. **Missing regression tests**: No automated check for coverage completeness
4. **Symbol utilization capped**: 62% of symbols (497/805) unused due to missing equipment types

### Root Causes Identified

| Issue | Evidence | Impact |
|-------|----------|---------|
| SFILES-centric mindset | Only imported 24 pyDEXPI classes matching SFILES aliases | 88% of standard equipment unreachable |
| Manual registration overhead | Each type needs ~10 lines, seemed prohibitive for 159 types | Led to selective registration instead of completeness |
| No fail-fast tests | No automated validation of coverage percentage | Gap persisted through Phases 0-5 undetected |
| Documentation drift | MCP tools advertise 159 types in schemas | Erodes user trust, violates published contracts |

## Upstream Library Analysis

### pyDEXPI Findings

**Equipment Classes** (159 total):
- ✅ All properly defined and stable
- ✅ Based on ISO 15926 standard
- ✅ Includes power generation, material handling, bulk solids, mobile transport
- ✅ Custom* variants for extensibility

**Valve Classes** (22 total):
- We import: 4 classes
- Available: BallValve, PlugValve, SafetyValve, CheckValve, OperatedValve, and 17+ more
- **Gap**: 18 valve types missing (82% coverage gap)

**Instrumentation Classes** (34 total):
- We import: ~10 classes for control loops
- Available: Full sensor/actuator/controller taxonomy
- **Status**: Better than equipment, but still gaps

**Design Philosophy**:
- Expects clients to use `CustomEquipment` with `typeName` metadata for unknowns
- `MLGraphLoader` coerces unknown components to `CustomEquipment` while preserving semantics
- Recommendation: Fail-soft with metadata preservation, not hard failures

### SFILES2 Findings

**Equipment Notation** (~24 OntoCape aliases):
- Intentionally minimal by design
- Aliases: pump, heat_exchanger, separator, reactor, tank, mixer, etc.
- **Critical**: Each alias maps to a **family** of DEXPI classes, not a single class

**Mapping Philosophy**:
```
SFILES "pump" → pyDEXPI [CentrifugalPump, ReciprocatingPump, RotaryPump, EjectorPump, ...]
SFILES "heat_exchanger" → pyDEXPI [HeatExchanger, PlateHeatExchanger, TubularHeatExchanger, ...]
```

**BFD vs PFD**:
- BFD blocks (high-level): storage, reaction, separation, distillation
- PFD equipment (detailed): Uses OntoCape aliases
- Expected expansion: BFD block → multiple PFD equipment → detailed DEXPI classes

**Current Parser Issue**:
- Only detects 4 BFD types: reactor, clarifier, treatment, separation
- Missing: power blocks, solids handling, utility systems
- Result: BFD expansion never triggers for many process types

## Gap Matrix: SFILES ↔ pyDEXPI

### Current 1:1 Mappings (Incorrect Design)

| SFILES Alias | Current DEXPI Class | Problem |
|--------------|---------------------|---------|
| pump | CentrifugalPump only | Ignores ReciprocatingPump, RotaryPump, EjectorPump |
| heat_exchanger | HeatExchanger only | Ignores Plate, Tubular, Spiral variants |
| separator | Separator only | Ignores Gravitational, Mechanical, Scrubbing types |
| turbine | Turbine only | Ignores SteamTurbine, GasTurbine specializations |

### Should Be 1:Many Mappings

| SFILES Alias | Primary Class | Variants (Total Classes) |
|--------------|---------------|--------------------------|
| pump | CentrifugalPump | ReciprocatingPump, RotaryPump, EjectorPump, CustomPump (5) |
| heat_exchanger | HeatExchanger | PlateHeatExchanger, TubularHeatExchanger, SpiralHeatExchanger, ThinFilmEvaporator, SprayCooler, HeatedSurfaceDryer (7) |
| separator | Separator | GravitationalSeparator, MechanicalSeparator, ScrubbingSeparator, ElectricalSeparator, CustomSeparator (6) |
| centrifuge | Centrifuge | FilteringCentrifuge, SedimentalCentrifuge, CustomCentrifuge (4) |
| compressor | Compressor | CentrifugalCompressor, AxialCompressor, ReciprocatingCompressor, RotaryCompressor (5) |

### Missing Equipment Categories

**Power Generation** (8 classes, 0 registered):
- SteamGenerator, SteamTurbine, GasTurbine
- Boiler, ElectricGenerator (AC/DC)
- CombustionEngine
- **Impact**: Cannot model power plants or utility systems

**Material Handling** (15 classes, 0 registered):
- Conveyor, Crusher, Mill, Grinder, Extruder
- Screw, Feeder, Lift
- Mobile transport (ForkliftTruck, Truck, Ship, RailWaggon)
- LoadingUnloadingSystem, PackagingSystem, TransportableContainer
- **Impact**: Cannot model solids processing or logistics

**Specialized Processing** (20 classes, 0 registered):
- Kneader, Agglomerator, Pelletizer, Briquetting equipment
- Multiple Sieve types, Weigher types
- CoolingTower variants, Column internals
- **Impact**: Cannot model bulk solids, specialty chemicals, food processing

**Heat Transfer Variants** (10 classes, 1 registered):
- Only HeatExchanger registered
- Missing: Plate, Tubular, Spiral variants
- Missing: CustomHeater, ElectricHeater
- Missing: Dryer variants, Evaporators, Coolers
- **Impact**: Cannot specify exchanger types for engineering calculations

## Symbol Coverage Impact

### Root Cause of 38% Symbol Coverage

**Hypothesis Confirmed**: 62% of symbols (497/805) are unused because corresponding equipment types aren't registered.

**Symbol families with no equipment types:**
- Boiler symbols → No Boiler, SteamGenerator classes
- Crusher/Mill symbols → No material handling classes
- Conveyor symbols → No Conveyor, Screw, Feeder classes
- Specialized separator symbols → No separator variant classes
- Power generation symbols → No turbine/generator variants

**Expected Impact of Full Coverage**:
- Registering 140 missing equipment types should unlock 200-300 additional symbols
- Final symbol coverage estimate: 60-70% (508-608/805)
- Remaining 30-40% symbols may be deprecated or highly specialized

## PFD → P&ID Expansion Analysis

### Current BFD Expansion Issues

**BFD Detection Logic** (src/core/conversion.py:191-199):
```python
# Only detects 4 BFD types:
if unit_type in ['reactor', 'clarifier', 'treatment', 'separation']:
    is_bfd = True
```

**Missing BFD Types**:
- Power blocks: boiler, steam_generator, turbine
- Solids: silo, conveyor, crusher, mill
- Utilities: cooling_tower, waste_gas_emitter
- Transport: packaging, loading_unloading

**Result**: BFD expansion never triggers for these process types

### Recommended Expansion Strategy

**For Equipment in Both Libraries** (SFILES2 ↔ pyDEXPI):
1. Register primary DEXPI class for SFILES alias
2. Register all variants with qualified names:
   - "pump" → CentrifugalPump (primary)
   - "pump_reciprocating" → ReciprocatingPump
   - "pump_rotary" → RotaryPump
3. BFD expansion templates select appropriate variant based on process context

**For Equipment in SFILES2 Only**:
- Map to closest pyDEXPI base class (e.g., ProcessColumn for any tower)
- Use `CustomEquipment` with `typeName` metadata preserving SFILES semantic
- Document mapping decision for users

**For Equipment in pyDEXPI Only**:
- Register with snake_case SFILES alias auto-generated from class name
  - SteamGenerator → "steam_generator"
  - LoadingUnloadingSystem → "loading_unloading_system"
- No BFD expansion template needed (PFD/P&ID only)

**For Complete Mismatches**:
- SFILES "mixer" can expand to Mixer (stirred) OR StaticMixer (inline)
- Use process context or explicit user parameter to disambiguate
- Default to most common type, allow override

## Implementation Recommendations

### 1. Use DexpiIntrospector for Auto-Generation

**Tool**: `src/tools/dexpi_introspector.py` already exists

**Process**:
```python
from src.tools.dexpi_introspector import DexpiIntrospector

introspector = DexpiIntrospector()
equipment_classes = introspector.get_available_types()

# Generate registration scaffolding for all 159 classes
# Output: CSV or Python script with EquipmentDefinition entries
```

**Benefits**:
- Avoids 1,600 lines of manual code
- Ensures no classes missed
- Can regenerate if pyDEXPI updates

### 2. Implement Regression Tests

**Test Coverage**:
```python
def test_all_pydexpi_classes_registered():
    """Verify all 159 pyDEXPI equipment classes are registered."""
    introspector = DexpiIntrospector()
    upstream_classes = set(introspector.get_available_types()['equipment'])

    registry = get_registry()
    registered_classes = set(d.dexpi_class.__name__ for d in registry._definitions.values())

    missing = upstream_classes - registered_classes
    assert len(missing) == 0, f"Missing {len(missing)} classes: {sorted(missing)}"

def test_one_to_many_mappings():
    """Verify SFILES aliases map to multiple DEXPI variants."""
    registry = get_registry()

    # Test pump family
    pump_variants = [
        registry.get_by_sfiles_type('pump'),           # CentrifugalPump
        registry.get_by_sfiles_type('pump_reciprocating'),
        registry.get_by_sfiles_type('pump_rotary'),
        registry.get_by_sfiles_type('pump_ejector')
    ]
    assert all(v is not None for v in pump_variants), "Missing pump variants"
    assert len(set(v.dexpi_class for v in pump_variants)) == 4, "Should map to 4 distinct classes"
```

### 3. Expand BFD Detection

**Update** src/core/conversion.py:191-199:
```python
BFD_TYPES = {
    # Existing
    'reactor', 'clarifier', 'treatment', 'separation', 'distillation',
    # Power generation
    'boiler', 'steam_generation', 'turbine', 'generator',
    # Solids handling
    'silo', 'storage', 'conveyor', 'crusher', 'mill', 'packaging',
    # Utilities
    'cooling_tower', 'waste_gas', 'scrubber', 'flare'
}

if unit_type in BFD_TYPES:
    is_bfd = True
```

### 4. Support CustomEquipment with Metadata

**Pattern**:
```python
# When exact DEXPI class not found
equipment = CustomEquipment()
equipment.tagName = tag
equipment.typeName = sfiles_type  # Preserve original semantic
equipment.ComponentClass = "Equipment"
equipment.ComponentName = sfiles_type.title()
# Add to model

# Downstream analytics can recover type from typeName
```

### 5. Update MCP Schemas

**Current (misleading)**:
```yaml
equipment_type:
  description: "Equipment type (one of 159 available)"
  enum: [pump, tank, mixer, ...]  # Only 24 items!
```

**Updated (accurate)**:
```yaml
equipment_type:
  description: "Equipment type (DEXPI class name or SFILES alias)"
  type: string
  examples:
    - "CentrifugalPump"  # Direct DEXPI class
    - "pump"             # SFILES alias (→ CentrifugalPump)
    - "pump_reciprocating"  # Variant alias
    - "SteamGenerator"   # Full class name
```

## Timeline & Effort

### Revised Estimate (Auto-Generation Approach)

**Phase 1: Auto-Generation Script** (2-3 hours)
- Run DexpiIntrospector to enumerate 159 classes
- Generate registration scaffolding (CSV/script)
- Map to NOAKADEXPI symbols (308 available)
- Define 1:Many SFILES mappings

**Phase 2: Core Layer Integration** (2-3 hours)
- Import all 159 classes (replace 24 imports)
- Apply generated EquipmentDefinition entries
- Update `_register()` for variant aliases
- Expand BFD detection list

**Phase 3: Regression Tests** (1-2 hours)
- Create tests/core/test_equipment_coverage.py
- Test all 159 classes registered
- Test 1:Many mappings
- Test instantiation

**Phase 4: Documentation** (1-2 hours)
- Update MCP schemas
- Revise CHANGELOG
- Equipment catalog
- Migration guide

**Total: 6-10 hours** (vs 14-20 hours manual)

## Open Questions & Recommendations

### 1. DEXPI Class Names vs SFILES Aliases as Primary Keys?

**Codex Recommendation**: Support both
- DEXPI class name as canonical key (e.g., "SteamGenerator")
- SFILES alias as alternative (e.g., "steam_generator")
- Registry lookup checks both maps

**Rationale**:
- Advanced users want precise DEXPI class selection
- SFILES users want simple shortcuts
- Supporting both maintains backward compatibility

### 2. Equipment Without Symbols?

**Codex Recommendation**: Use placeholders
- Assign "PE_CUSTOM_nnn" or similar
- Document for future symbol creation from NOAKADEXPI
- Don't block registration for symbol absence

### 3. Auto-Generate SFILES Shortcuts?

**Codex Recommendation**: Yes
- SteamGenerator → "steam_generator" (snake_case)
- LoadingUnloadingSystem → "loading_unloading_system"
- Allow manual override for better names

### 4. Handle Custom* Variant Classes?

**Codex Recommendation**: Register them, prefer specific
- Register CustomPump, CustomHeater, etc.
- Recommend specific types where available
- Use Custom* when user explicitly requests or no better match

## Conclusion

The 12% equipment coverage was **technical debt, not a design choice**. Upstream libraries are complete and stable. The solution is:

1. **Auto-generate** registrations using existing DexpiIntrospector
2. **Implement 1:Many** SFILES → DEXPI mappings
3. **Add regression tests** to prevent future drift
4. **Update documentation** to match reality

**Expected outcomes**:
- 100% DEXPI compliance (159/159 classes)
- 60-70% symbol utilization (vs 38% today)
- Better BFD expansion coverage
- Restored user trust in MCP tools

**Priority**: CRITICAL - Blocks Phase 5 Week 4+ visualization work
