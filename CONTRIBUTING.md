# Contributing to Engineering MCP Server

Thank you for your interest in contributing to the Process Engineering Drawings MCP Server! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. We expect all contributors to:

- Be respectful and considerate in all interactions
- Welcome newcomers and help them get started
- Focus on constructive criticism and collaborative problem-solving
- Respect differing viewpoints and experiences

## How to Contribute

### Reporting Issues

Before creating an issue, please:
1. Search existing issues to avoid duplicates
2. Use the issue templates when available
3. Provide clear, detailed information including:
   - Your environment (OS, Python version)
   - Steps to reproduce the issue
   - Expected vs actual behavior
   - Error messages and logs

### Suggesting Features

Feature requests are welcome! Please:
1. Check if the feature has already been requested
2. Explain the use case and benefits
3. Provide examples of how it would work
4. Consider how it fits with the project's goals

### Contributing Code

#### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/yourusername/engineering-mcp-server.git
cd engineering-mcp-server
git remote add upstream https://github.com/original/engineering-mcp-server.git
```

#### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available
```

#### 3. Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

#### 4. Make Your Changes

Follow these guidelines:

##### Code Style
- Follow PEP 8 Python style guide
- Use meaningful variable and function names
- Add type hints where appropriate
- Keep functions focused and small
- Document complex logic with comments

##### Documentation
- Update README.md if adding new features
- Add docstrings to all functions and classes
- Update or create examples for new functionality
- Ensure all MCP tools have clear descriptions

##### Testing
- Write tests for new functionality
- Ensure existing tests pass
- Aim for good test coverage
- Test edge cases and error conditions

#### 5. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add support for new valve types in DEXPI tools

- Added ButterflyValve and DiaphragmValve classes
- Updated valve type enum in dexpi_tools.py
- Added tests for new valve types
- Updated documentation"
```

Follow conventional commit format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks

#### 6. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title and description
- Reference to any related issues
- Summary of changes
- Screenshots if UI changes
- Test results

## Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_dexpi_tools.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v
```

### Writing Tests

```python
# Example test structure
import pytest
from src.tools.dexpi_tools import DexpiTools

class TestDexpiTools:
    @pytest.fixture
    def dexpi_tools(self):
        return DexpiTools({})
    
    async def test_create_pid(self, dexpi_tools):
        result = await dexpi_tools.handle_tool("dexpi_create_pid", {
            "project_name": "Test Project",
            "drawing_number": "PID-001"
        })
        assert result["status"] == "success"
        assert "model_id" in result
```

## Architecture Guidelines

### Adding New MCP Tools

1. **Define the tool in the appropriate handler** (`dexpi_tools.py` or `sfiles_tools.py`)
2. **Add to get_tools() method** with proper schema
3. **Implement handler method** with validation
4. **Add tests** for the new tool
5. **Update documentation** in README.md

Example:
```python
# In get_tools()
Tool(
    name="dexpi_add_new_component",
    description="Add a new component type",
    inputSchema={
        "type": "object",
        "properties": {
            "model_id": {"type": "string"},
            "component_type": {"type": "string"},
            "tag_name": {"type": "string"}
        },
        "required": ["model_id", "component_type", "tag_name"]
    }
)

# Handler method
async def _add_new_component(self, args: dict) -> dict:
    # Validate inputs
    # Perform operation
    # Return result
    pass
```

### Dashboard Development

When modifying the dashboard:
1. Keep visualization logic separate from data logic
2. Ensure WebSocket messages are properly formatted
3. Test with multiple concurrent connections
4. Maintain backward compatibility with existing projects

## Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows project style guidelines
- [ ] All tests pass locally
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages follow conventional format
- [ ] No sensitive information in code
- [ ] License headers maintained (AGPL-3.0)
- [ ] PR description is clear and complete

## Security Considerations

- Never commit credentials or API keys
- Validate all user inputs
- Sanitize file paths to prevent directory traversal
- Use secure defaults for all configurations
- Report security issues privately to maintainers

## Resources for Contributors

### Understanding the Codebase

- **DEXPI Standard**: [dexpi.org](https://www.dexpi.org/)
- **MCP Protocol**: [github.com/anthropics/mcp](https://github.com/anthropics/mcp)
- **pyDEXPI Docs**: [GitHub](https://github.com/process-intelligence-research/pyDEXPI)

### Development Tools

- **pytest**: Testing framework
- **black**: Code formatter
- **mypy**: Type checking
- **ruff**: Fast Python linter

### Getting Help

- Open a discussion on GitHub
- Review existing issues and PRs
- Check the documentation
- Ask questions in PR comments

## License Agreement

By contributing to this project, you agree that your contributions will be licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). This ensures that:

1. Your contributions remain open source
2. Any derivatives must also be AGPL-3.0 licensed
3. Network use requires source code disclosure
4. You have the right to contribute the code

## Recognition

Contributors will be recognized in:
- The project's contributors list
- Release notes for significant contributions
- Documentation credits where appropriate

Thank you for helping improve engineering drawing automation with AI!

---

*Questions? Open an issue or discussion on GitHub.*