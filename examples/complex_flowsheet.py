#!/usr/bin/env python3
"""
Complex Flowsheet Example
Creates a complete process flowsheet using SFILES notation with recycles and heat integration.
"""

import asyncio
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.tools.sfiles_tools import SfilesTools
from src.tools.project_tools import ProjectTools
from src.tools.validation_tools import ValidationTools


async def create_complex_flowsheet():
    """Create a complex flowsheet with SFILES."""
    print("Creating Complex Flowsheet Example...")
    print("=" * 50)
    
    # Initialize model stores and tool handlers
    dexpi_models = {}
    flowsheet_store = {}

    sfiles = SfilesTools(flowsheet_store, dexpi_models)
    projects = ProjectTools(dexpi_models, flowsheet_store)
    validation = ValidationTools(dexpi_models, flowsheet_store)
    
    # 1. Initialize project
    project_path = "/tmp/example_projects/complex_flowsheet"
    print(f"\n1. Initializing project at {project_path}")
    
    init_result = await projects.handle_tool("project_init", {
        "project_path": project_path,
        "project_name": "Complex Flowsheet Example",
        "description": "Process with recycles and heat integration"
    })
    if not init_result.get("ok"):
        raise RuntimeError(init_result)
    print("   ✅ Project initialized")
    
    # 2. Create flowsheet
    print("\n2. Creating PFD flowsheet")
    result = await sfiles.handle_tool("sfiles_create_flowsheet", {
        "name": "Integrated Chemical Process",
        "type": "PFD",
        "description": "Complete process with separation and recycle"
    })
    flowsheet_id = result["data"]["flowsheet_id"]
    print(f"   ✅ Flowsheet created with ID: {flowsheet_id}")
    
    # 3. Add unit operations
    print("\n3. Adding unit operations")
    
    units = [
        ("feed-1", "feed", "Raw material feed"),
        ("mixer-1", "mixer", "Feed mixer"),
        ("hex-1", "hex", "Feed preheater"),
        ("reactor-1", "reactor", "Main reactor"),
        ("hex-2", "hex", "Product cooler"),
        ("separator-1", "separator", "Phase separator"),
        ("distcol-1", "distcol", "Distillation column"),
        ("product-1", "product", "Main product"),
        ("byproduct-1", "byproduct", "Byproduct stream"),
        ("recycle-1", "recycle", "Recycle stream")
    ]
    
    for unit_name, unit_type, description in units:
        await sfiles.handle_tool("sfiles_add_unit", {
            "flowsheet_id": flowsheet_id,
            "unit_name": unit_name,
            "unit_type": unit_type,
            "parameters": {"description": description}
        })
        print(f"   ✅ Added {unit_type}: {unit_name}")
    
    # 4. Create process streams
    print("\n4. Creating process streams")
    
    streams = [
        ("feed-1", "mixer-1", "S-101", "Fresh feed"),
        ("recycle-1", "mixer-1", "S-102", "Recycle stream"),
        ("mixer-1", "hex-1", "S-103", "Mixed feed"),
        ("hex-1", "reactor-1", "S-104", "Heated feed"),
        ("reactor-1", "hex-2", "S-105", "Reactor effluent"),
        ("hex-2", "separator-1", "S-106", "Cooled product"),
        ("separator-1", "distcol-1", "S-107", "Liquid phase"),
        ("separator-1", "byproduct-1", "S-108", "Gas phase"),
        ("distcol-1", "product-1", "S-109", "Distillate product"),
        ("distcol-1", "recycle-1", "S-110", "Bottom recycle")
    ]
    
    for from_unit, to_unit, stream_name, description in streams:
        await sfiles.handle_tool("sfiles_add_stream", {
            "flowsheet_id": flowsheet_id,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "stream_name": stream_name,
            "properties": {
                "description": description,
                "flow": 1000,  # kg/hr
                "temperature": 25,  # °C
                "pressure": 1  # bar
            }
        })
        print(f"   ✅ Connected {from_unit} → {to_unit} ({stream_name})")
    
    # 5. Add control loops
    print("\n5. Adding control instrumentation")
    
    controls = [
        ("LC", "LC-101", "separator-1", "Level control"),
        ("TC", "TC-101", "reactor-1", "Temperature control"),
        ("FC", "FC-101", "feed-1", "Flow control"),
        ("PC", "PC-101", "distcol-1", "Pressure control")
    ]
    
    for control_type, control_name, connected_unit, description in controls:
        await sfiles.handle_tool("sfiles_add_control", {
            "flowsheet_id": flowsheet_id,
            "control_type": control_type,
            "control_name": control_name,
            "connected_unit": connected_unit
        })
        print(f"   ✅ Added {control_type}: {control_name} on {connected_unit}")
    
    # 6. Validate topology
    print("\n6. Validating flowsheet topology")
    validation_result = await validation.handle_tool("validate_model", {
        "model_id": flowsheet_id,
        "model_type": "sfiles",
        "scopes": ["syntax", "topology", "connectivity"]
    })
    if validation_result.get("ok"):
        metrics = validation_result["data"].get("metrics", {})
        print("   ✅ Validation passed")
        if metrics:
            print(f"      - Graph metrics: {metrics.get('basic', metrics)}")
    else:
        print(f"   ⚠️ Validation issues: {validation_result}")
    
    # 7. Export SFILES notation
    print("\n7. Generating SFILES notation")
    result = await sfiles.handle_tool("sfiles_to_string", {
        "flowsheet_id": flowsheet_id,
        "version": "v2",
        "canonical": True
    })
    sfiles_string = result["data"]["sfiles"]
    print(f"   ✅ SFILES v2: {sfiles_string}")

    # Validate SFILES syntax via parser helper
    parse_result = await sfiles.handle_tool("sfiles_parse_and_validate", {
        "sfiles_string": sfiles_string,
        "return_tokens": True
    })
    if parse_result.get("valid"):
        print(f"   ✅ Parsed {parse_result['num_tokens']} tokens")
    else:
        print(f"   ⚠️ Parse issues: {parse_result}")
    
    # 8. Export to various formats
    print("\n8. Exporting flowsheet formats")
    
    # Export NetworkX
    result = await sfiles.handle_tool("sfiles_export_networkx", {
        "flowsheet_id": flowsheet_id
    })
    print(f"   ✅ Exported NetworkX graph")
    
    # Export GraphML
    result = await sfiles.handle_tool("sfiles_export_graphml", {
        "flowsheet_id": flowsheet_id
    })
    if result["data"].get("graphml"):
        print(f"   ✅ Exported GraphML")
    
    # 9. Save to project
    print("\n9. Saving to project")
    save_result = await projects.handle_tool("project_save", {
        "project_path": project_path,
        "model_id": flowsheet_id,
        "model_name": "complex_process",
        "model_type": "sfiles",
        "commit_message": "Create complex flowsheet with recycles and controls"
    })
    if not save_result.get("ok"):
        raise RuntimeError(save_result)
    saved_paths = save_result["data"]["saved_paths"]
    print("   ✅ Saved to project:")
    for label, path in saved_paths.items():
        if path:
            print(f"      - {label}: {path}")
    
    # 10. Demonstrate round-trip conversion
    print("\n10. Testing round-trip conversion")
    
    # Parse and validate
    canonical_result = await sfiles.handle_tool("sfiles_canonical_form", {
        "sfiles_string": sfiles_string,
        "version": "v2"
    })
    canonical = canonical_result["data"]["canonical"]
    print(f"   ✅ Canonical form: {canonical[:50]}...")
    
    print("\n" + "=" * 50)
    print("✅ Complex flowsheet example completed!")
    print(f"📁 Project saved at: {project_path}")
    html_path = saved_paths.get("html")
    if html_path:
        print(f"📄 Open the Plotly report: {html_path}")
    print("\n📊 Process Summary:")
    print("   - 10 unit operations")
    print("   - 10 process streams")
    print("   - 4 control loops")
    print("   - 1 recycle stream")
    print("   - Heat integration via heat exchangers")


if __name__ == "__main__":
    asyncio.run(create_complex_flowsheet())
