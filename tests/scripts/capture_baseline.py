#!/usr/bin/env python3
"""
Baseline Capture Script for Phase 1 Migration

Captures legacy behavior as JSON fixtures BEFORE migration starts.
Run once, commit fixtures to git, use for equivalence tests.

Usage:
    python tests/scripts/capture_baseline.py

Generates:
    tests/fixtures/baseline/equipment.json
    tests/fixtures/baseline/sfiles_conversions.json

These fixtures document the "before" state and remain valid
even after legacy code is deleted.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.fixtures.legacy_equipment import legacy_create_equipment, get_legacy_equipment_specs


def capture_equipment_baseline():
    """Capture equipment creation baseline for all types."""
    print("Capturing equipment baseline...")

    baseline = {}

    # Get test specifications
    equipment_specs = get_legacy_equipment_specs()

    for equipment_type, tag, specs, nozzles in equipment_specs:
        print(f"  - {equipment_type}: {tag}")

        try:
            equipment = legacy_create_equipment(equipment_type, tag, specs, nozzles)

            # Serialize equipment attributes
            baseline[f"{equipment_type}_{tag}"] = {
                'type': type(equipment).__name__,
                'equipment_type': equipment_type,
                'tagName': equipment.tagName,
                'nozzle_count': len(equipment.nozzles) if hasattr(equipment, 'nozzles') else 0,
                'nozzle_details': [
                    {
                        'id': n.id,
                        'subTagName': n.subTagName,
                        'nominalPressure': n.nominalPressureRepresentation,
                        'has_nodes': len(n.nodes) > 0 if hasattr(n, 'nodes') and n.nodes else False
                    }
                    for n in (equipment.nozzles if hasattr(equipment, 'nozzles') else [])
                ],
                'attributes': {
                    k: str(v) for k, v in equipment.__dict__.items()
                    if not k.startswith('_') and k not in ['nozzles']
                }
            }

        except Exception as e:
            print(f"    ERROR: {e}")
            baseline[f"{equipment_type}_{tag}"] = {
                'error': str(e),
                'type': 'FAILED'
            }

    # Write to JSON
    output_path = project_root / 'tests' / 'fixtures' / 'baseline' / 'equipment.json'
    with open(output_path, 'w') as f:
        json.dump(baseline, f, indent=2)

    print(f"✅ Equipment baseline saved to {output_path}")
    print(f"   Captured {len([v for v in baseline.values() if v.get('type') != 'FAILED'])} equipment types")

    return baseline


def capture_sfiles_baseline():
    """Capture SFILES conversion baseline patterns."""
    print("\nCapturing SFILES conversion baseline...")

    # Import SFILES conversion tools
    try:
        from src.converters.sfiles_dexpi_mapper import SfilesDexpiMapper
        from src.core.conversion import ConversionEngine
    except ImportError as e:
        print(f"  WARNING: Could not import conversion tools: {e}")
        print(f"  Skipping SFILES baseline capture")
        return {}

    baseline = {}

    # Test patterns
    test_cases = [
        "tank[storage]->pump[centrifugal]",
        "pump[centrifugal]->tank[storage]",
        "tank[storage]->pump[centrifugal]->reactor[vessel]",
        "feed[tank]->P-101[pump]->T-201[reactor]",
        "pump[pump_centrifugal]->heater[heater]->mixer[mixer]",
    ]

    mapper = SfilesDexpiMapper()
    engine = ConversionEngine()

    for i, sfiles_string in enumerate(test_cases):
        print(f"  - Case {i}: {sfiles_string[:50]}...")

        try:
            # Parse SFILES
            sfiles_model = engine.parse_sfiles(sfiles_string)

            # Convert via legacy mapper
            dexpi_model = mapper.sfiles_to_dexpi(sfiles_model)

            # Count equipment
            equipment_count = 0
            if hasattr(dexpi_model, 'conceptualModel') and dexpi_model.conceptualModel:
                if hasattr(dexpi_model.conceptualModel, 'taggedPlantItems'):
                    equipment_count = len(list(dexpi_model.conceptualModel.taggedPlantItems))

            # Count connections
            connection_count = 0
            if hasattr(dexpi_model.conceptualModel, 'pipingNetworkSystems'):
                for pns in dexpi_model.conceptualModel.pipingNetworkSystems:
                    if hasattr(pns, 'segments'):
                        connection_count += len(list(pns.segments))

            baseline[f"case_{i}"] = {
                'input': sfiles_string,
                'equipment_count': equipment_count,
                'connection_count': connection_count,
                'unit_count': len(sfiles_model.units),
                'stream_count': len(sfiles_model.streams)
            }

        except Exception as e:
            print(f"    ERROR: {e}")
            baseline[f"case_{i}"] = {
                'input': sfiles_string,
                'error': str(e),
                'status': 'FAILED'
            }

    # Write to JSON
    output_path = project_root / 'tests' / 'fixtures' / 'baseline' / 'sfiles_conversions.json'
    with open(output_path, 'w') as f:
        json.dump(baseline, f, indent=2)

    print(f"✅ SFILES baseline saved to {output_path}")
    print(f"   Captured {len([v for v in baseline.values() if v.get('status') != 'FAILED'])} conversion patterns")

    return baseline


def main():
    """Main entry point."""
    print("=" * 60)
    print("Phase 1 Migration - Baseline Capture")
    print("=" * 60)
    print()

    # Capture equipment baseline
    equipment_baseline = capture_equipment_baseline()

    # Capture SFILES baseline
    sfiles_baseline = capture_sfiles_baseline()

    print()
    print("=" * 60)
    print("Baseline capture complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Review fixtures in tests/fixtures/baseline/")
    print("2. Commit to git: git add tests/fixtures/baseline/ && git commit -m 'Phase 1 baseline'")
    print("3. Tag baseline: git tag phase1-baseline")
    print("4. Begin migration with confidence - fixtures preserve 'before' state")
    print()

    # Summary
    equipment_success = len([v for v in equipment_baseline.values() if v.get('type') != 'FAILED'])
    sfiles_success = len([v for v in sfiles_baseline.values() if v.get('status') != 'FAILED'])

    print(f"Summary:")
    print(f"  Equipment fixtures: {equipment_success} captured")
    print(f"  SFILES fixtures: {sfiles_success} captured")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
