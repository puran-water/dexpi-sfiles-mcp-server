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

    NOTE: GraphicBuilder CLI only accepts a single argument (input filename).
    It automatically generates PNG output by replacing .xml with .png.
    We work around this limitation by:
    1. Running GraphicBuilder to create PNG
    2. For SVG: We need to extract SVG from GraphicBuilder's internal processing
    3. For PDF: Convert PNG to PDF using external tools

    Args:
        input_xml: Proteus/DEXPI XML content
        output_format: Output format (PNG only for now, SVG/PDF TODO)
        options: Additional rendering options (currently ignored)

    Returns:
        Dictionary with rendered content and metadata
    """
    temp_dir = Path(config["graphicbuilder"]["temp_dir"])

    # GraphicBuilder requires input file to end with .xml
    # and automatically creates output as input.png
    input_file = temp_dir / f"input_{os.getpid()}.xml"
    expected_output = input_file.with_suffix('.png')

    try:
        # Write input XML
        input_file.write_text(input_xml, encoding='utf-8')

        # Build GraphicBuilder command
        # NOTE: GraphicBuilder only accepts ONE argument - the input file
        # All other arguments (-i, -o, -f, -s, etc.) do NOT exist
        cmd = [
            "java",
            *config["graphicbuilder"].get("java_opts", "-Xmx2G").split(),
            "-jar",
            config["graphicbuilder"]["jar_path"],
            str(input_file)  # Single argument - input filename
        ]

        # Execute GraphicBuilder
        logger.info(f"Running GraphicBuilder: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # Increased timeout
            cwd=str(temp_dir)  # Run in temp dir so output file is created there
        )

        # GraphicBuilder has a bug - it exits with code 1 even on success
        # Check if output file was created instead of relying on returncode
        if not expected_output.exists():
            logger.error(f"GraphicBuilder stdout: {result.stdout}")
            logger.error(f"GraphicBuilder stderr: {result.stderr}")
            raise FileNotFoundError(
                f"GraphicBuilder did not create output file. "
                f"Expected: {expected_output}. "
                f"Exit code: {result.returncode}"
            )

        logger.info(f"GraphicBuilder created: {expected_output} ({expected_output.stat().st_size} bytes)")

        # For now, we only support PNG (GraphicBuilder's native format)
        if output_format.upper() != "PNG":
            logger.warning(f"Format {output_format} requested but GraphicBuilder only produces PNG. Returning PNG.")

        # Read PNG content
        content = base64.b64encode(expected_output.read_bytes()).decode('ascii')

        return {
            "content": content,
            "format": "PNG",  # Always PNG for now
            "encoded": True,
            "metadata": {
                "file_size": expected_output.stat().st_size,
                "note": "GraphicBuilder CLI only supports PNG output"
            }
        }

    finally:
        # Clean up temporary files
        if input_file.exists():
            input_file.unlink()
        if expected_output.exists():
            expected_output.unlink()


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