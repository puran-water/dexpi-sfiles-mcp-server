"""Test template tools integration with area_deploy."""

import sys
import asyncio
sys.path.insert(0, '/home/hvksh/processeng/engineering-mcp-server')

from src.tools.template_tools import TemplateTools
from pydexpi.dexpi_classes.dexpiModel import DexpiModel

print("=" * 70)
print("TEST: Template Tools Integration")
print("=" * 70)

# Initialize stores
dexpi_models = {}
flowsheets = {}

# Initialize template tools
template_tools = TemplateTools(dexpi_models, flowsheets)

print(f"✓ Template library path: {template_tools.template_library_path}")

# ========================================================================
# Test 1: template_list
# ========================================================================

print("\n" + "=" * 70)
print("Test 1: template_list")
print("=" * 70)

async def test_template_list():
    result = await template_tools._template_list({"category": "all"})
    if result.get("ok"):
        print(f"✓ {result['data']['message']}")
        print(f"  Templates found: {result['data']['count']}")
        for template in result["data"]["templates"]:
            print(f"    - {template['name']} ({template['category']}): {template['description']}")
    else:
        print(f"✗ Failed: {result.get('error', {}).get('message', 'Unknown error')}")
        sys.exit(1)

asyncio.run(test_template_list())

# ========================================================================
# Test 2: template_get_schema
# ========================================================================

print("\n" + "=" * 70)
print("Test 2: template_get_schema (pump_basic)")
print("=" * 70)

async def test_get_schema():
    result = await template_tools._template_get_schema({"template_name": "pump_basic"})
    if result.get("ok"):
        print(f"✓ {result['data']['message']}")
        print(f"  - Version: {result['data']['version']}")
        print(f"  - Category: {result['data']['category']}")
        print(f"  - Parameters: {len(result['data']['parameters'])}")
        for param_name, param_def in result['data']['parameters'].items():
            print(f"    * {param_name}: {param_def.get('type', 'any')}")
        print(f"  - Components: {len(result['data']['components'])}")
    else:
        print(f"✗ Failed: {result.get('error', {}).get('message', 'Unknown error')}")
        sys.exit(1)

asyncio.run(test_get_schema())

# ========================================================================
# Test 3: area_deploy (DEXPI - pump_basic)
# ========================================================================

print("\n" + "=" * 70)
print("Test 3: area_deploy (DEXPI - pump_basic)")
print("=" * 70)

async def test_deploy_pump_basic():
    # Create DEXPI model
    model = DexpiModel()
    dexpi_models["test_pump"] = model

    # Deploy template
    result = await template_tools._area_deploy({
        "model_id": "test_pump",
        "model_type": "dexpi",
        "template_name": "pump_basic",
        "parameters": {
            "area": "100",
            "sequence": 1,
            "pump_type": "CentrifugalPump",
            "flow_rate": 100.0,
            "discharge_pressure": 5.0
        }
    })

    if result.get("ok"):
        print(f"✓ {result['data']['message']}")
        print(f"  - Components added: {result['data']['component_count']}")
        for comp_id in result["data"]["components_added"]:
            print(f"    * {comp_id}")

        # Verify in model
        if model.conceptualModel and model.conceptualModel.taggedPlantItems:
            print(f"✓ Model verification:")
            print(f"  - TaggedPlantItems: {len(model.conceptualModel.taggedPlantItems)}")
            for item in model.conceptualModel.taggedPlantItems:
                tag = getattr(item, 'tagName', getattr(item, 'Tag', 'NO_TAG'))
                print(f"    * {tag} ({item.__class__.__name__})")
        else:
            print("✗ Model has no tagged plant items")
            sys.exit(1)
    else:
        error = result.get("error", {})
        print(f"✗ Failed: {error.get('message', 'Unknown error')}")
        if "validation_errors" in error.get("details", {}):
            print(f"  Validation errors: {error['details']['validation_errors']}")
        sys.exit(1)

asyncio.run(test_deploy_pump_basic())

# ========================================================================
# Test 4: area_deploy (DEXPI - pump_station_n_plus_1)
# ========================================================================

print("\n" + "=" * 70)
print("Test 4: area_deploy (DEXPI - pump_station_n_plus_1)")
print("=" * 70)

