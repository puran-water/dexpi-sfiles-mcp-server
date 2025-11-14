#!/usr/bin/env python3
"""
DEPRECATED: Enrich merged_catalog.json with dexpi_class mappings from mapper.py

WARNING: This script is deprecated and will be removed in v2.0.

The catalog enrichment is now handled automatically by the ComponentRegistry
and SymbolRegistry systems. Manual enrichment is no longer needed and creates
circular dependencies (registry loads catalog → script mutates catalog → registry reload).

The merged_catalog.json is already sufficiently enriched (308/805 symbols have dexpi_class).
Additional mappings should be added through the symbol generation pipeline, not manual enrichment.

This script is kept for reference only and may not work correctly with the new architecture.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Set

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.visualization.symbols.mapper import DexpiSymbolMapper


def enrich_catalog():
    """Enrich catalog with DEXPI class mappings."""

    import warnings
    warnings.warn(
        "enrich_symbol_catalog.py is deprecated and will be removed in v2.0. "
        "Catalog enrichment creates circular dependencies. "
        "Use the symbol generation pipeline instead.",
        DeprecationWarning
    )

    # Paths
    catalog_path = Path(__file__).parent.parent / "src" / "visualization" / "symbols" / "assets" / "merged_catalog.json"
    backup_path = catalog_path.with_suffix('.json.backup')

    print("=" * 60)
    print("Enriching Symbol Catalog with DEXPI Class Mappings")
    print("=" * 60)

    # Load catalog
    print(f"\n1. Loading catalog from: {catalog_path}")
    with open(catalog_path) as f:
        catalog = json.load(f)

    total_symbols = len(catalog.get('symbols', {}))
    print(f"   Total symbols: {total_symbols}")

    # Initialize mapper
    print("\n2. Loading DEXPI class mappings from mapper.py")
    mapper = DexpiSymbolMapper()

    # Get all mappings
    total_mappings = len(mapper.SYMBOL_MAPPINGS)
    print(f"   Total DEXPI class mappings: {total_mappings}")

    # Create reverse mapping: symbol_id -> dexpi_class
    symbol_to_dexpi: Dict[str, str] = {}
    dexpi_to_symbol: Dict[str, str] = {}

    for dexpi_class, mapping in mapper.SYMBOL_MAPPINGS.items():
        symbol_id = mapping.symbol_id
        dexpi_to_symbol[dexpi_class] = symbol_id

        # Map symbol to DEXPI class
        if symbol_id not in symbol_to_dexpi:
            symbol_to_dexpi[symbol_id] = dexpi_class
        else:
            # Multiple DEXPI classes map to same symbol
            # Keep the first one (could append to list in future)
            pass

    print(f"   Unique symbol IDs with mappings: {len(symbol_to_dexpi)}")

    # Backup original
    print(f"\n3. Creating backup: {backup_path}")
    with open(backup_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    # Enrich catalog
    print("\n4. Enriching catalog entries:")
    enriched_count = 0
    null_count = 0

    for symbol_id, symbol_data in catalog['symbols'].items():
        if symbol_id in symbol_to_dexpi:
            symbol_data['dexpi_class'] = symbol_to_dexpi[symbol_id]
            enriched_count += 1
        else:
            # Check variants (A/B suffixes)
            base_id = symbol_id.rstrip('B').rstrip('A')
            for variant in [base_id, base_id + 'A', base_id + 'B']:
                if variant in symbol_to_dexpi:
                    symbol_data['dexpi_class'] = symbol_to_dexpi[variant]
                    enriched_count += 1
                    break
            else:
                null_count += 1

    print(f"   Enriched: {enriched_count} symbols")
    print(f"   Still null: {null_count} symbols (no mapping available)")

    # Update metadata
    catalog['enrichment'] = {
        'dexpi_mappings_applied': True,
        'mappings_source': 'src/visualization/symbols/mapper.py',
        'enriched_count': enriched_count,
        'null_count': null_count
    }

    # Save enriched catalog
    print(f"\n5. Saving enriched catalog: {catalog_path}")
    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    print("\n6. Verification:")
    print(f"   Before: All symbols had dexpi_class=null")
    print(f"   After: {enriched_count} symbols have dexpi_class mappings")
    print(f"   Coverage: {enriched_count / total_symbols * 100:.1f}%")

    # Show examples
    print("\n7. Example mappings:")
    examples = [
        'PP001A',  # CentrifugalPump
        'PV005A',  # GateValve
        'PE025A',  # Tank
        'PE037A',  # HeatExchanger
    ]

    for symbol_id in examples:
        if symbol_id in catalog['symbols']:
            dexpi_class = catalog['symbols'][symbol_id].get('dexpi_class')
            name = catalog['symbols'][symbol_id].get('name', 'Unknown')
            if dexpi_class:
                print(f"   ✓ {symbol_id} ({name}): {dexpi_class}")
            else:
                print(f"   ✗ {symbol_id} ({name}): null")

    # Show DEXPI class distribution
    print("\n8. DEXPI class distribution (top 10):")
    dexpi_counts: Dict[str, int] = {}
    for symbol_data in catalog['symbols'].values():
        dexpi_class = symbol_data.get('dexpi_class')
        if dexpi_class:
            dexpi_counts[dexpi_class] = dexpi_counts.get(dexpi_class, 0) + 1

    for dexpi_class, count in sorted(dexpi_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {dexpi_class}: {count} symbols")

    print("\n" + "=" * 60)
    print("Enrichment Complete!")
    print("=" * 60)
    print(f"\nBackup saved to: {backup_path}")
    print(f"Enriched catalog: {catalog_path}")
    print(f"\n✓ Bug #2 Fixed: {enriched_count} symbols now have dexpi_class mappings")

    return enriched_count, null_count


if __name__ == '__main__':
    try:
        enrich_catalog()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
