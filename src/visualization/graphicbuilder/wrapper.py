"""
GraphicBuilder Python Wrapper Client
Provides Python interface to GraphicBuilder Docker service
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import base64
import logging
from dataclasses import dataclass
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class RenderOptions:
    """Options for rendering."""
    dpi: int = 300
    scale: float = 1.0
    include_imagemap: bool = True
    layers: List[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for API."""
        return {
            k: v for k, v in {
                'dpi': self.dpi,
                'scale': self.scale,
                'include_imagemap': self.include_imagemap,
                'layers': self.layers
            }.items() if v is not None
        }


@dataclass
class RenderResult:
    """Result from rendering operation."""
    content: Union[str, bytes]
    format: str
    metadata: Dict[str, Any]
    imagemap: Optional[str] = None
    encoded: bool = False

    def save_to_file(self, path: Union[str, Path]) -> None:
        """Save rendered content to file."""
        path = Path(path)

        if self.encoded:
            # Decode base64 content for binary formats
            content = base64.b64decode(self.content)
            path.write_bytes(content)
        else:
            # Write text content for SVG
            path.write_text(self.content, encoding='utf-8')

        logger.info(f"Saved {self.format} to {path}")

    def extract_imagemap(self) -> Optional[Dict[str, Any]]:
        """Extract imagemap data from SVG content."""
        if self.format != 'SVG' or self.encoded:
            return None

        try:
            root = ET.fromstring(self.content)

            # Look for clickable areas in SVG
            areas = []
            for elem in root.findall('.//*[@id]'):
                # Check if element has interaction attributes
                if elem.get('onclick') or elem.get('data-tag'):
                    bbox = elem.get('bbox')
                    areas.append({
                        'id': elem.get('id'),
                        'tag': elem.get('data-tag'),
                        'type': elem.tag.split('}')[-1],  # Remove namespace
                        'bbox': bbox
                    })

            if areas:
                return {
                    'areas': areas,
                    'count': len(areas)
                }
        except Exception as e:
            logger.warning(f"Failed to extract imagemap: {e}")

        return None


class GraphicBuilderRenderer:
    """Python client for GraphicBuilder Docker service."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        """
        Initialize GraphicBuilder client.

        Args:
            host: Service host
            port: Service port
        """
        self.base_url = f"http://{host}:{port}"
        self.client = httpx.AsyncClient(timeout=60.0)
        self._cache = {}  # Simple in-memory cache

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """
        Check if service is healthy.

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def render(
        self,
        proteus_xml: str,
        format: str = "SVG",
        options: Optional[RenderOptions] = None
    ) -> RenderResult:
        """
        Render Proteus/DEXPI XML to specified format.

        Args:
            proteus_xml: XML content to render
            format: Output format (SVG, PNG, PDF)
            options: Rendering options

        Returns:
            RenderResult with rendered content
        """
        # Validate format
        format = format.upper()
        if format not in ['SVG', 'PNG', 'PDF']:
            raise ValueError(f"Unsupported format: {format}")

        # Prepare request
        if options is None:
            options = RenderOptions()

        # Check cache
        cache_key = f"{hash(proteus_xml)}_{format}_{hash(str(options.to_dict()))}"
        if cache_key in self._cache:
            logger.info("Returning cached result")
            return self._cache[cache_key]

        # Send request to service
        payload = {
            "xml": proteus_xml,
            "format": format,
            "options": options.to_dict()
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/render",
                json=payload
            )
            response.raise_for_status()

            data = response.json()

            # Create result
            result = RenderResult(
                content=data['content'],
                format=data['format'],
                metadata=data.get('metadata', {}),
                imagemap=data.get('imagemap'),
                encoded=data.get('encoded', False)
            )

            # Cache result
            self._cache[cache_key] = result

            return result

        except httpx.HTTPError as e:
            logger.error(f"Render request failed: {e}")
            raise RuntimeError(f"Failed to render: {e}")

    async def validate_xml(self, proteus_xml: str) -> Dict[str, Any]:
        """
        Validate Proteus/DEXPI XML.

        Args:
            proteus_xml: XML content to validate

        Returns:
            Validation result
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/validate",
                json={"xml": proteus_xml}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Validation request failed: {e}")
            raise RuntimeError(f"Failed to validate XML: {e}")

    async def list_symbols(self) -> List[Dict[str, str]]:
        """
        List available symbols in the library.

        Returns:
            List of symbol information
        """
        try:
            response = await self.client.get(f"{self.base_url}/symbols")
            response.raise_for_status()
            data = response.json()
            return data.get('symbols', [])
        except httpx.HTTPError as e:
            logger.error(f"List symbols request failed: {e}")
            raise RuntimeError(f"Failed to list symbols: {e}")

    def parse_imagemap(self, svg_content: str) -> Optional[Dict[str, Any]]:
        """
        Parse imagemap data from SVG content.

        Args:
            svg_content: SVG content with imagemap

        Returns:
            Parsed imagemap data
        """
        result = RenderResult(
            content=svg_content,
            format='SVG',
            metadata={},
            encoded=False
        )
        return result.extract_imagemap()


# Synchronous wrapper for convenience
class GraphicBuilderRendererSync:
    """Synchronous wrapper for GraphicBuilder client."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.async_renderer = GraphicBuilderRenderer(host, port)

    def render(
        self,
        proteus_xml: str,
        format: str = "SVG",
        options: Optional[RenderOptions] = None
    ) -> RenderResult:
        """Render synchronously."""
        return asyncio.run(self.async_renderer.render(proteus_xml, format, options))

    def health_check(self) -> bool:
        """Health check synchronously."""
        return asyncio.run(self.async_renderer.health_check())

    def validate_xml(self, proteus_xml: str) -> Dict[str, Any]:
        """Validate XML synchronously."""
        return asyncio.run(self.async_renderer.validate_xml(proteus_xml))

    def list_symbols(self) -> List[Dict[str, str]]:
        """List symbols synchronously."""
        return asyncio.run(self.async_renderer.list_symbols())

    def close(self):
        """Close the client."""
        asyncio.run(self.async_renderer.close())


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Example Proteus XML (minimal)
        example_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PlantModel>
            <Equipment ID="P-101" Type="CentrifugalPump">
                <Position X="100" Y="200"/>
                <TagName>P-101</TagName>
            </Equipment>
        </PlantModel>
        """

        async with GraphicBuilderRenderer() as renderer:
            # Check health
            healthy = await renderer.health_check()
            print(f"Service healthy: {healthy}")

            if healthy:
                # Render to SVG
                result = await renderer.render(
                    example_xml,
                    format="SVG",
                    options=RenderOptions(dpi=300, scale=1.0)
                )

                print(f"Rendered {result.format}")
                print(f"Metadata: {result.metadata}")

                # Save to file
                result.save_to_file("output.svg")

                # Extract imagemap
                imagemap = result.extract_imagemap()
                if imagemap:
                    print(f"Found {imagemap['count']} interactive areas")

    asyncio.run(main())