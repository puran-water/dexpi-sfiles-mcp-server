"""
Core Layer - Single Source of Truth for Engineering MCP Server

This layer provides canonical implementations and registries to eliminate
duplication across the codebase. All business logic should reference these
core modules rather than maintaining their own mappings.

Modules:
- equipment_registry: Canonical equipment type mappings and metadata
- equipment_factory: Unified equipment instantiation logic
- symbol_registry: Single source for DEXPI class to symbol mappings
- conversion_engine: Unified SFILES↔DEXPI conversion logic
"""

from .equipment import (
    EquipmentRegistry,
    EquipmentFactory,
    EquipmentDefinition,
    EquipmentCategory,
    get_registry as get_equipment_registry,
    get_factory as get_equipment_factory
)
from .symbols import (
    SymbolRegistry,
    SymbolInfo,
    SymbolSource,
    SymbolCategory,
    get_registry as get_symbol_registry
)
from .conversion import (
    ConversionEngine,
    SfilesModel,
    SfilesUnit,
    SfilesStream,
    get_engine as get_conversion_engine
)
from .layout_store import (
    LayoutStore,
    LayoutNotFoundError,
    OptimisticLockError,
    create_layout_store,
)

__all__ = [
    # Equipment
    'EquipmentRegistry',
    'EquipmentFactory',
    'EquipmentDefinition',
    'EquipmentCategory',
    'get_equipment_registry',
    'get_equipment_factory',
    # Symbols
    'SymbolRegistry',
    'SymbolInfo',
    'SymbolSource',
    'SymbolCategory',
    'get_symbol_registry',
    # Conversion
    'ConversionEngine',
    'SfilesModel',
    'SfilesUnit',
    'SfilesStream',
    'get_conversion_engine',
    # Layout
    'LayoutStore',
    'LayoutNotFoundError',
    'OptimisticLockError',
    'create_layout_store',
]