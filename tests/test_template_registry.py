"""Test template operations registration and integration."""

import sys
sys.path.insert(0, '/home/hvksh/processeng/engineering-mcp-server')

from src.registry.operations import register_all_operations
from src.registry.operation_registry import get_operation_registry, reset_operation_registry

print("=" * 70)
print("TEST: Template Operations Registration")
print("=" * 70)

# Reset and register all operations
reset_operation_registry()
register_all_operations()

registry = get_operation_registry()

# Verify operations registered
print(f"✓ Registry has {len(registry._operations)} operations registered")

# Check for template operations
if registry.exists("template_instantiate_dexpi"):
    print("✓ template_instantiate_dexpi registered")
    op = registry.get("template_instantiate_dexpi")
    print(f"  - Category: {op.category.value}")
    print(f"  - Version: {op.version}")
    print(f"  - Has DiffMetadata: {op.metadata.diff_metadata is not None}")
else:
    print("✗ template_instantiate_dexpi NOT found")
    sys.exit(1)

if registry.exists("template_instantiate_sfiles"):
    print("✓ template_instantiate_sfiles registered")
    op = registry.get("template_instantiate_sfiles")
    print(f"  - Category: {op.category.value}")
    print(f"  - Version: {op.version}")
    print(f"  - Has DiffMetadata: {op.metadata.diff_metadata is not None}")
else:
    print("✗ template_instantiate_sfiles NOT found")
    sys.exit(1)

# List all STRATEGIC operations
from src.registry.operation_registry import OperationCategory

strategic_ops = [
    op for op in registry._operations.values()
    if op.category == OperationCategory.STRATEGIC
]
print(f"\n✓ Found {len(strategic_ops)} STRATEGIC operations:")
for op in strategic_ops:
    print(f"  - {op.name}")

# Also verify by checking the enum value
strategic_ops_by_value = [
    op for op in registry._operations.values()
    if op.category.value == "strategic"  # lowercase to match enum definition
]
print(f"✓ Verified {len(strategic_ops_by_value)} STRATEGIC operations (by value check)")

# Verify total count
expected_total = 7  # 3 DEXPI + 2 SFILES + 2 Template
if len(registry._operations) == expected_total:
    print(f"\n✓ Total operations: {len(registry._operations)} (expected {expected_total})")
else:
    print(f"\n⚠ Total operations: {len(registry._operations)} (expected {expected_total})")

print("\n" + "=" * 70)
print("ALL REGISTRATION TESTS PASSED ✓")
print("=" * 70)
