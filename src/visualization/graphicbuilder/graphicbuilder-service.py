#!/usr/bin/env python3
"""
GraphicBuilder Service Wrapper
Provides HTTP API for GraphicBuilder Java application
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import yaml
import logging
from typing import Optional, Dict, Any
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load configuration
CONFIG_PATH = Path("/app/config.yaml")
if CONFIG_PATH.exists():
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
else:
    config = {
        "graphicbuilder": {
            "jar_path": "/app/GraphicBuilder/target/GraphicBuilder.jar",
            "symbol_path": "/app/symbols",
            "temp_dir": "/tmp/graphicbuilder"
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "max_file_size": 50 * 1024 * 1024  # 50MB
        }
    }

# Ensure temp directory exists
Path(config["graphicbuilder"]["temp_dir"]).mkdir(parents=True, exist_ok=True)


def run_graphicbuilder(
    input_xml: str,
    output_format: str = "SVG",
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute GraphicBuilder with input XML and return rendered output.

    Args:
        input_xml: Proteus/DEXPI XML content
        output_format: Output format (SVG, PNG, PDF)
        options: Additional rendering options

    Returns:
        Dictionary with rendered content and metadata
    """
    temp_dir = Path(config["graphicbuilder"]["temp_dir"])

    # Create temporary files
    input_file = temp_dir / f"input_{os.getpid()}.xml"
    output_file = temp_dir / f"output_{os.getpid()}.{output_format.lower()}"

    try:
        # Write input XML
        input_file.write_text(input_xml, encoding='utf-8')

        # Build GraphicBuilder command
        cmd = [
            "java",
            "-jar",
            config["graphicbuilder"]["jar_path"],
            "-i", str(input_file),
            "-o", str(output_file),
            "-f", output_format.upper(),
            "-s", config["graphicbuilder"]["symbol_path"]
        ]

        # Add additional options if provided
        if options:
            if options.get("dpi"):
                cmd.extend(["-d", str(options["dpi"])])
            if options.get("scale"):
                cmd.extend(["-scale", str(options["scale"])])

        # Execute GraphicBuilder
        logger.info(f"Running GraphicBuilder: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )

        if result.returncode != 0:
            logger.error(f"GraphicBuilder error: {result.stderr}")
            raise RuntimeError(f"GraphicBuilder failed: {result.stderr}")

        # Read output file
        if not output_file.exists():
            raise FileNotFoundError(f"Output file not generated: {output_file}")

        # Read content based on format
        if output_format.upper() == "SVG":
            content = output_file.read_text(encoding='utf-8')
            encoded = False
        else:
            content = base64.b64encode(output_file.read_bytes()).decode('ascii')
            encoded = True

        # Parse metadata from SVG if available
        metadata = {}
        if output_format.upper() == "SVG":
            # Extract basic SVG metadata
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(content)
                metadata["width"] = root.get("width", "unknown")
                metadata["height"] = root.get("height", "unknown")
                metadata["viewBox"] = root.get("viewBox", "unknown")
            except ET.ParseError as e:
                raise ValueError(
                    f"Failed to parse SVG output from GraphicBuilder. "
                    f"The generated SVG is malformed. "
                    f"Parse error: {e}"
                ) from e
            except (AttributeError, TypeError) as e:
                raise ValueError(
                    f"Failed to extract metadata from SVG. "
                    f"Unexpected SVG structure. "
                    f"Error: {e}"
                ) from e

        return {
            "content": content,
            "format": output_format.upper(),
            "encoded": encoded,
            "metadata": metadata
        }

    finally:
        # Clean up temporary files
        if input_file.exists():
            input_file.unlink()
        if output_file.exists():
            output_file.unlink()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "GraphicBuilder",
        "version": "1.0.0"
    })


@app.route('/render', methods=['POST'])
def render():
    """
    Main rendering endpoint.

    Expected JSON payload:
    {
        "xml": "<Proteus XML content>",
        "format": "SVG|PNG|PDF",
        "options": {
            "dpi": 300,
            "scale": 1.0,
            "include_imagemap": true
        }
    }
    """
    try:
        data = request.get_json()

        if not data or 'xml' not in data:
            return jsonify({
                "error": "Missing 'xml' field in request"
            }), 400

        xml_content = data['xml']
        output_format = data.get('format', 'SVG').upper()
        options = data.get('options', {})

        # Validate format
        if output_format not in ['SVG', 'PNG', 'PDF']:
            return jsonify({
                "error": f"Unsupported format: {output_format}"
            }), 400

        # Run GraphicBuilder
        result = run_graphicbuilder(xml_content, output_format, options)

        # Return rendered content
        response = {
            "content": result["content"],
            "format": result["format"],
            "encoded": result["encoded"],
            "metadata": result["metadata"]
        }

        # Add imagemap if requested and available
        if options.get('include_imagemap') and output_format == 'SVG':
            # TODO: Extract imagemap from SVG
            response["imagemap"] = None

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Rendering error: {str(e)}", exc_info=True)
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/symbols', methods=['GET'])
def list_symbols():
    """List available symbols in the library."""
    symbol_path = Path(config["graphicbuilder"]["symbol_path"])
    symbols = []

    if symbol_path.exists():
        for svg_file in symbol_path.rglob("*.svg"):
            rel_path = svg_file.relative_to(symbol_path)
            symbols.append({
                "path": str(rel_path),
                "name": svg_file.stem,
                "category": rel_path.parts[0] if len(rel_path.parts) > 1 else "root"
            })

    return jsonify({
        "symbols": symbols,
        "count": len(symbols)
    })


@app.route('/validate', methods=['POST'])
def validate_xml():
    """Validate Proteus/DEXPI XML without rendering."""
    try:
        data = request.get_json()

        if not data or 'xml' not in data:
            return jsonify({
                "error": "Missing 'xml' field in request"
            }), 400

        # TODO: Implement XML validation
        # For now, just check if it's valid XML
        import xml.etree.ElementTree as ET
        try:
            ET.fromstring(data['xml'])
            return jsonify({
                "valid": True,
                "message": "XML is well-formed"
            }), 200
        except ET.ParseError as e:
            return jsonify({
                "valid": False,
                "message": str(e)
            }), 200

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return jsonify({
            "error": str(e)
        }), 500


if __name__ == '__main__':
    logger.info(f"Starting GraphicBuilder service on {config['server']['host']}:{config['server']['port']}")
    app.run(
        host=config['server']['host'],
        port=config['server']['port'],
        debug=False
    )