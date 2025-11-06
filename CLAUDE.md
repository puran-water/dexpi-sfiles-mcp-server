# CLAUDE.md - MCP Client Guidelines

## Project File Management

### IMPORTANT: File Overwriting Policy

When saving models to a project, **ALWAYS overwrite existing files** rather than creating new versions with different names. The git integration handles version control automatically.

#### Correct Behavior ✅
```
# Save initially
project_save(model_name="reactor_design", ...)  # Creates reactor_design.json

# After modifications, save again with SAME name
project_save(model_name="reactor_design", ...)  # Overwrites reactor_design.json
```

#### Incorrect Behavior ❌
```
# DO NOT create versioned files
project_save(model_name="reactor_design_v2", ...)  # Wrong!
project_save(model_name="reactor_design_modified", ...)  # Wrong!
project_save(model_name="reactor_design_2024", ...)  # Wrong!
```

### Why This Matters

1. **Git handles versioning** - Each save creates a git commit automatically
2. **Clean project structure** - Avoids file proliferation
3. **Clear history** - Git log shows all changes with timestamps and messages
4. **Easy rollback** - Users can checkout any previous version via git

### Best Practices

1. **Use consistent model names** throughout a project
2. **Write meaningful commit messages** that describe what changed
3. **Let users decide** when to create checkpoints (via commit messages)
4. **Trust git** to maintain the complete history

### Example Workflow

```python
# Initial creation
project_init(project_path="/projects/plant_design")
model_id = create_pid(project_name="Plant A", drawing_number="PID-001")

# First save
project_save(
    model_name="main_pid",  # Remember this name!
    commit_message="Initial P&ID with feed section"
)

# Make changes...
add_equipment(model_id, ...)

# Save again with SAME name
project_save(
    model_name="main_pid",  # Same name - overwrites file
    commit_message="Added reactor section"
)

# More changes...
add_instrumentation(model_id, ...)

# Save again with SAME name
project_save(
    model_name="main_pid",  # Same name - overwrites file
    commit_message="Added control loops"
)
```

The result is ONE file (`main_pid.json`) with full history in git, not three separate files.

## Visualization

### Visualization Options

The system provides multiple visualization formats:
- **HTML**: Interactive plotly visualization with spring layout (current default)
- **GraphML**: For topology analysis and external tools
- **JSON**: Git-trackable state representation
- **SVG/DXF**: Planned for Phase 1 of BFD system (Sprint 5) - will enable browser review and CAD tool integration

**Current Status:** SVG generation for BFD/PFD diagrams is not yet implemented. Use HTML visualizations for interactive viewing or GraphML for external tool integration. SVG export will be added in a future update when BFD visualization system is complete.

## File Organization

Projects follow this structure:
```
project_root/
├── .git/           # Version control
├── metadata.json   # Project metadata
├── bfd/           # Block flow diagrams (SFILES)
├── pfd/           # Process flow diagrams (SFILES)
└── pid/           # P&ID diagrams (DEXPI)
```

Each diagram type has its own folder, but within each folder, **overwrite files with the same name** when saving updates.