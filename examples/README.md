# Engineering MCP Server Examples

This directory contains runnable Python scripts that demonstrate how to drive the MCP tools directly. Each example builds models using the same code paths that MCP clients call.

## Contents

| File | Description |
|------|-------------|
| `simple_pid.py` | Creates a minimal DEXPI P&ID (tank → pump → reactor → tank) and saves it with project tools. |
| `complex_flowsheet.py` | Builds an SFILES flowsheet with multiple units, recycle streams, and control instrumentation. |

These are the only scripts currently checked in. If you add more, update this table accordingly.

## Running the Examples

```bash
cd /path/to/engineering-mcp-server
source .venv/bin/activate  # if using a virtual environment
python examples/simple_pid.py
python examples/complex_flowsheet.py
```

Each script writes its output to `/tmp/example_projects/<example_name>` using the `project_*` MCP tools. After running, open the generated Plotly HTML files (e.g., `/tmp/example_projects/simple_pid/pid/simple_pid.html`) or the accompanying GraphML to review the results.

## Using Examples with MCP Clients

You can reference these scripts when prompting an MCP-aware client (Claude Code, Codex CLI, etc.). For example:

- “Create a P&ID similar to the steps in `examples/simple_pid.py`.”
- “Build a flowsheet like `examples/complex_flowsheet.py`, then export GraphML.”

## Creating Your Own Script

Use the following template to bootstrap additional examples:

```python
import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.tools.dexpi_tools import DexpiTools
from src.tools.sfiles_tools import SfilesTools
from src.tools.project_tools import ProjectTools

async def main():
    dexpi_models = {}
    sfiles_models = {}

    dexpi = DexpiTools(dexpi_models, sfiles_models)
    sfiles = SfilesTools(sfiles_models, dexpi_models)
    projects = ProjectTools(dexpi_models, sfiles_models)

    # Your MCP tool calls here...

if __name__ == "__main__":
    asyncio.run(main())
```

## Additional Resources

- [README.md](../README.md) – Feature overview and tool catalog
- [SETUP.md](../SETUP.md) – Installation instructions
- [docs/DYNAMIC_SCHEMA.md](../docs/DYNAMIC_SCHEMA.md) – Details about schema introspection (schema_* tools)

Keep example files synchronized with the rest of the documentation so users can trust that each script runs without modification.
