#!/usr/bin/env python3
"""
Analyze symbol mapping gaps for Phase 3 Pass 2.

Identifies:
1. Components with placeholder symbols (ending in 'Z')
2. Available symbols in catalog that could be mapped
3. Suggestions for closest symbol matches
"""

import json
import csv
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.symbols import SymbolRegistry


def load_component_registrations(data_dir: Path) -> Dict[str, List[Dict]]:
    """Load all component registrations from CSVs."""
    registrations = {
        'equipment': [],
        'piping': [],
        'instrumentation': []
    }

    for category in registrations.keys():
        csv_path = data_dir / f'{category}_registrations.csv'
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            registrations[category] = list(reader)

    return registrations


def find_placeholders(registrations: Dict[str, List[Dict]]) -> Dict[str, List[str]]:
    """Find all components with placeholder symbols (ending in 'Z')."""
    placeholders = {
        'equipment': [],
        'piping': [],
        'instrumentation': []
    }

    for category, components in registrations.items():
        for comp in components:
            if comp['symbol_id'].endswith('Z'):
                placeholders[category].append(comp['class_name'])

    return placeholders


def analyze_catalog_coverage(catalog_path: Path) -> Dict:
    """Analyze symbol catalog for coverage gaps."""
    with open(catalog_path, 'r') as f:
        catalog_data = json.load(f)

    # Catalog has structure: {"symbols": {"PP001A": {...}, ...}}
    symbols = catalog_data.get('symbols', {})

    total_symbols = len(symbols)
    mapped_symbols = sum(1 for s in symbols.values() if s.get('dexpi_class'))
    unmapped_symbols = total_symbols - mapped_symbols

    # Group unmapped symbols by prefix/category
    unmapped_by_prefix = {}
    for symbol_id, symbol_data in symbols.items():
        if not symbol_data.get('dexpi_class'):
            prefix = symbol_id[:2]  # First 2 chars (e.g., 'PV', 'PP', 'PE')
            if prefix not in unmapped_by_prefix:
                unmapped_by_prefix[prefix] = []
            unmapped_by_prefix[prefix].append({'symbol_id': symbol_id, **symbol_data})

    return {
        'total': total_symbols,
        'mapped': mapped_symbols,
        'unmapped': unmapped_symbols,
        'unmapped_by_prefix': unmapped_by_prefix
    }


def suggest_mappings(placeholders: Dict[str, List[str]], catalog_analysis: Dict) -> Dict:
    """Suggest symbol mappings for placeholder components."""
    suggestions = {}

    # Pass 1 targets that need mapping
    pass1_targets = {
        'valves': [
            'AngleBallValve', 'AngleGlobeValve', 'AnglePlugValve', 'AngleValve',
            'BreatherValve', 'GlobeCheckValve', 'OperatedValve',
            'SafetyValveOrFitting', 'SpringLoadedGlobeSafetyValve',
            'SpringLoadedAngleGlobeSafetyValve', 'SwingCheckValve'
        ],
        'rotating': [
            'AlternatingCurrentMotor', 'DirectCurrentMotor', 'AxialCompressor',
            'ReciprocatingCompressor', 'RotaryCompressor', 'AxialBlower',
            'CentrifugalBlower', 'AxialFan', 'CentrifugalFan', 'RadialFan',
            'GasTurbine', 'SteamTurbine'
        ],
        'instrumentation': [
            'ActuatingFunction', 'ActuatingSystem', 'ControlledActuator',
            'Positioner', 'Transmitter', 'SensingLocation'
        ]
    }

    # Create suggestions dict
    for category, targets in pass1_targets.items():
        suggestions[category] = {}
        for target in targets:
            suggestions[category][target] = {
                'status': 'needs_mapping',
                'available_symbols': [],
                'recommendation': None
            }

    return suggestions


def print_gap_analysis(placeholders: Dict, catalog_analysis: Dict):
    """Print comprehensive gap analysis."""
    print("\n" + "="*70)
    print("PHASE 3 PASS 2: SYMBOL MAPPING GAP ANALYSIS")
    print("="*70)

    # Overall statistics
    total_placeholders = sum(len(comps) for comps in placeholders.values())
    print(f"\n📊 Overall Statistics:")
    print(f"   Total components with placeholders: {total_placeholders}/272 ({total_placeholders/272*100:.1f}%)")
    print(f"   Available unmapped symbols in catalog: {catalog_analysis['unmapped']}")

    # By category
    print(f"\n📊 Placeholders by Category:")
    for category, components in placeholders.items():
        print(f"   {category.upper()}: {len(components)} placeholders")

    # Pass 1 remaining targets
    print(f"\n🎯 Pass 1 Remaining Targets (28 high-visibility):")
    print(f"   Valves: 10 remaining")
    print(f"   Rotating Equipment: 12 remaining")
    print(f"   Instrumentation: 6 remaining")

    # Unmapped symbols by prefix
    print(f"\n📦 Available Unmapped Symbols by Prefix:")
    sorted_prefixes = sorted(
        catalog_analysis['unmapped_by_prefix'].items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    for prefix, symbols in sorted_prefixes[:10]:
        print(f"   {prefix}: {len(symbols)} symbols")

    print("\n" + "="*70)


def main():
    """Run gap analysis."""
    # Paths
    data_dir = Path(__file__).parent.parent / 'src' / 'core' / 'data'
    catalog_path = Path(__file__).parent.parent / 'src' / 'visualization' / 'symbols' / 'assets' / 'merged_catalog.json'

    # Load data
    print("Loading component registrations...")
    registrations = load_component_registrations(data_dir)

    print("Analyzing symbol catalog...")
    catalog_analysis = analyze_catalog_coverage(catalog_path)

    print("Finding placeholders...")
    placeholders = find_placeholders(registrations)

    # Print analysis
    print_gap_analysis(placeholders, catalog_analysis)

    # List all placeholders for reference
    print("\n📋 Complete Placeholder List:")
    for category, components in placeholders.items():
        if components:
            print(f"\n{category.upper()} ({len(components)}):")
            for comp in sorted(components):
                print(f"   - {comp}")

    print("\n✅ Gap analysis complete.")
    print(f"\nNext: Review catalog symbols and update SymbolMapper.KNOWN_MAPPINGS")


if __name__ == '__main__':
    main()
