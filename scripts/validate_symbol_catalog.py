#!/usr/bin/env python3
"""
Validate symbol catalog dexpi_class mappings

This script validates that:
1. All equipment/valve symbols have dexpi_class mappings where possible
2. The catalog structure is valid
3. No regressions in dexpi_class field

Usage:
    python scripts/validate_symbol_catalog.py

Exit codes:
    0: Validation passed
    1: Validation failed (errors found)
"""

import json
import sys
from pathlib import Path
from collections import Counter


def main():
    """Validate merged_catalog.json"""

    # Path to catalog
    repo_root = Path(__file__).parent.parent
    catalog_path = repo_root / "src" / "visualization" / "symbols" / "assets" / "merged_catalog.json"

    print(f"Validating catalog: {catalog_path}")
    print("=" * 70)

    # Load catalog
    try:
        with open(catalog_path) as f:
            catalog = json.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: Catalog not found at {catalog_path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in catalog: {e}")
        return 1

    # Validate structure
    required_keys = ["version", "statistics", "symbols"]
    missing_keys = [key for key in required_keys if key not in catalog]
    if missing_keys:
        print(f"❌ ERROR: Missing required keys: {missing_keys}")
        return 1

    total_symbols = len(catalog["symbols"])
    print(f"✅ Valid JSON structure")
    print(f"   Total symbols: {total_symbols}")

    # Count dexpi_class mappings
    null_count = 0
    mapped_count = 0
    equipment_prefixes = ("PP", "PT", "PV", "PE", "PS")  # Equipment, tank, valve, equipment, separator
    equipment_null = []
    equipment_mapped = []

    for symbol_id, symbol_data in catalog["symbols"].items():
        dexpi_class = symbol_data.get("dexpi_class")
        is_equipment = symbol_id.startswith(equipment_prefixes)

        if dexpi_class is None:
            null_count += 1
            if is_equipment:
                equipment_null.append(symbol_id)
        else:
            mapped_count += 1
            if is_equipment:
                equipment_mapped.append(symbol_id)

    # Report statistics
    print(f"\n📊 DEXPI Class Mapping Statistics:")
    print(f"   Mapped:   {mapped_count:4d} ({mapped_count/total_symbols*100:.1f}%)")
    print(f"   Unmapped: {null_count:4d} ({null_count/total_symbols*100:.1f}%)")

    print(f"\n📊 Equipment Symbol Statistics:")
    print(f"   Mapped equipment:   {len(equipment_mapped):3d}")
    print(f"   Unmapped equipment: {len(equipment_null):3d}")

    # Category breakdown
    categories = Counter(s.get("category") for s in catalog["symbols"].values())
    print(f"\n📊 Categories:")
    for category, count in categories.most_common(10):
        print(f"   {category:20s}: {count:3d}")

    # Percentage-based thresholds to protect against regression
    # Current baseline: 308 total (38.3%), 289 equipment (76.7%)
    MIN_MAPPED_PERCENTAGE = 35.0  # Require at least 35% of all symbols mapped
    MIN_EQUIPMENT_PERCENTAGE = 70.0  # Require at least 70% of equipment symbols mapped

    total_equipment = len(equipment_mapped) + len(equipment_null)
    mapped_percentage = (mapped_count / total_symbols) * 100 if total_symbols > 0 else 0
    equipment_percentage = (len(equipment_mapped) / total_equipment) * 100 if total_equipment > 0 else 0

    errors = []

    if mapped_percentage < MIN_MAPPED_PERCENTAGE:
        errors.append(
            f"Only {mapped_percentage:.1f}% of symbols mapped "
            f"(expected >={MIN_MAPPED_PERCENTAGE}%, {mapped_count}/{total_symbols} symbols)"
        )

    if equipment_percentage < MIN_EQUIPMENT_PERCENTAGE:
        errors.append(
            f"Only {equipment_percentage:.1f}% of equipment symbols mapped "
            f"(expected >={MIN_EQUIPMENT_PERCENTAGE}%, {len(equipment_mapped)}/{total_equipment} symbols)"
        )

    # Show sample of unmapped equipment
    if equipment_null:
        print(f"\n⚠️  Sample unmapped equipment symbols (first 10):")
        for symbol_id in equipment_null[:10]:
            print(f"   - {symbol_id}")

    # Final verdict
    print(f"\n{'=' * 70}")
    if errors:
        print("❌ VALIDATION FAILED")
        for error in errors:
            print(f"   - {error}")
        return 1
    else:
        print("✅ VALIDATION PASSED")
        print(f"   - {mapped_count} symbols have dexpi_class mappings")
        print(f"   - {len(equipment_mapped)} equipment symbols mapped")
        print(f"   - Catalog structure is valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
