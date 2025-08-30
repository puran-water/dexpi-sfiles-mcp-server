# Engineering Drawing MCP Server

An MCP (Model Context Protocol) server for LLM-assisted generation of engineering drawings including Block Flow Diagrams (BFD), Process Flow Diagrams (PFD), and Piping & Instrumentation Diagrams (P&ID).

## Features

- **P&ID Generation (DEXPI-based)**
  - Create and manipulate P&ID models using DEXPI standard
  - Add equipment, piping, and instrumentation
  - Export to JSON and GraphML formats
  - ISA-5.1 compliant tag validation

- **BFD/PFD Generation (SFILES2-based)**
  - Create flowsheets with units and streams
  - Convert to/from compact SFILES string format
  - Export to NetworkX and GraphML formats
  - Support for control instrumentation

- **Graph Conversion**
  - Unified conversion between DEXPI, NetworkX, and GraphML
  - Machine-learning ready representations
  - Topology analysis and comparison

- **LLM Integration**
  - LLM-guided pattern generation for P&IDs
  - Structured plan validation
  - Equipment pattern library

- **Engineering Validation**
  - ISA-5.1 tag name validation
  - Pipe class and material validation
  - Equipment specification constraints
  - Control loop validation

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd engineering-mcp-server

# Install dependencies
pip install -e .

# For development
pip install -e ".[dev]"
```

## Usage

### Starting the MCP Server

```bash
python -m src.server
```

Or using the installed script:

```bash
engineering-mcp
```

### Available MCP Tools

#### P&ID Tools (DEXPI)

- `dexpi_create_pid` - Initialize a new P&ID model
- `dexpi_add_equipment` - Add equipment (pump, tank, reactor, etc.)
- `dexpi_add_piping` - Add piping segments
- `dexpi_add_instrumentation` - Add instrumentation
- `dexpi_connect_components` - Create piping connections
- `dexpi_validate_model` - Validate P&ID model
- `dexpi_export_json` - Export as JSON
- `dexpi_export_graphml` - Export as GraphML
- `dexpi_import_json` - Import from JSON

#### BFD/PFD Tools (SFILES)

- `sfiles_create_flowsheet` - Initialize a new flowsheet
- `sfiles_add_unit` - Add unit operation
- `sfiles_add_stream` - Add stream between units
- `sfiles_to_string` - Convert to SFILES string
- `sfiles_from_string` - Create from SFILES string
- `sfiles_export_networkx` - Export as NetworkX graph
- `sfiles_export_graphml` - Export as GraphML
- `sfiles_add_control` - Add control instrumentation
- `sfiles_validate_topology` - Validate flowsheet topology

### Available MCP Resources

Resources provide read-only access to generated models:

- `dexpi/{model_id}/json` - P&ID model as JSON
- `dexpi/{model_id}/graphml` - P&ID topology as GraphML
- `dexpi/{model_id}/networkx` - P&ID as NetworkX graph
- `sfiles/{flowsheet_id}/string` - Flowsheet as SFILES string
- `sfiles/{flowsheet_id}/graphml` - Flowsheet as GraphML
- `sfiles/{flowsheet_id}/networkx` - Flowsheet as NetworkX graph

## Example Usage with LLM

### Creating a P&ID

```json
{
  "tool": "dexpi_create_pid",
  "arguments": {
    "project_name": "Water Treatment Plant",
    "drawing_number": "WTP-PID-001",
    "revision": "A",
    "description": "Raw water intake system"
  }
}
```

### Adding Equipment

```json
{
  "tool": "dexpi_add_equipment",
  "arguments": {
    "model_id": "uuid-here",
    "equipment_type": "Pump",
    "tag_name": "P-101",
    "specifications": {
      "flow_rate": 100.0,
      "head": 30.0
    }
  }
}
```

### Creating a BFD/PFD

```json
{
  "tool": "sfiles_create_flowsheet",
  "arguments": {
    "name": "Ethanol Production",
    "type": "PFD",
    "description": "Fermentation section"
  }
}
```

### Adding Units and Streams

```json
{
  "tool": "sfiles_add_unit",
  "arguments": {
    "flowsheet_id": "uuid-here",
    "unit_name": "fermentor-1",
    "unit_type": "reactor",
    "parameters": {
      "volume": 500.0,
      "temperature": 35.0
    }
  }
}
```

## Architecture

The server is organized into several modules:

- **tools/** - MCP tool implementations for DEXPI and SFILES
- **resources/** - MCP resource providers for data access
- **converters/** - Graph conversion utilities
- **generators/** - LLM-guided generation functions
- **validators/** - Engineering constraints and validation
- **patterns/** - Equipment pattern library

## Testing

Run tests using pytest:

```bash
pytest tests/
```

With coverage:

```bash
pytest --cov=src tests/
```

## Development

Format code:

```bash
black src/ tests/
```

Lint code:

```bash
ruff check src/ tests/
```

Type checking:

```bash
mypy src/
```

## Dependencies

- **pyDEXPI** - DEXPI P&ID data model (AGPL-3.0 license)
- **SFILES2** - Flowsheet representation (Apache license)
- **NetworkX** - Graph manipulation
- **MCP** - Model Context Protocol

## License

MIT

## Contributing

Contributions are welcome! Please ensure all tests pass and code is formatted before submitting pull requests.

## Notes

- This server provides data-only representations without visualization
- Graphics/visualization can be added as a separate layer
- All formats (JSON, SFILES, GraphML) are git-friendly and diffable
- The server runs as a service to satisfy pyDEXPI's AGPL license requirements