#!/usr/bin/env python3
"""
Merge NOAKADEXPI and DISCDEXPI Symbol Libraries
Tracks provenance and handles duplicates intelligently
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SymbolProvenance:
    """Track symbol source and version."""
    source_repo: str  # "NOAKADEXPI" or "DISCDEXPI"
    commit_sha: Optional[str] = None
    modified_at: Optional[str] = None
    file_hash: Optional[str] = None
    is_unique_to_source: bool = False


@dataclass
class MergedSymbol:
    """Symbol with provenance tracking."""
    id: str
    name: str
    category: str
    dexpi_class: Optional[str]
    source_file: str
    provenance: SymbolProvenance
    metadata: Dict = None


class SymbolLibraryMerger:
    """Merge NOAKA and DISC symbol libraries with intelligent deduplication."""

    def __init__(self, base_path: Path = None):
        """Initialize merger."""
        if base_path is None:
            base_path = Path(__file__).parent / "assets"

        self.base_path = base_path
        self.noaka_path = base_path / "NOAKADEXPI"
        self.disc_path = base_path / "DISCDEXPI"
        self.merged_path = base_path / "MERGED"

        # Track symbols by ID
        self.noaka_symbols: Dict[str, MergedSymbol] = {}
        self.disc_symbols: Dict[str, MergedSymbol] = {}
        self.merged_symbols: Dict[str, MergedSymbol] = {}

    def get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_git_info(self, repo_path: Path) -> Dict[str, str]:
        """Get git commit info for a repository."""
        try:
            # For cloned repos
            if (repo_path.parent / ".git").exists():
                cwd = repo_path.parent
            else:
                # Assume it's from a specific commit
                cwd = None

            if cwd:
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%H %ai"],
                    capture_output=True,
                    text=True,
                    cwd=cwd
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(" ", 1)
                    return {
                        "commit_sha": parts[0][:8],
                        "modified_at": parts[1] if len(parts) > 1 else None
                    }
        except Exception as e:
            logger.debug(f"Could not get git info: {e}")

        return {"commit_sha": None, "modified_at": None}

    def scan_repository(self, repo_path: Path, repo_name: str) -> Dict[str, MergedSymbol]:
        """Scan a repository for symbols."""
        symbols = {}

        if not repo_path.exists():
            logger.warning(f"Repository path does not exist: {repo_path}")
            return symbols

        git_info = self.get_git_info(repo_path)

        # Scan all SVG files
        for svg_path in repo_path.rglob("*.svg"):
            # Extract symbol ID from filename
            symbol_id = svg_path.stem

            # Determine category from path
            if "Detail" in str(svg_path):
                category = "Detail"
                base_id = symbol_id.replace("_Detail", "")
            elif "Origo" in str(svg_path):
                category = "Origo"
                base_id = symbol_id.replace("_Origo", "")
            else:
                category = self._guess_category(symbol_id)
                base_id = symbol_id

            # Create symbol entry
            symbol = MergedSymbol(
                id=symbol_id,
                name=symbol_id,  # Will be enriched from Excel later
                category=category,
                dexpi_class=None,  # Will be mapped later
                source_file=str(svg_path.relative_to(self.base_path)),
                provenance=SymbolProvenance(
                    source_repo=repo_name,
                    commit_sha=git_info.get("commit_sha"),
                    modified_at=git_info.get("modified_at"),
                    file_hash=self.get_file_hash(svg_path)
                )
            )

            symbols[symbol_id] = symbol

        logger.info(f"Found {len(symbols)} symbols in {repo_name}")
        return symbols

    def _guess_category(self, symbol_id: str) -> str:
        """Guess category from symbol ID prefix."""
        prefix_map = {
            "PP": "Pumps",
            "PV": "Valves",
            "PT": "Tanks",
            "PE": "Equipment",
            "PF": "Filters",
            "PS": "Separators",
            "IM": "Instrumentation",
            "ND": "Annotations",
            "LZ": "Special"
        }

        prefix = symbol_id[:2] if len(symbol_id) >= 2 else ""
        return prefix_map.get(prefix, "Unknown")

    def merge_libraries(self) -> Dict[str, MergedSymbol]:
        """Merge NOAKA and DISC libraries with deduplication."""

        # Scan both repositories
        self.noaka_symbols = self.scan_repository(self.noaka_path, "NOAKADEXPI")
        self.disc_symbols = self.scan_repository(self.disc_path, "DISCDEXPI")

        # Find unique symbols
        noaka_only = set(self.noaka_symbols.keys()) - set(self.disc_symbols.keys())
        disc_only = set(self.disc_symbols.keys()) - set(self.noaka_symbols.keys())
        both = set(self.noaka_symbols.keys()) & set(self.disc_symbols.keys())

        logger.info(f"Unique to NOAKA: {len(noaka_only)}")
        logger.info(f"Unique to DISC: {len(disc_only)}")
        logger.info(f"In both: {len(both)}")

        # Process unique symbols
        for symbol_id in noaka_only:
            symbol = self.noaka_symbols[symbol_id]
            symbol.provenance.is_unique_to_source = True
            self.merged_symbols[symbol_id] = symbol

        for symbol_id in disc_only:
            symbol = self.disc_symbols[symbol_id]
            symbol.provenance.is_unique_to_source = True
            self.merged_symbols[symbol_id] = symbol

        # Process duplicates - prefer DISC as it's more recent
        for symbol_id in both:
            noaka_sym = self.noaka_symbols[symbol_id]
            disc_sym = self.disc_symbols[symbol_id]

            # Compare file hashes
            if noaka_sym.provenance.file_hash == disc_sym.provenance.file_hash:
                # Files are identical, use DISC for consistency
                self.merged_symbols[symbol_id] = disc_sym
                logger.debug(f"{symbol_id}: Identical in both, using DISC")
            else:
                # Files differ, prefer DISC but log difference
                self.merged_symbols[symbol_id] = disc_sym
                logger.info(f"{symbol_id}: Different versions, using DISC (newer)")

        return self.merged_symbols

    def create_merged_catalog(self) -> Dict:
        """Create catalog with all merged symbols."""
        catalog = {
            "version": "2.0",
            "created_at": datetime.now().isoformat(),
            "statistics": {
                "total_symbols": len(self.merged_symbols),
                "noaka_unique": sum(1 for s in self.merged_symbols.values()
                                  if s.provenance.source_repo == "NOAKADEXPI"
                                  and s.provenance.is_unique_to_source),
                "disc_unique": sum(1 for s in self.merged_symbols.values()
                                 if s.provenance.source_repo == "DISCDEXPI"
                                 and s.provenance.is_unique_to_source),
                "shared": sum(1 for s in self.merged_symbols.values()
                            if not s.provenance.is_unique_to_source)
            },
            "symbols": {}
        }

        # Add all symbols
        for symbol_id, symbol in self.merged_symbols.items():
            catalog["symbols"][symbol_id] = {
                "id": symbol.id,
                "name": symbol.name,
                "category": symbol.category,
                "dexpi_class": symbol.dexpi_class,
                "source_file": symbol.source_file,
                "provenance": asdict(symbol.provenance),
                "metadata": symbol.metadata or {}
            }

        return catalog

    def save_merged_catalog(self, output_path: Path = None):
        """Save merged catalog to JSON."""
        if output_path is None:
            output_path = self.base_path / "merged_catalog.json"

        catalog = self.create_merged_catalog()

        with open(output_path, 'w') as f:
            json.dump(catalog, f, indent=2)

        logger.info(f"Saved merged catalog to {output_path}")
        logger.info(f"Total symbols: {catalog['statistics']['total_symbols']}")
        logger.info(f"NOAKA unique: {catalog['statistics']['noaka_unique']}")
        logger.info(f"DISC unique: {catalog['statistics']['disc_unique']}")
        logger.info(f"Shared: {catalog['statistics']['shared']}")

    def generate_difference_report(self) -> str:
        """Generate detailed difference report."""
        report = []
        report.append("=" * 60)
        report.append("SYMBOL LIBRARY MERGE REPORT")
        report.append("=" * 60)
        report.append("")

        # Overall statistics
        report.append("STATISTICS")
        report.append("-" * 40)
        report.append(f"NOAKADEXPI symbols: {len(self.noaka_symbols)}")
        report.append(f"DISCDEXPI symbols: {len(self.disc_symbols)}")
        report.append(f"Merged total: {len(self.merged_symbols)}")
        report.append("")

        # Unique to each source
        noaka_only = [s for s in self.merged_symbols.values()
                     if s.provenance.source_repo == "NOAKADEXPI"
                     and s.provenance.is_unique_to_source]
        disc_only = [s for s in self.merged_symbols.values()
                    if s.provenance.source_repo == "DISCDEXPI"
                    and s.provenance.is_unique_to_source]

        if noaka_only:
            report.append(f"UNIQUE TO NOAKADEXPI ({len(noaka_only)} symbols)")
            report.append("-" * 40)
            for symbol in sorted(noaka_only, key=lambda s: s.id)[:20]:
                report.append(f"  - {symbol.id} ({symbol.category})")
            if len(noaka_only) > 20:
                report.append(f"  ... and {len(noaka_only) - 20} more")
            report.append("")

        if disc_only:
            report.append(f"UNIQUE TO DISCDEXPI ({len(disc_only)} symbols)")
            report.append("-" * 40)
            for symbol in sorted(disc_only, key=lambda s: s.id)[:20]:
                report.append(f"  - {symbol.id} ({symbol.category})")
            if len(disc_only) > 20:
                report.append(f"  ... and {len(disc_only) - 20} more")
            report.append("")

        # Category breakdown
        report.append("CATEGORY BREAKDOWN")
        report.append("-" * 40)
        categories = {}
        for symbol in self.merged_symbols.values():
            if symbol.category not in categories:
                categories[symbol.category] = []
            categories[symbol.category].append(symbol.id)

        for category in sorted(categories.keys()):
            report.append(f"{category}: {len(categories[category])} symbols")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


def main():
    """Main merge function."""
    merger = SymbolLibraryMerger()

    # Merge libraries
    merger.merge_libraries()

    # Save catalog
    merger.save_merged_catalog()

    # Generate report
    report = merger.generate_difference_report()
    print(report)

    # Save report
    report_path = Path(__file__).parent / "assets" / "merge_report.txt"
    report_path.write_text(report)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()