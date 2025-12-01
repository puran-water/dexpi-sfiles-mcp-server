#!/usr/bin/env python3
"""
Generate registrations for ALL 272 pyDEXPI classes across all categories.

Categories:
- Equipment: 159 classes
- Piping: 79 classes
- Instrumentation: 34 classes
"""

import sys
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.components import get_registry, ComponentType

# Reuse equipment generation classes
sys.path.append(str(Path(__file__).parent))
from generate_equipment_registrations import (
    EquipmentCategorizer, SFILESAliasGenerator, SymbolMapper, NozzleDefaults
)


class PipingCategorizer:
    """Categorize piping components."""

    CATEGORY_RULES = {
        'valve': 'VALVE',
        'pipe': 'PIPE',
        'flange': 'CONNECTION',
        'connection': 'CONNECTION',
        'coupling': 'CONNECTION',
        'flow': 'FLOW_MEASUREMENT',
        'meter': 'FLOW_MEASUREMENT',
        'orifice': 'FLOW_MEASUREMENT',
        'venturi': 'FLOW_MEASUREMENT',
        'strainer': 'FILTRATION',
        'filter': 'FILTRATION',
        'flame': 'SAFETY',
        'safety': 'SAFETY',
        'relief': 'SAFETY',
        'rupture': 'SAFETY',
        'network': 'STRUCTURE',
        'system': 'STRUCTURE',
        'segment': 'STRUCTURE',
    }

    @classmethod
    def categorize(cls, class_name: str) -> str:
        """Determine piping category."""
        name_lower = class_name.lower()

        for keyword, category in cls.CATEGORY_RULES.items():
            if keyword in name_lower:
                return category

        return 'OTHER_PIPING'


class InstrumentationCategorizer:
    """Categorize instrumentation components."""

    CATEGORY_RULES = {
        'actuating': 'ACTUATING',
        'actuator': 'ACTUATING',
        'positioner': 'ACTUATING',
        'signal': 'SIGNAL',
        'sensing': 'SENSING',
        'sensor': 'SENSING',
        'transmitter': 'TRANSMITTER',
        'detector': 'DETECTOR',
        'control': 'CONTROL',
        'measuring': 'MEASUREMENT',
        'primary': 'MEASUREMENT',
        'loop': 'CONTROL_LOOP',
        'frequency': 'CONVERTER',
    }

    @classmethod
    def categorize(cls, class_name: str) -> str:
        """Determine instrumentation category."""
        name_lower = class_name.lower()

        for keyword, category in cls.CATEGORY_RULES.items():
            if keyword in name_lower:
                return category

        return 'OTHER_INSTRUMENTATION'


