#!/usr/bin/env python3
"""
Suggest symbol mappings for Phase 3 Pass 2.

Analyzes component names and symbol names to find matches.
"""

import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple
from difflib import SequenceMatcher


def load_catalog(catalog_path: Path) -> Dict:
    """Load merged catalog."""
    with open(catalog_path, 'r') as f:
        catalog_data = json.load(f)
    return catalog_data.get('symbols', {})


def load_placeholders(data_dir: Path) -> Dict[str, Dict]:
    """Load components with placeholder symbols."""
    placeholders = {}

    for category in ['equipment', 'piping', 'instrumentation']:
        csv_path = data_dir / f'{category}_registrations.csv'
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['symbol_id'].endswith('Z'):
                    placeholders[row['class_name']] = {
                        'category': category,
                        'symbol_id': row['symbol_id'],
                        'csv_category': row['category']
                    }

    return placeholders


def normalize_name(name: str) -> str:
    """Normalize name for comparison."""
    # Convert CamelCase to space-separated
    name = re.sub('([A-Z])', r' \1', name).strip()
    # Remove special characters, lowercase
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name).lower()
    return name


def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, normalize_name(str1), normalize_name(str2)).ratio()


def suggest_matches(component_name: str, symbols: Dict, prefix_filter: str = None) -> List[Tuple]:
    """Suggest symbol matches for a component."""
    suggestions = []

    for symbol_id, symbol_data in symbols.items():
        # Filter by prefix if specified
        if prefix_filter and not symbol_id.startswith(prefix_filter):
            continue

        # Skip if already mapped to a DEXPI class
        if symbol_data.get('dexpi_class'):
            continue

        # Calculate similarity with symbol name
        symbol_name = symbol_data.get('name', '')
        similarity = calculate_similarity(component_name, symbol_name)

        if similarity > 0.3:  # Threshold for consideration
            suggestions.append((
                symbol_id,
                symbol_name,
                similarity,
                symbol_data.get('category', 'Unknown')
            ))

    # Sort by similarity
    suggestions.sort(key=lambda x: x[2], reverse=True)
    return suggestions[:5]  # Top 5


def get_prefix_for_category(csv_category: str, component_category: str) -> str:
    """Get appropriate symbol prefix for component category."""
    # Equipment categories
    if component_category == 'equipment':
        if 'ROTATING' in csv_category or 'PUMP' in csv_category or 'COMPRESSOR' in csv_category:
            return 'PP'  # Pumps/Prime movers
        elif 'HEAT' in csv_category or 'VESSEL' in csv_category:
            return 'PE'  # Process equipment
        elif 'SEPARATION' in csv_category:
            return 'PS'  # Separators
        elif 'TRANSPORT' in csv_category:
            return 'PC'  # Conveyors
        else:
            return 'PE'  # Default equipment

    # Piping categories
    elif component_category == 'piping':
        if 'VALVE' in csv_category:
            return 'PV'  # Valves
        elif 'FLOW_MEASUREMENT' in csv_category:
            return 'PF'  # Flow measurement
        elif 'FILTRATION' in csv_category:
            return 'PF'  # Filters
        else:
            return 'PP'  # Piping

    # Instrumentation
    elif component_category == 'instrumentation':
        return 'IM'  # Instrumentation

    return 'PE'  # Default


def main():
    """Generate mapping suggestions."""
    # Paths
    data_dir = Path(__file__).parent.parent / 'src' / 'core' / 'data'
    catalog_path = Path(__file__).parent.parent / 'src' / 'visualization' / 'symbols' / 'assets' / 'merged_catalog.json'

    print("Loading catalog and placeholders...")
    catalog = load_catalog(catalog_path)
    placeholders = load_placeholders(data_dir)

    print(f"\nFound {len(placeholders)} components with placeholders")
    print(f"Available symbols in catalog: {len(catalog)}")

    # Pass 1 remaining targets (high priority)
    pass1_targets = {
        'AngleBallValve', 'AngleGlobeValve', 'AnglePlugValve', 'AngleValve',
        'BreatherValve', 'GlobeCheckValve', 'OperatedValve',
        'SafetyValveOrFitting', 'SpringLoadedGlobeSafetyValve',
        'SpringLoadedAngleGlobeSafetyValve', 'SwingCheckValve',
        'AlternatingCurrentMotor', 'DirectCurrentMotor', 'AxialCompressor',
        'ReciprocatingCompressor', 'RotaryCompressor', 'AxialBlower',
        'CentrifugalBlower', 'AxialFan', 'CentrifugalFan', 'RadialFan',
        'GasTurbine', 'SteamTurbine',
        'ActuatingFunction', 'ActuatingSystem', 'ControlledActuator',
        'Positioner', 'Transmitter', 'SensingLocation'
    }

    print("\n" + "="*70)
    print("PASS 1 TARGET MAPPING SUGGESTIONS")
    print("="*70)

    pass1_suggestions = {}
    for component in sorted(pass1_targets):
        if component in placeholders:
            info = placeholders[component]
            prefix = get_prefix_for_category(info['csv_category'], info['category'])

            suggestions = suggest_matches(component, catalog, prefix)

            if suggestions:
                pass1_suggestions[component] = suggestions
                print(f"\n{component} (category: {info['csv_category']}, prefix: {prefix}):")
                for symbol_id, symbol_name, similarity, cat in suggestions:
                    print(f"  → {symbol_id:20s} | {symbol_name:40s} | {similarity:.2f} | {cat}")
            else:
                print(f"\n{component}: No good matches found (will need fallback)")

    # Generate Python dict output for KNOWN_MAPPINGS
    print("\n" + "="*70)
    print("SUGGESTED KNOWN_MAPPINGS ADDITIONS")
    print("="*70)
    print("\n# Add to SymbolMapper.KNOWN_MAPPINGS:")
    print("\nKNOWN_MAPPINGS = {")
    print("    # ... existing mappings ...")
    print("\n    # Phase 3 Pass 2: Remaining Pass 1 targets")

    for component in sorted(pass1_targets):
        if component in pass1_suggestions and pass1_suggestions[component]:
            best_match = pass1_suggestions[component][0]
            print(f"    '{component}': '{best_match[0]}',  # {best_match[1]} (similarity: {best_match[2]:.2f})")

    print("}\n")

    # Save detailed suggestions to JSON
    output_path = Path(__file__).parent.parent / 'docs' / 'generated' / 'symbol_mapping_suggestions.json'
    output_path.parent.mkdir(exist_ok=True)

    suggestions_data = {
        'pass1_targets': {},
        'all_placeholders': {}
    }

    for component, suggestions in pass1_suggestions.items():
        suggestions_data['pass1_targets'][component] = [
            {
                'symbol_id': s[0],
                'symbol_name': s[1],
                'similarity': s[2],
                'category': s[3]
            }
            for s in suggestions
        ]

    with open(output_path, 'w') as f:
        json.dump(suggestions_data, f, indent=2)

    print(f"✅ Detailed suggestions saved to: {output_path}")


if __name__ == '__main__':
    main()
