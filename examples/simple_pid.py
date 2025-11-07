#!/usr/bin/env python3
"""
Simple P&ID Example
Creates a basic P&ID with tank, pump, reactor, and instrumentation.
"""

import asyncio
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.tools.dexpi_tools import DexpiTools
from src.tools.project_tools import ProjectTools
from src.tools.validation_tools import ValidationTools


async def create_simple_pid():
    """Create a simple P&ID demonstration."""
    print("Creating Simple P&ID Example...")
    print("=" * 50)
    
    # Initialize model stores and tool handlers
    dexpi_models = {}
    flowsheets = {}

    dexpi = DexpiTools(dexpi_models, flowsheets)
    projects = ProjectTools(dexpi_models, flowsheets)
    validation = ValidationTools(dexpi_models, flowsheets)
    
    # 1. Initialize project
    project_path = "/tmp/example_projects/simple_pid"
    print(f"\n1. Initializing project at {project_path}")
    
    init_result = await projects.handle_tool("project_init", {
        "project_path": project_path,
        "project_name": "Simple P&ID Example",
        "description": "Basic process with tank, pump, and reactor"
    })
    if not init_result.get("ok"):
        raise RuntimeError(init_result)
    print("   ✅ Project initialized")
    
    # 2. Create P&ID
    print("\n2. Creating P&ID drawing")
    result = await dexpi.handle_tool("dexpi_create_pid", {
        "project_name": "Simple Process",
        "drawing_number": "PID-EX-001",
        "revision": "A",
        "description": "Simple process example"
    })
    model_id = result["data"]["model_id"]
    print(f"   ✅ P&ID created with ID: {model_id}")
    
    # 3. Add equipment
    print("\n3. Adding equipment")
    
    # Add feed tank
    await dexpi.handle_tool("dexpi_add_equipment", {
        "model_id": model_id,
        "equipment_type": "Tank",
        "tag_name": "TK-101",
        "specifications": {}
    })
    print("   ✅ Added feed tank TK-101")
    
    # Add pump
    await dexpi.handle_tool("dexpi_add_equipment", {
        "model_id": model_id,
        "equipment_type": "Pump",
        "tag_name": "P-101",
        "specifications": {}
    })
    print("   ✅ Added pump P-101")
    
    # Add reactor
    await dexpi.handle_tool("dexpi_add_equipment", {
        "model_id": model_id,
        "equipment_type": "Reactor",
        "tag_name": "R-101",
        "specifications": {}
    })
    print("   ✅ Added reactor R-101")
    
    # Add product tank
    await dexpi.handle_tool("dexpi_add_equipment", {
        "model_id": model_id,
        "equipment_type": "Tank",
        "tag_name": "TK-102",
        "specifications": {}
    })
    print("   ✅ Added product tank TK-102")
    
    # 4. Add valves
    print("\n4. Adding valves")
    
    await dexpi.handle_tool("dexpi_add_valve", {
        "model_id": model_id,
        "valve_type": "BallValve",
        "tag_name": "V-101",
        "nominal_diameter": "DN50"
    })
    print("   ✅ Added ball valve V-101")
    
    await dexpi.handle_tool("dexpi_add_valve", {
        "model_id": model_id,
        "valve_type": "GlobeValve",
        "tag_name": "V-102",
        "nominal_diameter": "DN50"
    })
    print("   ✅ Added globe valve V-102")
    
    # 5. Add instrumentation
    print("\n5. Adding instrumentation")
    
    await dexpi.handle_tool("dexpi_add_instrumentation", {
        "model_id": model_id,
        "instrument_type": "LevelTransmitter",
        "tag_name": "LT-101",
        "connected_equipment": "TK-101"
    })
    print("   ✅ Added level transmitter LT-101 on TK-101")
    
    await dexpi.handle_tool("dexpi_add_instrumentation", {
        "model_id": model_id,
        "instrument_type": "TemperatureIndicator",
        "tag_name": "TI-101",
        "connected_equipment": "R-101"
    })
    print("   ✅ Added temperature indicator TI-101 on R-101")
    
    await dexpi.handle_tool("dexpi_add_instrumentation", {
        "model_id": model_id,
        "instrument_type": "PressureIndicator",
        "tag_name": "PI-101",
        "connected_equipment": "R-101"
    })
    print("   ✅ Added pressure indicator PI-101 on R-101")
    
    # 6. Create piping connections
    print("\n6. Creating piping connections")
    
    await dexpi.handle_tool("dexpi_connect_components", {
        "model_id": model_id,
        "from_component": "TK-101",
        "to_component": "P-101",
        "line_number": "100-PL-001",
        "pipe_class": "CS150"
    })
    print("   ✅ Connected TK-101 to P-101")
    
    await dexpi.handle_tool("dexpi_connect_components", {
        "model_id": model_id,
        "from_component": "P-101",
        "to_component": "R-101",
        "line_number": "100-PL-002",
        "pipe_class": "CS150"
    })
    print("   ✅ Connected P-101 to R-101")
    
    await dexpi.handle_tool("dexpi_connect_components", {
        "model_id": model_id,
        "from_component": "R-101",
        "to_component": "TK-102",
        "line_number": "100-PL-003",
        "pipe_class": "CS150"
    })
    print("   ✅ Connected R-101 to TK-102")
    
    # 7. Validate the model
    print("\n7. Validating P&ID")
    validation_result = await validation.handle_tool("validate_model", {
        "model_id": model_id,
        "model_type": "dexpi",
        "checks": ["syntax", "topology"]
    })
    if validation_result.get("ok"):
        print("   ✅ Validation passed")
    else:
        print(f"   ⚠️ Issues: {validation_result}")
    
    # 8. Save to project
    print("\n8. Saving to project")
    save_result = await projects.handle_tool("project_save", {
        "project_path": project_path,
        "model_id": model_id,
        "model_name": "simple_pid",
        "model_type": "dexpi",
        "commit_message": "Create simple P&ID with tank-pump-reactor system"
    })
    if not save_result.get("ok"):
        raise RuntimeError(save_result)
    saved_paths = save_result["data"]["saved_paths"]
    print(f"   ✅ Saved JSON: {saved_paths['json']}")
    
    # 9. Export formats
    print("\n9. Exporting formats")
    
    # Export JSON
    result = await dexpi.handle_tool("dexpi_export_json", {
        "model_id": model_id
    })
    json_payload = result["data"]["json"]
    print(f"   ✅ Exported JSON ({len(json_payload)} characters)")

    # Export GraphML
    result = await dexpi.handle_tool("dexpi_export_graphml", {
        "model_id": model_id,
        "include_msr": True
    })
    if result["data"].get("graphml"):
        print(f"   ✅ Exported GraphML")
    
    print("\n" + "=" * 50)
    print("✅ Simple P&ID example completed!")
    print(f"📁 Project saved at: {project_path}")
    html_path = saved_paths.get("html")
    if html_path:
        print(f"📄 Open the Plotly report: {html_path}")


if __name__ == "__main__":
    asyncio.run(create_simple_pid())
