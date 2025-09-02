# Process Engineering Drawings MCP Server
### Machine-Readable, Git-Compatible BFD/PFD/P&ID Generation with DEXPI and SFILES

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://github.com/anthropics/mcp)

## Motivation

### Database-First Engineering Documentation

Engineering workflows require deliverables to be machine-readable and directly processable by Large Language Models (LLMs). This approach prioritizes data models over visual representations, with visualization serving as a secondary layer.

Traditional process engineering drawings (Block Flow Diagrams, Process Flow Diagrams, and Piping & Instrumentation Diagrams) are created using proprietary CAD software that produces binary files which are:
- Not machine-readable by LLMs or automation systems
- Not compatible with git-based version control and diff tools
- Not interoperable across different engineering platforms
- Locked into vendor-specific formats preventing workflow automation

This repository implements a database-first approach to process engineering documentation where:
- The primary artifact is a structured, machine-readable data model (DEXPI/SFILES)
- Visualization is generated from the data model, not vice versa
- All engineering information is stored in git-compatible text formats
- LLMs can directly create, modify, and analyze engineering drawings through MCP tools
- Version control provides complete traceability of engineering decisions

### Technical Implementation

This MCP (Model Context Protocol) server provides LLM-accessible tools for engineering drawing generation using:
- **DEXPI** - ISO 15926 compliant P&ID data model for detailed instrumentation diagrams
- **SFILES** - Compact text notation for BFD/PFD flowsheet representation
- **Git-native storage** - JSON and text formats enabling proper version control and diffing
- **Visualization layer** - Cytoscape.js-based rendering of the underlying data models

## Features

### Core Capabilities
- **LLM-Accessible Drawing Generation** - MCP tools enable LLMs to programmatically create and modify process drawings
- **Dynamic Schema Generation** - Automatically discovers and exposes all pyDEXPI classes through introspection
- **DEXPI P&ID Support** - Full implementation of DEXPI standard for detailed P&ID data models
- **SFILES BFD/PFD Support** - Compact text notation for flowsheet representation
- **Git-Based Persistence** - Version-controlled storage with automatic commit tracking
- **Visualization Dashboard** - Web-based rendering of data models using Cytoscape.js
- **GraphML Export** - Standardized graph format for machine learning pipelines

### MCP Tools Available (50 Total - Consolidating to 12)

**New in v0.3.0:** Batch tools that reduce LLM calls from 50+ to 1-3:
- **model_batch_apply** - Execute multiple operations atomically
- **rules_apply** - Structured validation for LLMs  
- **graph_connect** - Autowiring with inline valve insertion

After testing and validation, legacy tools will be deprecated in favor of the consolidated set:

#### DEXPI P&ID Tools (14 tools)
- `dexpi_create_pid` - Initialize P&ID with ISO 15926 compliant metadata
- `dexpi_add_equipment` - Add equipment from 159 available types (dynamically discovered from pyDEXPI)
- `dexpi_add_piping` - Create piping segments with material specifications
- `dexpi_add_valve` - Add valves from 22 available types including safety and control valves
- `dexpi_insert_valve_in_segment` - Insert valve inline within existing piping segment
- `dexpi_add_instrumentation` - Add instrumentation from 33 available types with signal support
- `dexpi_add_control_loop` - Create complete control loops with signal generating, control, and actuating functions
- `dexpi_connect_components` - Create piping connections between equipment with automatic validation
- `dexpi_import_json` - Import P&ID from JSON representation
- `dexpi_import_proteus_xml` - Import P&ID from Proteus 4.2 XML format
- `dexpi_export_json` - Export P&ID to JSON for version control
- `dexpi_export_graphml` - Export topology as GraphML with sanitization for ML pipelines
- `dexpi_convert_from_sfiles` - Convert SFILES flowsheet to DEXPI P&ID model

