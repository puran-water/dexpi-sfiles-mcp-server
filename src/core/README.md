# Core Layer Architecture

## Overview

The core layer provides single sources of truth for all engineering data and operations, eliminating the 3-5 duplicate implementations that were scattered across the codebase.

## Problem Solved

Previously, the codebase had duplicate implementations of:
- **Equipment type mappings** in 3 places (sfiles_dexpi_mapper.py, pfd_expansion_engine.py, model_service.py)
- **Symbol mappings** in 3 places (mapper.py, catalog.py, importer.py)
- **Equipment creation logic** in 4 places
- **SFILES parsing** in 2 places
- **Conversion logic** scattered across multiple modules

This duplication made maintenance difficult and led to inconsistencies.

## Core Modules

### 1. equipment.py
**Single source of truth for equipment types and creation**

- `EquipmentRegistry`: Central registry of all equipment definitions
  - Maps between SFILES types, DEXPI classes, and BFD types
  - Stores metadata, validation rules, and expansion templates
  - 24 equipment types registered covering all common P&ID elements

- `EquipmentFactory`: Unified equipment instantiation
  - Creates equipment with proper initialization
  - Handles BFD to PFD expansion
  - Provides fallback for unknown types

### 2. symbols.py
**Canonical symbol mappings and metadata**

- `SymbolRegistry`: Manages all symbol data
  - Tracks 805 symbols from NOAKADEXPI and DISCDEXPI
  - Maintains provenance (which library each symbol comes from)
  - Maps DEXPI classes to symbol IDs
  - Provides search and categorization

### 3. conversion.py
**Unified SFILES ↔ DEXPI conversion engine**

- `ConversionEngine`: Bidirectional conversion with validation
  - Parses SFILES notation (simple and extended formats)
  - Converts to/from DEXPI models
  - Validates round-trip integrity
  - Handles BFD expansion

## Usage Examples

### Creating Equipment
```python
from core import get_equipment_factory

factory = get_equipment_factory()
pump = factory.create(
    equipment_type="pump",
    tag="P-101",
    params={"flowRate": 100.0, "head": 50.0}
)
```

### Looking Up Symbols
```python
from core import get_symbol_registry

registry = get_symbol_registry()
symbol = registry.get_by_dexpi_class("CentrifugalPump")
print(f"Symbol ID: {symbol.symbol_id}")
```

### Converting SFILES to DEXPI
```python
from core import get_conversion_engine

engine = get_conversion_engine()
sfiles = "feed[tank]->pump[pump]->reactor[reactor]"
dexpi_model = engine.sfiles_to_dexpi(sfiles)
```

## Migration Path

### Phase 1: Core Implementation ✅
- Created core modules with consolidated logic
- All tests passing

### Phase 2: Adapter Layer ✅
- Created dexpi_tools_v2.py as adapter
- Maintains MCP tool compatibility

### Phase 3: Module Refactoring (In Progress)
- Update existing modules to use core imports:
  - [ ] model_service.py
  - [ ] sfiles_dexpi_mapper.py
  - [ ] pfd_expansion_engine.py
  - [ ] visualization/orchestrator modules

### Phase 4: Cleanup
- Remove duplicate implementations
- Add deprecation warnings
- Update documentation

## Benefits

1. **Single Source of Truth**: Each concern has one owner
2. **Consistency**: All modules use the same definitions
3. **Maintainability**: Changes in one place affect entire system
4. **Extensibility**: Easy to add new equipment types or symbols
5. **Testability**: Core layer has comprehensive test coverage

## Architecture Principles

- **Separation of Concerns**: Each module has a single responsibility
- **Dependency Inversion**: Modules depend on abstractions (registries)
- **Open/Closed**: Easy to extend without modifying existing code
- **DRY**: No duplicate implementations

## Next Steps

1. Complete refactoring of existing modules
2. Add Proteus XML serialization support
3. Integrate with visualization pipeline
4. Add presentation/layout registry (as suggested by Codex)

## Testing

Run the test suite:
```bash
python3 test_core_layer.py
```

All core functionality is tested including:
- Equipment registry lookups
- Equipment factory creation
- Symbol registry searches
- SFILES/DEXPI conversion
- Round-trip validation