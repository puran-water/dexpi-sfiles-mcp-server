# Engineering MCP Server Examples

This directory contains example scripts and projects demonstrating the capabilities of the Engineering MCP Server.

## 📁 Contents

- `simple_pid.py` - Create a basic P&ID with tank, pump, and reactor
- `complex_flowsheet.py` - Build a complete process flowsheet with SFILES
- `reactor_system.py` - Detailed reactor system with instrumentation
- `distillation_column.py` - Distillation column with heat integration
- `batch_process.py` - Batch reactor with sequential operations

## 🚀 Running Examples

### Prerequisites

1. Ensure the MCP server is installed (see [SETUP.md](../SETUP.md))
2. Activate the virtual environment:
```bash
cd ..
source .venv/bin/activate
```

### Running Individual Examples

```bash
# Run a specific example
python examples/simple_pid.py

# All examples create projects in /tmp/example_projects/
# View results in the dashboard at http://localhost:8000
```

### Using with Claude Desktop

These examples show the MCP tool calls that Claude can make. Simply ask Claude:
- "Create a P&ID like the simple_pid example"
- "Build a distillation system with heat integration"
- "Generate a batch process flowsheet"

## 📊 Example Descriptions

### 1. Simple P&ID (`simple_pid.py`)
Creates a basic P&ID with:
- Feed tank (TK-101)
- Centrifugal pump (P-101)
- Stirred reactor (R-101)
- Piping connections
- Level and temperature instrumentation

### 2. Complex Flowsheet (`complex_flowsheet.py`)
Demonstrates SFILES capabilities:
- Multiple unit operations
- Recycle streams
- Heat integration
- Parallel processing paths
- Compact notation export

### 3. Reactor System (`reactor_system.py`)
Complete reactor system with:
- Feed preparation
- Preheating
- Reaction section
- Product separation
- Control loops
- Safety instrumentation

### 4. Distillation Column (`distillation_column.py`)
Separation system featuring:
- Feed preheater
- Distillation column
- Reboiler and condenser
- Reflux system
- Product streams

### 5. Batch Process (`batch_process.py`)
Batch operation example:
- Sequential operations
- Charging and discharging
- Temperature control
- Batch tracking

## 🎯 Learning Path

1. **Start with `simple_pid.py`** to understand basic DEXPI operations
2. **Try `complex_flowsheet.py`** to learn SFILES notation
3. **Explore `reactor_system.py`** for instrumentation examples
4. **Study `distillation_column.py`** for heat integration patterns
5. **Review `batch_process.py`** for sequential logic

## 📝 Creating Your Own Examples

Use this template:

```python
import asyncio
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.tools.dexpi_tools import DexpiTools
from src.tools.sfiles_tools import SfilesTools

async def create_my_process():
    # Initialize tools
    dexpi = DexpiTools({})
    sfiles = SfilesTools({})
    
    # Your process here
    pass

if __name__ == "__main__":
    asyncio.run(create_my_process())
```

## 🔗 Additional Resources

- [DEXPI Standard Examples](https://www.dexpi.org/examples)
- [SFILES Notation Guide](../docs/sfiles_notation.md)
- [MCP Tool Reference](../docs/mcp_tools.md)

---

*For questions or contributions, see [CONTRIBUTING.md](../CONTRIBUTING.md)*