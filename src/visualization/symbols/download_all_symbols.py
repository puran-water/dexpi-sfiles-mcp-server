#!/usr/bin/env python3
"""
Download ALL NOAKADEXPI Symbols
Downloads all 289 symbols from the repository including variations
"""

import logging
import requests
import json
from pathlib import Path
from typing import Dict, List
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompleteNOAKADEXPIDownloader:
    """Download ALL symbols from NOAKADEXPI repository."""

    REPO_OWNER = "equinor"
    REPO_NAME = "NOAKADEXPI"
    API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/Symbols"
    RAW_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main"

    def __init__(self, output_dir: Path = None):
        """Initialize downloader."""
        if output_dir is None:
            output_dir = Path(__file__).parent / "assets" / "NOAKADEXPI"

        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_all_symbol_files(self) -> List[Dict]:
        """Get list of all SVG files from GitHub API."""
        try:
            # Get main symbols directory
            response = requests.get(self.API_URL)
            response.raise_for_status()
            items = response.json()

            svg_files = []

            for item in items:
                if item['type'] == 'file' and item['name'].endswith('.svg'):
                    svg_files.append({
                        'name': item['name'],
                        'path': f"Symbols/{item['name']}",
                        'download_url': item['download_url']
                    })
                elif item['type'] == 'dir':
                    # Get subdirectory contents (Detail, Origo)
                    subdir_url = f"{self.API_URL}/{item['name']}"
                    subdir_response = requests.get(subdir_url)

                    if subdir_response.status_code == 200:
                        subdir_items = subdir_response.json()
                        for subitem in subdir_items:
                            if subitem['type'] == 'file' and subitem['name'].endswith('.svg'):
                                svg_files.append({
                                    'name': subitem['name'],
                                    'path': f"Symbols/{item['name']}/{subitem['name']}",
                                    'download_url': subitem['download_url'],
                                    'subdir': item['name']
                                })

            logger.info(f"Found {len(svg_files)} SVG files total")
            return svg_files

        except Exception as e:
            logger.error(f"Failed to get file list: {e}")
            return []

    def download_symbol(self, file_info: Dict) -> bool:
        """Download a single symbol."""
        try:
            # Determine output path
            if 'subdir' in file_info:
                output_path = self.output_dir / file_info['subdir'] / file_info['name']
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = self.output_dir / file_info['name']

            # Skip if already downloaded
            if output_path.exists():
                logger.debug(f"Already exists: {file_info['name']}")
                return True

            # Download file
            response = requests.get(file_info['download_url'], timeout=10)
            response.raise_for_status()

            # Save file
            output_path.write_bytes(response.content)
            logger.info(f"Downloaded: {file_info['name']}")

            return True

        except Exception as e:
            logger.error(f"Failed to download {file_info['name']}: {e}")
            return False

    def download_all(self) -> Dict:
        """Download all symbols."""
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        # Get all symbol files
        svg_files = self.get_all_symbol_files()
        stats['total'] = len(svg_files)

        if not svg_files:
            logger.error("No SVG files found!")
            return stats

        logger.info(f"Starting download of {stats['total']} symbols...")

        # Download each file
        for i, file_info in enumerate(svg_files, 1):
            # Check if file already exists
            if 'subdir' in file_info:
                output_path = self.output_dir / file_info['subdir'] / file_info['name']
            else:
                output_path = self.output_dir / file_info['name']

            if output_path.exists():
                stats['skipped'] += 1
                logger.debug(f"[{i}/{stats['total']}] Skipped (exists): {file_info['name']}")
                continue

            # Download
            if self.download_symbol(file_info):
                stats['success'] += 1
            else:
                stats['failed'] += 1

            # Progress
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{stats['total']} downloaded")

            # Rate limiting to avoid API limits
            if i % 30 == 0:
                time.sleep(1)

        logger.info(f"Download complete: {stats['success']} new, {stats['skipped']} skipped, {stats['failed']} failed")

        # Save download manifest
        manifest_path = self.output_dir / "download_manifest.json"
        manifest = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'stats': stats,
            'files': [f['name'] for f in svg_files]
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return stats

    def verify_downloads(self) -> Dict:
        """Verify all downloaded files."""
        # Count files in each directory
        main_files = list(self.output_dir.glob("*.svg"))
        detail_files = list((self.output_dir / "Detail").glob("*.svg")) if (self.output_dir / "Detail").exists() else []
        origo_files = list((self.output_dir / "Origo").glob("*.svg")) if (self.output_dir / "Origo").exists() else []

        total = len(main_files) + len(detail_files) + len(origo_files)

        result = {
            'main': len(main_files),
            'detail': len(detail_files),
            'origo': len(origo_files),
            'total': total
        }

        logger.info(f"Verification: {result['main']} main, {result['detail']} detail, {result['origo']} origo = {result['total']} total")

        return result


def main():
    """Main download function."""
    downloader = CompleteNOAKADEXPIDownloader()

    # Download all symbols
    stats = downloader.download_all()

    print("\n" + "="*60)
    print("NOAKADEXPI SYMBOL DOWNLOAD COMPLETE")
    print("="*60)
    print(f"Total files: {stats['total']}")
    print(f"Downloaded: {stats['success']}")
    print(f"Skipped (already exist): {stats['skipped']}")
    print(f"Failed: {stats['failed']}")

    # Verify
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    verification = downloader.verify_downloads()
    print(f"Main symbols: {verification['main']}")
    print(f"Detail symbols: {verification['detail']}")
    print(f"Origo symbols: {verification['origo']}")
    print(f"Total verified: {verification['total']}")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()