#### SFILES Flowsheet Tools (12 tools)
- `sfiles_create_flowsheet` - Initialize BFD or PFD flowsheet
- `sfiles_add_unit` - Add unit operations to flowsheet
- `sfiles_add_stream` - Connect units with process streams
- `sfiles_add_control` - Add control instrumentation to flowsheet
- `sfiles_to_string` - Export flowsheet as compact SFILES notation (v1 or v2)
- `sfiles_from_string` - Create flowsheet from SFILES string representation
- `sfiles_export_networkx` - Export flowsheet as NetworkX graph JSON
- `sfiles_export_graphml` - Export flowsheet topology as GraphML
- `sfiles_parse_and_validate` - Parse SFILES string and validate against regex patterns
- `sfiles_canonical_form` - Convert SFILES to canonical form for comparison
- `sfiles_pattern_helper` - Get SFILES regex patterns and syntax examples
- `sfiles_convert_from_dexpi` - Convert DEXPI P&ID model to SFILES flowsheet

#### Project Management Tools (4 tools)
- `project_init` - Initialize git-tracked project for engineering models
- `project_save` - Save model to project with automatic git commit
- `project_load` - Load model from project repository
- `project_list` - List all models in a project

#### Validation Tools (2 tools)
- `validate_model` - Comprehensive validation of model syntax, topology, and constraints
- `validate_round_trip` - Validate round-trip conversion integrity

#### Schema Introspection Tools (4 tools)
- `schema_list_classes` - List all available classes in DEXPI or SFILES schemas
- `schema_describe_class` - Get detailed information about a specific class
- `schema_find_class` - Search for classes by partial name or pattern
- `schema_get_hierarchy` - Get the inheritance hierarchy for a class or category

#### Graph Analytics Tools (5 tools)
- `graph_analyze_topology` - Analyze paths, cycles, bottlenecks, and connectivity
- `graph_find_paths` - Find paths between nodes in the graph
- `graph_detect_patterns` - Detect common patterns like heat integration, recycle loops
- `graph_calculate_metrics` - Calculate graph metrics like diameter, density, clustering
- `graph_compare_models` - Compare graph structures of two models

#### Search and Query Tools (6 tools)
- `search_by_tag` - Find equipment, instruments, or nodes by tag pattern
- `search_by_type` - Find all components of a specific type
- `search_by_attributes` - Search for components by attribute values
- `search_connected` - Find all components connected to a specific node
- `query_model_statistics` - Get statistical summary of model contents
- `search_by_stream` - Search for streams by properties or connected units

## Requirements

- Python 3.10+
- Virtual environment recommended
- Git for version control

## Installation

### Method 1: Using uv (Recommended)
```bash
# Clone the repository
git clone https://github.com/puran-water/dexpi-sfiles-mcp-server.git
cd dexpi-sfiles-mcp-server

# Run with uv (handles dependencies automatically)
uv run python -m src.server
```

### Method 2: Traditional pip installation
```bash
# Clone the repository
git clone https://github.com/puran-water/dexpi-sfiles-mcp-server.git
cd dexpi-sfiles-mcp-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the MCP server
python -m src.server
```

### Method 3: Package installation (Future)
```bash
# Once published to PyPI
pip install engineering-mcp-server
engineering-mcp
```

See [SETUP.md](SETUP.md) for detailed installation instructions.

## Usage

### With Claude Code (Recommended)

1. Create or update `.mcp.json` in your project root:
```json
{
  "mcpServers": {
    "engineering-mcp": {
      "command": "python",
      "args": ["-m", "src.server"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/engineering-mcp-server"
      }
    }
  }
}
```

2. Use natural language in Claude Code to create drawings:
```
"Create a P&ID for a reactor system with feed tank, pump, heat exchanger, and distillation column"
```

### With Codex CLI

1. Add to your Codex configuration (`~/.codex/config.toml`):
```toml
[mcp_servers.engineering-mcp]
command = "uv"
args = ["--directory", "/path/to/engineering-mcp-server", "run", "python", "-m", "src.server"]
```

Or if installed via pip:
```toml
[mcp_servers.engineering-mcp]
command = "python"
args = ["-m", "src.server"]
```

2. Launch Codex TUI interface for interactive engineering drawing creation:
```bash
codex
```

Then use natural language in the TUI:
```
> Create a BFD for an ammonia synthesis process
> Add a distillation column C-101 to the current P&ID
> Generate control loop for level control on tank TK-101
```

### With uvx (Quick Start)

For temporary usage without installation:
```bash
uvx --from engineering-mcp-server engineering-mcp
```

### Dashboard Visualization

1. Start the dashboard server:
```bash
python -m src.dashboard.server
```

