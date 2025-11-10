#!/usr/bin/env python3
"""
Backfill dexpi_class fields in merged_catalog.json using mapper.py mappings

This script populates the missing dexpi_class fields in the symbol catalog
by reverse-mapping from the SYMBOL_MAPPINGS in mapper.py.

Usage:
    python scripts/backfill_symbol_dexpi_classes.py

Fixes Bug #2: Symbol Catalog Missing DEXPI Mappings
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.visualization.symbols.mapper import DexpiSymbolMapper


def main():
    """Backfill dexpi_class fields in merged_catalog.json"""

    # Path to catalog
    repo_root = Path(__file__).parent.parent
    catalog_path = repo_root / "src" / "visualization" / "symbols" / "assets" / "merged_catalog.json"

    print(f"Loading catalog from: {catalog_path}")

    # Load catalog
    with open(catalog_path) as f:
        catalog = json.load(f)

    total_symbols = len(catalog["symbols"])
    print(f"Total symbols in catalog: {total_symbols}")

    # Create reverse mapping: symbol_id -> dexpi_class
    reverse_mapping = {}
    conflicts = {}

    # Instantiate mapper to access instance methods
    mapper = DexpiSymbolMapper()

    # 1. Add base SYMBOL_MAPPINGS
    for dexpi_class, mapping in DexpiSymbolMapper.SYMBOL_MAPPINGS.items():
        symbol_id = mapping.symbol_id
        if symbol_id in reverse_mapping:
            # Multiple DEXPI classes map to same symbol
            if symbol_id not in conflicts:
                conflicts[symbol_id] = [reverse_mapping[symbol_id]]
            conflicts[symbol_id].append(dexpi_class)
            continue
        reverse_mapping[symbol_id] = dexpi_class

    # 2. Add actuated variants (PV*B suffixes)
    actuated_map = {
        "PV003A": "PV003B",  # Three way
        "PV004A": "PV004B",  # Four way
        "PV005A": "PV005B",  # Gate
        "PV007A": "PV007B",  # Globe
        "PV008A": "PV008B",  # Float
        "PV014A": "PV014B",  # Pinch
        "PV015A": "PV015B",  # Diaphragm
        "PV016A": "PV016B",  # Needle
        "PV018A": "PV018B",  # Butterfly
        "PV019A": "PV019B",  # Ball
        "PV023A": "PV023B",  # Plug
    }

    for base_id, actuated_id in actuated_map.items():
        # Find the DEXPI class for the base symbol
        if base_id in reverse_mapping:
            base_dexpi_class = reverse_mapping[base_id]
            # Create "Operated" variant name
            actuated_dexpi_class = f"Operated{base_dexpi_class}"
            reverse_mapping[actuated_id] = actuated_dexpi_class

    # 3. Add ALTERNATIVE_MAPPINGS
    for dexpi_class, symbol_id in DexpiSymbolMapper.ALTERNATIVE_MAPPINGS.items():
        if symbol_id not in reverse_mapping:
            reverse_mapping[symbol_id] = dexpi_class

    print(f"Reverse mappings created: {len(reverse_mapping)}")
    print(f"  - Base mappings: {len(DexpiSymbolMapper.SYMBOL_MAPPINGS)}")
    print(f"  - Actuated variants: {len(actuated_map)}")
    print(f"  - Alternative mappings: {len(DexpiSymbolMapper.ALTERNATIVE_MAPPINGS)}")

    if conflicts:
        print(f"\nWarning: {len(conflicts)} symbol IDs have multiple DEXPI class mappings:")
        for symbol_id, dexpi_classes in list(conflicts.items())[:5]:
            print(f"  {symbol_id}: {', '.join(dexpi_classes)}")
        if len(conflicts) > 5:
            print(f"  ... and {len(conflicts) - 5} more")

    # Count current state
    null_before = sum(1 for s in catalog["symbols"].values() if s.get("dexpi_class") is None)
    print(f"\nSymbols with dexpi_class=null before: {null_before}")

    # Update catalog
    # Note: Catalog IDs may have suffixes like "_Origo", "_Detail", "_Option1"
    # We need to strip these to match against mapper base IDs
    suffixes = ["_Origo", "_Detail", "_Option1", "_Option2", "_Option3"]

    updated = 0
    no_match = []

    for symbol_id, symbol_data in catalog["symbols"].items():
        # Try exact match first
        if symbol_id in reverse_mapping:
            old_value = symbol_data.get("dexpi_class")
            new_value = reverse_mapping[symbol_id]
            symbol_data["dexpi_class"] = new_value
            if old_value != new_value:
                updated += 1
                if updated <= 5:  # Show first 5 updates
                    print(f"  Updated {symbol_id}: {old_value} -> {new_value}")
            continue

        # Try stripping suffixes
        base_id = symbol_id
        for suffix in suffixes:
            if symbol_id.endswith(suffix):
                base_id = symbol_id[:-len(suffix)]
                break

        if base_id != symbol_id and base_id in reverse_mapping:
            old_value = symbol_data.get("dexpi_class")
            new_value = reverse_mapping[base_id]
            symbol_data["dexpi_class"] = new_value
            if old_value != new_value:
                updated += 1
                if updated <= 10:  # Show first 10 updates
                    print(f"  Updated {symbol_id} (base: {base_id}): {old_value} -> {new_value}")
        elif symbol_id.startswith(("PP", "PT", "PV", "PE")):  # Equipment/valve symbols
            no_match.append(symbol_id)

    # Count after
    null_after = sum(1 for s in catalog["symbols"].values() if s.get("dexpi_class") is None)

    # Save back
    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    print(f"\n✅ Updated {updated} symbols with dexpi_class mappings")
    print(f"Symbols with dexpi_class=null after: {null_after}")
    print(f"Improvement: {null_before - null_after} symbols now have dexpi_class")

    if no_match:
        print(f"\n⚠️  {len(no_match)} equipment/valve symbols have no mapper entry:")
        for symbol_id in no_match[:10]:
            print(f"  - {symbol_id}")
        if len(no_match) > 10:
            print(f"  ... and {len(no_match) - 10} more")

    print(f"\nCatalog saved to: {catalog_path}")


if __name__ == "__main__":
    main()
