# Setup Guide for Engineering MCP Server

This guide provides detailed installation and configuration instructions for the Process Engineering Drawings MCP Server.

## 📋 Prerequisites

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
- Web browser (for dashboard visualization)

## 🔧 Installation Steps

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
python -c "from src.tools import DexpiTools, SfilesTools; print('✅ Installation successful!')"
```

## 🚀 Configuration

### MCP Server Configuration

The MCP server can be configured through environment variables or a configuration file.

#### Environment Variables

```bash
# Optional: Set custom port for dashboard
export DASHBOARD_PORT=8000

# Optional: Set project storage directory
export PROJECT_ROOT=/path/to/projects

# Optional: Enable debug logging
export DEBUG=true
```

#### Configuration File

Create a `.env` file in the project root:

```env
# Dashboard Configuration
DASHBOARD_PORT=8000
DASHBOARD_HOST=0.0.0.0

# Storage Configuration
PROJECT_ROOT=/path/to/projects

# Logging
DEBUG=false
LOG_LEVEL=INFO
```

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

## 🖥️ Dashboard Setup

The web dashboard provides real-time visualization of your engineering drawings.

### Starting the Dashboard

```bash
# Activate virtual environment first
source .venv/bin/activate  # or appropriate command for your OS

# Start the dashboard server
python -m src.dashboard.server

# The dashboard will be available at http://localhost:8000
```

### Dashboard Features
- **Project Browser**: Navigate and open saved projects
- **Model Viewer**: Visualize DEXPI P&IDs and SFILES flowsheets
- **Layout Options**: Switch between hierarchical, force-directed, and breadth-first layouts
- **Real-time Updates**: See changes as the LLM modifies drawings
- **Export Options**: Download visualizations as images or GraphML

### Accessing the Dashboard

1. Open your web browser
2. Navigate to `http://localhost:8000`
3. Enter a project path (e.g., `/tmp/demo_project`)
4. Click "Open Project" to load models
5. Click on any model in the sidebar to visualize it

## 🧪 Testing the Installation

### Run Built-in Tests

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_dexpi_tools.py
pytest tests/test_sfiles_tools.py
pytest tests/test_persistence.py
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
    print(f"✅ DEXPI working: {result['model_id']}")
    
    # Test SFILES tools
    sfiles = SfilesTools({})
    result = await sfiles.handle_tool("sfiles_create_flowsheet", {
        "name": "Test Process",
        "type": "PFD"
    })
    print(f"✅ SFILES working: {result['flowsheet_id']}")

asyncio.run(test_installation())
```

## 🐛 Troubleshooting

### Common Issues and Solutions

#### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**: Ensure you're running from the project root directory and the virtual environment is activated:
```bash
cd /path/to/engineering-mcp-server
source .venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:${PWD}"
```

#### Port Already in Use

**Problem**: `[Errno 98] error while attempting to bind on address ('0.0.0.0', 8000): address already in use`

**Solution**: Either kill the existing process or use a different port:
```bash
# Find and kill the process using port 8000
lsof -i :8000  # Find the PID
kill -9 <PID>  # Kill the process

# Or use a different port
DASHBOARD_PORT=8001 python -m src.dashboard.server
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

## 🔄 Updating

To update to the latest version:

```bash
# Pull latest changes
git pull origin main

# Activate virtual environment
source .venv/bin/activate

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services
# MCP server will restart automatically with Claude Desktop
# Manually restart dashboard if running
```

## 🎓 Next Steps

After successful installation:

1. **Read the README.md** for usage examples and API documentation
2. **Try the examples** in the `examples/` directory
3. **Explore the dashboard** to understand visualization capabilities
4. **Create your first project** using Claude Desktop or the Python API
5. **Join the community** and share your engineering drawings

## 📚 Additional Resources

- [DEXPI Standard Documentation](https://www.dexpi.org/)
- [MCP Protocol Specification](https://github.com/anthropics/mcp)
- [pyDEXPI Library Documentation](https://github.com/process-intelligence-research/pyDEXPI)
- [Cytoscape.js Documentation](https://js.cytoscape.org/)

---

*For contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md)*