2. Open http://localhost:8000 in your browser

3. Enter your project path and click "Open Project"

4. Click on models to visualize them with interactive layouts

## Project Structure

```
engineering-mcp-server/
├── src/
│   ├── server.py              # Main MCP server
│   ├── tools/                  # MCP tool implementations
│   │   ├── dexpi_tools.py     # DEXPI P&ID tools
│   │   └── sfiles_tools.py    # SFILES flowsheet tools
│   ├── persistence/           # Git-based storage
│   ├── dashboard/             # Web visualization
│   │   ├── server.py          # FastAPI server
│   │   └── static/            # HTML/JS frontend
│   └── converters/            # Format converters
├── examples/                  # Example drawings
├── tests/                     # Test suite
├── requirements.txt          # Python dependencies
├── LICENSE                   # AGPL v3 license
└── README.md                # This file
```

## Example: Creating a P&ID

```python
# The LLM can execute these through MCP:

# 1. Initialize project
dexpi_init_project(
    project_path="/tmp/plant_project",
    project_name="Demo Plant"
)

# 2. Create P&ID
model_id = dexpi_create_pid(
    project_name="Demo Plant",
    drawing_number="PID-001"
)

# 3. Add equipment
dexpi_add_equipment(
    model_id=model_id,
    equipment_type="Tank",
    tag_name="TK-101"
)

dexpi_add_equipment(
    model_id=model_id,
    equipment_type="Pump",
    tag_name="P-101"
)

# 4. Connect with piping
dexpi_connect_components(
    model_id=model_id,
    from_component="TK-101",
    to_component="P-101",
    line_number="100-PL-001"
)

# 5. Save to git
dexpi_save_to_project(
    model_id=model_id,
    project_path="/tmp/plant_project",
    model_name="main_pid"
)
```

## Example: Creating a PFD with SFILES

```python
# Create flowsheet
flowsheet_id = sfiles_create_flowsheet(
    name="Reactor Process",
    type="PFD"
)

# Add units
sfiles_add_unit(flowsheet_id, "feed-1", "feed")
sfiles_add_unit(flowsheet_id, "reactor-1", "reactor")
sfiles_add_unit(flowsheet_id, "product-1", "product")

# Connect units
sfiles_add_stream(flowsheet_id, "feed-1", "reactor-1")
sfiles_add_stream(flowsheet_id, "reactor-1", "product-1")

# Export SFILES notation
result = sfiles_to_string(flowsheet_id)
# Output: "(feed)(reactor)(product)"
```

## Standards & Specifications

- **DEXPI** - ISO 15926 compliant P&ID information model
- **SFILES** - Simplified Flowsheet Input Line Entry System
- **GraphML** - Graph Markup Language for ML pipelines
- **MCP** - Anthropic's Model Context Protocol

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

### Key License Requirements

- **Source Code Disclosure**: If you run this software as a network service, you must provide source code access to users
- **Copyleft**: Modifications must be released under the same AGPL license
- **Attribution**: Must maintain copyright notices and license information

### Dependencies & Attribution

This project uses the following open-source libraries:

- **pyDEXPI** - AGPL-3.0 License
  - Copyright (C) 2025 Artur M. Schweidtmann
  - [GitHub](https://github.com/process-intelligence-research/pyDEXPI)
  
- **NetworkX** - BSD 3-Clause License
  - Copyright (C) NetworkX Developers
  
- **FastAPI** - MIT License
  - Copyright (c) 2018 Sebastián Ramírez
  
- **MCP** - MIT License
  - Copyright (c) 2024 Anthropic

See [LICENSE](LICENSE) for full license text and [LICENSES/](LICENSES/) for dependency licenses.

## Acknowledgments

- **Process Intelligence Research** for pyDEXPI
- **Anthropic** for the MCP protocol
- **DEXPI Initiative** for P&ID standards
- **Cytoscape.js** team for visualization

## Contact

For questions, issues, or contributions, please open an issue on GitHub.

## Links

- [DEXPI Standard](https://www.dexpi.org/)
- [MCP Documentation](https://github.com/anthropics/mcp)
- [pyDEXPI Documentation](https://github.com/process-intelligence-research/pyDEXPI)
- [Dashboard Guide](docs/dashboard.md)

---

