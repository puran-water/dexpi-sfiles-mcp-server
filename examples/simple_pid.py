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
from src.persistence import ProjectPersistence


async def create_simple_pid():
    """Create a simple P&ID demonstration."""
    print("Creating Simple P&ID Example...")
    print("=" * 50)
    
    # Initialize tools with model store
    model_store = {}
    dexpi = DexpiTools(model_store)
    persistence = ProjectPersistence()
    
    # 1. Initialize project
    project_path = "/tmp/example_projects/simple_pid"
    print(f"\n1. Initializing project at {project_path}")
    
    result = await dexpi.handle_tool("dexpi_init_project", {
        "project_path": project_path,
        "project_name": "Simple P&ID Example",
        "description": "Basic process with tank, pump, and reactor"
    })
    print(f"   ✅ Project initialized")
    
    # 2. Create P&ID
    print("\n2. Creating P&ID drawing")
    result = await dexpi.handle_tool("dexpi_create_pid", {
        "project_name": "Simple Process",
        "drawing_number": "PID-EX-001",
        "revision": "A",
        "description": "Simple process example"
    })
    model_id = result["model_id"]
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
    result = await dexpi.handle_tool("dexpi_validate_model", {
        "model_id": model_id,
        "validation_level": "basic"
    })
    if result["valid"]:
        print("   ✅ P&ID validation passed")
    else:
        print(f"   ⚠️ Validation issues: {result.get('issues', [])}")
    
    # 8. Save to project
    print("\n8. Saving to project")
    result = await dexpi.handle_tool("dexpi_save_to_project", {
        "model_id": model_id,
        "project_path": project_path,
        "model_name": "simple_pid",
        "commit_message": "Create simple P&ID with tank-pump-reactor system"
    })
    print(f"   ✅ Saved to: {result['saved_files']['json']}")
    
    # 9. Export formats
    print("\n9. Exporting formats")
    
    # Export JSON
    result = await dexpi.handle_tool("dexpi_export_json", {
        "model_id": model_id
    })
    print(f"   ✅ Exported JSON ({len(result['json'])} characters)")
    
    # Export GraphML
    result = await dexpi.handle_tool("dexpi_export_graphml", {
        "model_id": model_id,
        "include_msr": True
    })
    if result.get("graphml"):
        print(f"   ✅ Exported GraphML")
    
    print("\n" + "=" * 50)
    print("✅ Simple P&ID example completed!")
    print(f"📁 Project saved at: {project_path}")
    print("🌐 View in dashboard: http://localhost:8000")
    print("   (Start dashboard with: python -m src.dashboard.server)")


if __name__ == "__main__":
    asyncio.run(create_simple_pid())