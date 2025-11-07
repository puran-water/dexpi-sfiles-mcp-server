# Setup Guide for Engineering MCP Server

This guide provides detailed installation and configuration instructions for the Process Engineering Drawings MCP Server.

## Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows (with WSL2 recommended)
- **Python**: Version 3.10 or higher
- **Git**: For version control
- **Memory**: Minimum 4GB RAM recommended
- **Disk Space**: At least 1GB free space

### Software Dependencies
- Python 3.10+ with pip
- Git 2.0+
- Virtual environment support (venv)

## Installation Steps

### 1. Clone the Repository

```bash
# Clone from GitHub (replace with your fork if applicable)
git clone https://github.com/yourusername/engineering-mcp-server.git
cd engineering-mcp-server
```

### 2. Set Up Python Virtual Environment

It's strongly recommended to use a virtual environment to avoid dependency conflicts:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

# On Windows with PowerShell:
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
# Ensure pip is up to date
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
# Test that the MCP server can start
python -m src.server --help

# Test that imports work correctly
python -c "from src.tools.dexpi_tools import DexpiTools; from src.tools.sfiles_tools import SfilesTools; print('Installation successful!')"
```

## Configuration

### MCP Server Configuration

The MCP server can be configured through environment variables or a configuration file.

#### Environment Variables

Define only the variables actually consumed by the codebase:

```bash
# Storage configuration for project persistence
export PROJECT_ROOT=/path/to/projects

# Logging
export LOG_LEVEL=INFO
export DEBUG=false
```

#### Configuration File

Optionally capture the same values in a `.env` file in the project root so tooling such as `direnv` or `dotenv` can load them automatically.

### Claude Desktop Integration

To use with Claude Desktop, add the server to your configuration:

1. **Find your Claude Desktop config file**:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Add the MCP server configuration**:

```json
{
  "mcpServers": {
    "engineering-mcp": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/engineering-mcp-server",
      "env": {
        "PYTHONPATH": "/absolute/path/to/engineering-mcp-server",
        "PATH": "/absolute/path/to/engineering-mcp-server/.venv/bin:$PATH"
      }
    }
  }
}
```

3. **Restart Claude Desktop** for changes to take effect

### Standalone MCP Usage

For development or testing without Claude Desktop:

```bash
# Start the MCP server directly
python -m src.server

# The server will output its capabilities in JSON format
# You can interact with it using the MCP protocol over stdin/stdout
```

## Visualization Outputs

This repository does **not** ship a dashboard service. Visualization artifacts are produced automatically when models are saved with `project_save`:

- `pid/<model>.html`, `pfd/<model>.html`, or `bfd/<model>.html`: Plotly-based interactive files that can be opened directly in any modern browser. The Plotly toolbar supports PNG/SVG export for local snapshots.
- `<model>.graphml`: GraphML exports generated via `UnifiedGraphConverter` for use with NetworkX or other graph analytics tools.

Open the HTML files manually in your browser or load the GraphML output into your preferred graph environment for further processing.

## Testing the Installation

### Run Built-in Tests

```bash
# Run all tests
pytest tests/

# Run specific test modules that exist in this repo
pytest tests/test_template_tools.py
pytest tests/test_graphml_export.py
pytest tests/test_transaction_manager.py
```

### Create a Test Project

```bash
# Start Python with the virtual environment activated
python

# Run this test script
```

```python
import asyncio
from src.tools.dexpi_tools import DexpiTools
from src.tools.sfiles_tools import SfilesTools

async def test_installation():
    # Test DEXPI tools
    dexpi = DexpiTools({})
    result = await dexpi.handle_tool("dexpi_create_pid", {
        "project_name": "Test Plant",
        "drawing_number": "PID-TEST-001"
    })
    print(f"DEXPI working: {result['model_id']}")
    
    # Test SFILES tools
    sfiles = SfilesTools({})
    result = await sfiles.handle_tool("sfiles_create_flowsheet", {
        "name": "Test Process",
        "type": "PFD"
    })
    print(f"SFILES working: {result['flowsheet_id']}")

asyncio.run(test_installation())
```

## Troubleshooting

### Common Issues and Solutions

#### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**: Ensure you're running from the project root directory and the virtual environment is activated:
```bash
cd /path/to/engineering-mcp-server
source .venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:${PWD}"
```


#### Virtual Environment Issues

**Problem**: `pip: command not found` or package installation fails

**Solution**: Ensure you're using the correct Python version and venv is activated:
```bash
# Check Python version
python3 --version  # Should be 3.10 or higher

# Recreate virtual environment if needed
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Claude Desktop Connection Issues

**Problem**: Claude Desktop doesn't recognize the MCP server

**Solution**: Check your configuration:
1. Verify the path in `claude_desktop_config.json` is absolute
2. Ensure the virtual environment path is included in the env PATH
3. Check that Python is accessible from the specified cwd
4. Restart Claude Desktop after configuration changes

### Getting Help

If you encounter issues not covered here:

1. Check the [GitHub Issues](https://github.com/yourusername/engineering-mcp-server/issues)
2. Review the error logs in the terminal
3. Enable debug mode: `DEBUG=true python -m src.server`
4. Open a new issue with:
   - Your OS and Python version
   - Complete error message
   - Steps to reproduce the issue

## Updating

To update to the latest version:

```bash
# Pull latest changes
git pull origin main

# Activate virtual environment
source .venv/bin/activate

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services as needed (e.g., relaunch MCP server inside your MCP client)
```

## Next Steps

After successful installation:

1. **Read the README.md** for usage examples and API documentation
2. **Try the examples** in the `examples/` directory
3. **Inspect generated HTML/GraphML outputs** after running `project_save`
4. **Create your first project** using Claude Desktop, Codex CLI, or the Python API
5. **Review documentation** for advanced features and API details

## Additional Resources

- [DEXPI Standard Documentation](https://www.dexpi.org/)
- [MCP Protocol Specification](https://github.com/anthropics/mcp)
- [pyDEXPI Library Documentation](https://github.com/process-intelligence-research/pyDEXPI)
- [Plotly Python Documentation](https://plotly.com/python/)

---

*For contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md)*
