#!/usr/bin/env python3
"""
Verify Symbol Mappings
Ensures all downloaded NOAKADEXPI symbols match the official Symbols.xlsm mappings
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from visualization.symbols.catalog import SymbolCatalog
# UPDATED: Use new SymbolResolver instead of deprecated DexpiSymbolMapper
from src.core.symbol_resolver import SymbolResolver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SymbolMappingVerifier:
    """Verify symbol mappings against official Symbols.xlsm."""

    # Official mappings from Symbols.xlsm (extracted from Excel)
    OFFICIAL_MAPPINGS = {
        # Pumps
        "PP001A": {"description": "Pump Centrifugal", "grouping": "Pump", "dexpi_class": "CentrifugalPump"},
        "PP002A": {"description": "Pump Diaphragm", "grouping": "Pump", "dexpi_class": "DiaphragmPump"},
        "PP003A": {"description": "Pump Gear", "grouping": "Pump", "dexpi_class": "GearPump"},
        "PP004A": {"description": "Pump Hand", "grouping": "Pump", "dexpi_class": "HandPump"},
        "PP005A": {"description": "Pump Sliding Vane", "grouping": "Pump", "dexpi_class": "SlidingVanePump"},
        "PP006A": {"description": "Pump Liquid Ring", "grouping": "Pump", "dexpi_class": "LiquidRingPump"},
        "PP007A": {"description": "Blower", "grouping": "Equipment", "dexpi_class": "Blower"},
        "PP008A": {"description": "Pump Proportioning", "grouping": "Pump", "dexpi_class": "ProportioningPump"},
        "PP009A": {"description": "Pump Triplex", "grouping": "Pump", "dexpi_class": "TriplexPump"},
        "PP010A": {"description": "Pump Reciprocating", "grouping": "Pump", "dexpi_class": "ReciprocatingPump"},

        # Valves (Manual)
        "PV001A": {"description": "Flange", "grouping": "In-line component", "dexpi_class": "Flange"},
        "PV002A": {"description": "Blind Flange", "grouping": "In-line component", "dexpi_class": "BlindFlange"},
        "PV003A": {"description": "Valve Three Way (Manual Valve)", "grouping": "Valve", "dexpi_class": "ThreeWayValve"},
        "PV004A": {"description": "Valve Four Way (Manual Valve)", "grouping": "Valve", "dexpi_class": "FourWayValve"},
        "PV005A": {"description": "Valve Gate (Manual Valve)", "grouping": "Valve", "dexpi_class": "GateValve"},
        "PV007A": {"description": "Valve Globe (Manual Valve)", "grouping": "Valve", "dexpi_class": "GlobeValve"},
        "PV008A": {"description": "Valve Float (Manual Valve)", "grouping": "Valve", "dexpi_class": "FloatValve"},
        "PV009A": {"description": "Valve Min. Flow And Check", "grouping": "Valve", "dexpi_class": "MinFlowCheckValve"},
        "PV010A": {"description": "Valve Choke", "grouping": "Valve", "dexpi_class": "ChokeValve"},
        "PV011A": {"description": "Not In Use for NOAKA DEXPI", "grouping": "Valve", "dexpi_class": None},

        # Tanks
        "PT001A": {"description": "Not found in main list", "grouping": "Vessel", "dexpi_class": "Tank"},
        "PT002A": {"description": "Pressure Vessel", "grouping": "Vessel", "dexpi_class": "PressureVessel"},
        "PT003A": {"description": "Tank Tower", "grouping": "Vessel", "dexpi_class": "Tower"},
        "PT004A": {"description": "Tank Pressure Quick Open Lid", "grouping": "Vessel", "dexpi_class": "QuickOpenLidTank"},
        "PT005A": {"description": "Tank Dome Roof", "grouping": "Vessel", "dexpi_class": "DomeRoofTank"},

        # Equipment
        "PE001A": {"description": "Concentric Reducer", "grouping": "In-line component", "dexpi_class": "ConcentricReducer"},
        "PE002A": {"description": "Eccentric Reducer", "grouping": "In-line component", "dexpi_class": "EccentricReducer"},
        "PE003A": {"description": "Inline Mixer", "grouping": "In-line component", "dexpi_class": "InlineMixer"},
        "PE010A": {"description": "Exch. Plate", "grouping": "Equipment", "dexpi_class": "PlateHeatExchanger"},
        "PE011A": {"description": "Exch. Fin", "grouping": "Equipment", "dexpi_class": "FinHeatExchanger"},
        "PE020A": {"description": "Drives Type by XX", "grouping": "ConnectedEquipment", "dexpi_class": "Drive"},
        "PE021A": {"description": "Turbine Type by XX", "grouping": "ConnectedEquipment", "dexpi_class": "Turbine"},
        "PE022A": {"description": "Crusher", "grouping": "Equipment", "dexpi_class": "Crusher"},

        # Filters
        "PF001A": {"description": "Flow T. Turbine", "grouping": "In-Line Instrument", "dexpi_class": "FlowTurbine"},
        "PF002A": {"description": "Flow T. Vortex", "grouping": "In-Line Instrument", "dexpi_class": "FlowVortex"},
        "PF003A": {"description": "Flow T. Coriolis", "grouping": "In-Line Instrument", "dexpi_class": "FlowCoriolis"},
        "PF004A": {"description": "Flow T. RotaMeter", "grouping": "In-Line Instrument", "dexpi_class": "FlowRotameter"},
        "PF005A": {"description": "Flow T. Mag", "grouping": "In-Line Instrument", "dexpi_class": "FlowMagnetic"},

        # Separators
        "PS001A": {"description": "Spectacle Blind NO", "grouping": "In-line component", "dexpi_class": "SpectacleBlind"},
        "PS003A": {"description": "Spade", "grouping": "In-line component", "dexpi_class": "Spade"},
    }

    def __init__(self, catalog_path: Path = None):
        """Initialize verifier."""
        if catalog_path is None:
            catalog_path = Path(__file__).parent / "assets"

        self.catalog = SymbolCatalog(catalog_path)
        # UPDATED: Use SymbolResolver instead of deprecated DexpiSymbolMapper
        self.resolver = SymbolResolver()

    def verify_all_mappings(self) -> Dict[str, any]:
        """
        Verify all symbol mappings.

        Returns:
            Verification results
        """
        results = {
            "total_symbols": len(self.catalog.symbols),
            "verified": 0,
            "mismatched": 0,
            "missing_mapping": 0,
            "issues": []
        }

        logger.info(f"Verifying {results['total_symbols']} symbols against official mappings")

        for symbol_id, symbol in self.catalog.symbols.items():
            issue = self.verify_symbol(symbol_id, symbol)
            if issue is None:
                results["verified"] += 1
            else:
                if issue["type"] == "missing":
                    results["missing_mapping"] += 1
                else:
                    results["mismatched"] += 1
                results["issues"].append(issue)

        return results

    def verify_symbol(self, symbol_id: str, symbol) -> Dict[str, any]:
        """
        Verify a single symbol mapping.

        Args:
            symbol_id: Symbol ID
            symbol: Symbol metadata

        Returns:
            Issue description or None if valid
        """
        # Check if symbol exists in official mappings
        if symbol_id not in self.OFFICIAL_MAPPINGS:
            # Check if it's a variation (Detail or Origo)
            base_id = symbol_id.replace("_Detail", "").replace("_Origo", "")
            if base_id in self.OFFICIAL_MAPPINGS:
                # Variation is OK
                return None
            else:
                return {
                    "type": "missing",
                    "symbol_id": symbol_id,
                    "message": f"Symbol {symbol_id} not found in official mappings"
                }

        official = self.OFFICIAL_MAPPINGS[symbol_id]

        # Verify DEXPI class matches
        if official["dexpi_class"] and symbol.dexpi_class != official["dexpi_class"]:
            return {
                "type": "mismatch",
                "symbol_id": symbol_id,
                "field": "dexpi_class",
                "expected": official["dexpi_class"],
                "actual": symbol.dexpi_class,
                "message": f"DEXPI class mismatch for {symbol_id}"
            }

        # Verify description matches (fuzzy)
        if official["description"] and official["description"] != "Not found in main list":
            if official["description"].lower() not in symbol.name.lower() and \
               symbol.name.lower() not in official["description"].lower():
                logger.warning(f"Description mismatch for {symbol_id}: "
                             f"Expected '{official['description']}', Got '{symbol.name}'")

        return None

    def update_catalog_mappings(self):
        """Update catalog with correct mappings from Symbols.xlsm."""
        updated = 0

        for symbol_id, symbol in self.catalog.symbols.items():
            if symbol_id in self.OFFICIAL_MAPPINGS:
                official = self.OFFICIAL_MAPPINGS[symbol_id]

                # Update DEXPI class if needed
                if official["dexpi_class"] and symbol.dexpi_class != official["dexpi_class"]:
                    logger.info(f"Updating {symbol_id} DEXPI class: "
                              f"{symbol.dexpi_class} -> {official['dexpi_class']}")
                    symbol.dexpi_class = official["dexpi_class"]
                    updated += 1

                # Update category if different
                if official["grouping"] != symbol.category:
                    logger.info(f"Updating {symbol_id} category: "
                              f"{symbol.category} -> {official['grouping']}")
                    symbol.category = official["grouping"]
                    updated += 1

        if updated > 0:
            self.catalog.save_catalog()
            logger.info(f"Updated {updated} symbol mappings in catalog")

        return updated

    def generate_mapping_report(self) -> str:
        """
        Generate detailed mapping report.

        Returns:
            Report text
        """
        results = self.verify_all_mappings()

        report = ["=" * 60]
        report.append("SYMBOL MAPPING VERIFICATION REPORT")
        report.append("=" * 60)
        report.append("")

        # Summary
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Symbols: {results['total_symbols']}")
        report.append(f"Verified OK: {results['verified']}")
        report.append(f"Mismatched: {results['mismatched']}")
        report.append(f"Missing Mapping: {results['missing_mapping']}")
        report.append("")

        # Issues
        if results['issues']:
            report.append("ISSUES FOUND")
            report.append("-" * 40)
            for issue in results['issues']:
                report.append(f"\nSymbol: {issue['symbol_id']}")
                report.append(f"  Type: {issue['type']}")
                report.append(f"  Message: {issue['message']}")
                if 'expected' in issue:
                    report.append(f"  Expected: {issue['expected']}")
                    report.append(f"  Actual: {issue['actual']}")
        else:
            report.append("✓ All symbols correctly mapped!")

        # Symbol inventory
        report.append("")
        report.append("SYMBOL INVENTORY BY CATEGORY")
        report.append("-" * 40)

        categories = {}
        for symbol in self.catalog.symbols.values():
            if symbol.category not in categories:
                categories[symbol.category] = []
            categories[symbol.category].append(symbol.id)

        for category, symbols in sorted(categories.items()):
            report.append(f"\n{category}: {len(symbols)} symbols")
            for symbol_id in sorted(symbols)[:5]:  # Show first 5
                report.append(f"  - {symbol_id}")
            if len(symbols) > 5:
                report.append(f"  ... and {len(symbols) - 5} more")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


def main():
    """Main verification function."""
    verifier = SymbolMappingVerifier()

    # Generate report
    report = verifier.generate_mapping_report()
    print(report)

    # Save report
    report_path = Path(__file__).parent / "assets" / "mapping_verification_report.txt"
    report_path.write_text(report)
    print(f"\nReport saved to: {report_path}")

    # Update mappings if needed
    print("\nUpdating catalog with official mappings...")
    updated = verifier.update_catalog_mappings()
    print(f"Updated {updated} mappings")

    # Verify resolver class
    print("\nVerifying SymbolResolver...")
    resolver = SymbolResolver()

    test_classes = [
        "CentrifugalPump",
        "GateValve",
        "Tank",
        "PlateHeatExchanger",
        "Agitator"
    ]

    for dexpi_class in test_classes:
        # UPDATED: Use new SymbolResolver API
        symbol = resolver.get_by_dexpi_class(dexpi_class)
        symbol_id = symbol.symbol_id if symbol else None
        print(f"  {dexpi_class} -> {symbol_id}")


if __name__ == "__main__":
    main()