class PipingAliasGenerator:
    """Generate SFILES aliases for piping components."""

    # Valve families
    VALVE_FAMILIES = {
        'ball_valve': ['BallValve', 'AngleBallValve'],
        'globe_valve': ['GlobeValve', 'AngleGlobeValve', 'GlobeCheckValve'],
        'plug_valve': ['PlugValve', 'AnglePlugValve'],
        'check_valve': ['CheckValve', 'SwingCheckValve', 'GlobeCheckValve', 'CustomCheckValve'],
        'safety_valve': ['SafetyValveOrFitting', 'SpringLoadedGlobeSafetyValve', 'SpringLoadedAngleGlobeSafetyValve', 'CustomSafetyValveOrFitting'],
        'operated_valve': ['OperatedValve', 'CustomOperatedValve'],
    }

    @classmethod
    def to_snake_case(cls, name: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @classmethod
    def generate_alias(cls, class_name: str, category: str) -> Tuple[str, bool, Optional[str]]:
        """
        Generate SFILES alias for piping component.

        Returns:
            Tuple of (alias, is_primary, family)
        """
        # Valves get "valve_" prefix
        if category == 'VALVE':
            # Check if primary in a family
            for family, members in cls.VALVE_FAMILIES.items():
                if class_name in members:
                    if class_name == members[0]:
                        return (family, True, family)
                    else:
                        # Generate variant alias
                        variant = cls.to_snake_case(class_name)
                        return (variant, False, family)

            # Standalone valve
            return (cls.to_snake_case(class_name), False, None)

        # Non-valves use simple snake_case
        return (cls.to_snake_case(class_name), False, None)

    @classmethod
    def get_family(cls, class_name: str) -> Optional[str]:
        """Get the family alias if this class belongs to one."""
        for family, members in cls.VALVE_FAMILIES.items():
            if class_name in members:
                return family
        return None


class InstrumentationAliasGenerator:
    """Generate SFILES aliases for instrumentation."""

    # Instrumentation families
    FAMILIES = {
        'actuator': ['ActuatingFunction', 'ActuatingSystem', 'ControlledActuator'],
        'actuator_electric': ['ActuatingElectricalFunction', 'ActuatingElectricalSystem', 'ActuatingElectricalLocation'],
        'transmitter': ['Transmitter', 'FlowDetector'],
        'signal_connector': ['SignalOffPageConnector', 'SignalOffPageConnectorReference', 'SignalOffPageConnectorObjectReference', 'SignalOffPageConnectorReferenceByNumber'],
        'flow_signal_connector': ['FlowInSignalOffPageConnector', 'FlowOutSignalOffPageConnector'],
    }

    @classmethod
    def to_snake_case(cls, name: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @classmethod
    def generate_alias(cls, class_name: str) -> Tuple[str, bool, Optional[str]]:
        """Generate SFILES alias for instrumentation."""
        # Check families
        for family, members in cls.FAMILIES.items():
            if class_name in members:
                if class_name == members[0]:
                    return (family, True, family)
                else:
                    return (cls.to_snake_case(class_name), False, family)

        # Default snake_case
        return (cls.to_snake_case(class_name), False, None)


def generate_all_registrations():
    """Generate registrations for all 272 classes."""
    registry = get_registry()

    all_registrations = {
        'equipment': [],
        'piping': [],
        'instrumentation': []
    }

    # Equipment (reuse existing logic)
    from generate_equipment_registrations import generate_registration_data
    all_registrations['equipment'] = generate_registration_data()

    # Instantiate SymbolMapper for piping and instrumentation (Phase 3 Pass 1)
    symbol_mapper = SymbolMapper()

    # Piping - get class names from ComponentRegistry
    piping_defs = registry.get_all_by_type(ComponentType.PIPING)
    piping_classes = [d.dexpi_class.__name__ for d in piping_defs]
    for class_name in sorted(piping_classes):
        category = PipingCategorizer.categorize(class_name)
        alias, is_primary, family = PipingAliasGenerator.generate_alias(class_name, category)

        # Symbol mapping using SymbolMapper (Phase 3 Pass 1)
        symbol_id = symbol_mapper.map_symbol(class_name, category, 'piping')

        # Connection defaults
        if category == 'VALVE':
            connection_count = 2  # Inlet/outlet
        elif category == 'PIPE':
            connection_count = 2  # Start/end
        elif category == 'CONNECTION':
            connection_count = 2  # Two sides
        elif category == 'FLOW_MEASUREMENT':
            connection_count = 2  # Inline
        elif category == 'STRUCTURE':
            connection_count = 0  # Abstract
        else:
            connection_count = 2  # Default

        display_name = re.sub('([A-Z])', r' \1', class_name).strip()

        all_registrations['piping'].append({
            'class_name': class_name,
            'sfiles_alias': alias,
            'is_primary': is_primary,
            'family': family or '',
            'category': category,
            'symbol_id': symbol_id,
            'connection_count': connection_count,
            'display_name': display_name,
        })

    # Instrumentation - get class names from ComponentRegistry
    inst_defs = registry.get_all_by_type(ComponentType.INSTRUMENTATION)
    inst_classes = [d.dexpi_class.__name__ for d in inst_defs]
    for class_name in sorted(inst_classes):
        category = InstrumentationCategorizer.categorize(class_name)
        alias, is_primary, family = InstrumentationAliasGenerator.generate_alias(class_name)

        # Symbol mapping using SymbolMapper (Phase 3 Pass 1)
        symbol_id = symbol_mapper.map_symbol(class_name, category, 'instrumentation')

        # Connection defaults
        if category in ['ACTUATING', 'CONTROL']:
            connection_count = 1  # Control output
        elif category in ['SIGNAL', 'MEASUREMENT', 'SENSING']:
            connection_count = 2  # Signal in/out
        else:
            connection_count = 1  # Default

        display_name = re.sub('([A-Z])', r' \1', class_name).strip()

        all_registrations['instrumentation'].append({
            'class_name': class_name,
            'sfiles_alias': alias,
            'is_primary': is_primary,
            'family': family or '',
            'category': category,
            'symbol_id': symbol_id,
            'connection_count': connection_count,
            'display_name': display_name,
        })

    return all_registrations


def write_csv_by_category(all_registrations: Dict, output_dir: Path):
    """Write CSV files for each category."""
    for category, registrations in all_registrations.items():
        csv_path = output_dir / f'{category}_registrations.csv'

        # Field names depend on category
        if category == 'equipment':
            fieldnames = ['class_name', 'sfiles_alias', 'is_primary', 'family', 'category', 'symbol_id', 'nozzle_count', 'display_name']
        else:
            fieldnames = ['class_name', 'sfiles_alias', 'is_primary', 'family', 'category', 'symbol_id', 'connection_count', 'display_name']

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(registrations)

        print(f"✓ {category.upper()} CSV written to {csv_path} ({len(registrations)} classes)")


def print_comprehensive_summary(all_registrations: Dict):
    """Print comprehensive summary."""
    print("\n" + "="*70)
    print("COMPLETE PYDEXPI REGISTRATION SUMMARY")
    print("="*70)

    total = sum(len(regs) for regs in all_registrations.values())
    print(f"\nTotal classes registered: {total}")

    for category, registrations in sorted(all_registrations.items()):
        print(f"\n{category.upper()}: {len(registrations)} classes")

        # Count by category
        categories = {}
        for reg in registrations:
            cat = reg['category']
            categories[cat] = categories.get(cat, 0) + 1

        print(f"  By subcategory:")
        for cat, count in sorted(categories.items()):
            print(f"    {cat}: {count}")

        # Count families
        families = {}
        for reg in registrations:
            if reg['family']:
                families[reg['family']] = families.get(reg['family'], 0) + 1

        if families:
            print(f"  Families defined: {len(families)}")
            top_families = sorted(families.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"  Top families:")
            for family, count in top_families:
                print(f"    {family}: {count} variants")

    print("\n" + "="*70)
    print("✓ COMPLETE REGISTRATION GENERATION SUCCESSFUL!")
    print("="*70)
    print(f"\nAll {total}/272 pyDEXPI classes now have registration data.")
    print(f"\nNext: Phase 2 integration into core layer (8-10 hours)")


if __name__ == '__main__':
    print("Generating registrations for ALL 272 pyDEXPI classes...")
    print("="*70)

    # Generate data
    all_registrations = generate_all_registrations()

    # Output directory
    output_dir = Path(__file__).parent.parent / 'docs' / 'generated'
    output_dir.mkdir(exist_ok=True)

    # Write CSVs
    write_csv_by_category(all_registrations, output_dir)

    # Print summary
    print_comprehensive_summary(all_registrations)