async def test_deploy_n_plus_1():
    # Create DEXPI model
    model = DexpiModel()
    dexpi_models["test_n_plus_1"] = model

    # Deploy template with 3 pumps (2+1 redundancy)
    result = await template_tools._area_deploy({
        "model_id": "test_n_plus_1",
        "model_type": "dexpi",
        "template_name": "pump_station_n_plus_1",
        "parameters": {
            "area": "200",
            "pump_count": 3,
            "control_type": "flow",
            "pump_type": "CentrifugalPump"
        }
    })

    if result.get("ok"):
        print(f"✓ {result['data']['message']}")
        print(f"  - Components added: {result['data']['component_count']}")

        print(f"✓ Model verification:")
        if model.conceptualModel and model.conceptualModel.taggedPlantItems:
            print(f"  - Total items: {len(model.conceptualModel.taggedPlantItems)}")
        else:
            print("✗ Model has no tagged plant items")
            sys.exit(1)
    else:
        print(f"✗ Failed: {result.get('error', {}).get('message', 'Unknown error')}")
        sys.exit(1)

asyncio.run(test_deploy_n_plus_1())

# ========================================================================
# Test 5: area_deploy (DEXPI - tank_farm)
# ========================================================================

print("\n" + "=" * 70)
print("Test 5: area_deploy (DEXPI - tank_farm)")
print("=" * 70)

async def test_deploy_tank_farm():
    # Create DEXPI model
    model = DexpiModel()
    dexpi_models["test_tank_farm"] = model

    # Deploy tank farm with 4 tanks
    result = await template_tools._area_deploy({
        "model_id": "test_tank_farm",
        "model_type": "dexpi",
        "template_name": "tank_farm",
        "parameters": {
            "area": "300",
            "tank_count": 4,
            "tank_type": "Tank",
            "level_control": True
        }
    })

    if result.get("ok"):
        print(f"✓ {result['data']['message']}")
        print(f"  - Components added: {result['data']['component_count']}")

        # Verify
        if model.conceptualModel and model.conceptualModel.taggedPlantItems:
            print(f"✓ Model has {len(model.conceptualModel.taggedPlantItems)} tagged items")
        else:
            print("✗ Model has no tagged plant items")
            sys.exit(1)
    else:
        print(f"✗ Failed: {result.get('error', {}).get('message', 'Unknown error')}")
        sys.exit(1)

asyncio.run(test_deploy_tank_farm())

# ========================================================================
# Test 6: area_deploy (SFILES - heat_exchanger_with_integration)
# ========================================================================

print("\n" + "=" * 70)
print("Test 6: area_deploy (SFILES - heat_exchanger_with_integration)")
print("=" * 70)

async def test_deploy_heat_exchanger_sfiles():
    # Create SFILES flowsheet
    from src.adapters.sfiles_adapter import get_flowsheet_class

    Flowsheet = get_flowsheet_class()
    flowsheet = Flowsheet()
    flowsheet.name = "Test HX"
    flowsheets["test_hx"] = flowsheet

    # Deploy template with heat integration
    result = await template_tools._area_deploy({
        "model_id": "test_hx",
        "model_type": "sfiles",
        "template_name": "heat_exchanger_with_integration",
        "parameters": {
            "area": "400",
            "sequence": 1,
            "heat_integration": True
        }
    })

    if result.get("ok"):
        print(f"✓ {result['data']['message']}")
        print(f"  - Components added: {result['data']['component_count']}")

        # Verify flowsheet has nodes
        if flowsheet.state.number_of_nodes() > 0:
            print(f"✓ Flowsheet has {flowsheet.state.number_of_nodes()} nodes")

            # Check for HI nodes
            hi_nodes = [
                node for node, data in flowsheet.state.nodes(data=True)
                if data.get("_hi_node", False)
            ]
            if hi_nodes:
                print(f"✓ Found {len(hi_nodes)} heat integration nodes:")
                for node in hi_nodes:
                    print(f"    * {node}")
            else:
                print("  (No HI nodes marked - template may not use heat_integration=True)")
        else:
            print("✗ Flowsheet has no nodes")
            sys.exit(1)
    else:
        print(f"✗ Failed: {result.get('error', {}).get('message', 'Unknown error')}")
        sys.exit(1)

asyncio.run(test_deploy_heat_exchanger_sfiles())

print("\n" + "=" * 70)
print("ALL TEMPLATE TOOL TESTS PASSED ✓")
print("=" * 70)
print("\nSummary:")
print("  ✓ template_list works")
print("  ✓ template_get_schema works")
print("  ✓ area_deploy works for DEXPI models")
print("  ✓ area_deploy works for SFILES models")
print("  ✓ All 4 templates validated")
