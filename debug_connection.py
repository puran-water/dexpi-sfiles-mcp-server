#!/usr/bin/env python3
"""Debug the connection issue."""

from pydexpi.dexpi_classes.piping import (
    PipingNetworkSegment,
    PipingNetworkSystem, 
    PipingConnection,
    Pipe,
    PipingNode
)

# Test 1: What goes in items vs connections?
print("Testing PipingNetworkSegment structure...")

# Create a simple connection
connection = PipingConnection(
    id="conn_test"
)

# Create a pipe
pipe = Pipe(
    id="pipe_test"
)

# Test segment creation
print("\n1. Creating segment with connection in connections list:")
try:
    segment1 = PipingNetworkSegment(
        id="segment1",
        connections=[connection],
        items=[]  # Empty items
    )
    print("   SUCCESS: Segment created with connection in connections list")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n2. Creating segment with pipe in items list:")
try:
    segment2 = PipingNetworkSegment(
        id="segment2",
        connections=[],
        items=[pipe]  # Pipe in items - this is wrong!
    )
    print("   SUCCESS: Segment created with pipe in items")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n3. Creating segment with pipe in connections list:")
try:
    segment3 = PipingNetworkSegment(
        id="segment3",
        connections=[pipe],  # Pipe as connection 
        items=[]
    )
    print("   SUCCESS: Segment created with pipe in connections")
except Exception as e:
    print(f"   ERROR: {e}")

# Check what type of objects go in items
from pydexpi.dexpi_classes.piping import PipingNetworkSegmentItem
print(f"\n4. PipingNetworkSegmentItem is: {PipingNetworkSegmentItem}")

# Try to find what's a valid item
import inspect
print("\n5. Valid item types (subclasses of PipingNetworkSegmentItem):")
for name, obj in inspect.getmembers(pydexpi.dexpi_classes.piping):
    if inspect.isclass(obj):
        try:
            if issubclass(obj, PipingNetworkSegmentItem):
                print(f"   - {name}")
        except:
            pass