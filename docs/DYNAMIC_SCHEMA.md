# Dynamic Schema Generation

## Overview

The Engineering MCP Server implements runtime introspection of pyDEXPI classes to dynamically generate tool schemas. This eliminates hardcoded type limitations and exposes the full capability of the underlying pyDEXPI library.

## Architecture

### DexpiIntrospector Class

Located in `src/tools/dexpi_introspector.py`, this class performs runtime discovery of all pyDEXPI classes:

```python
class DexpiIntrospector:
    _equipment_classes: Dict[str, Type]      # 159 equipment types
    _piping_classes: Dict[str, Type]         # 79 piping components
    _instrumentation_classes: Dict[str, Type] # 33 instrumentation types
```

### Discovery Process

1. **Module Inspection**: Scans `pydexpi.dexpi_classes` modules at runtime
2. **Class Identification**: Identifies classes with Pydantic `model_fields` attribute
3. **Categorization**: Organizes classes by type (equipment, piping, instrumentation)
4. **Schema Generation**: Converts Pydantic FieldInfo to JSON schema

### Type Mapping

Python type annotations are mapped to JSON schema types:

| Python Type | JSON Schema Type |
|------------|------------------|
| `str` | "string" |
| `int` | "integer" |
| `float` | "number" |
| `bool` | "boolean" |
| `datetime` | "string" |
| `list[T]` | "array" |
| `T \| None` | type with nullable |
| Pydantic models | "object" |

### Attribute Categories

pyDEXPI uses three attribute categories via `json_schema_extra`:

- **composition**: Nested DEXPI objects owned by parent
- **reference**: References to other objects by ID
- **data**: Primitive values and data types

## Implementation Details

### Dynamic Enum Generation

Tool schemas use dynamically generated enums:

```python
equipment_types = self.introspector.generate_dynamic_enum("equipment")
# Returns: ["Agglomerator", "Agitator", ..., "WetCoolingTower"]
```

### Class Description

The `describe_class` method provides comprehensive class information:

```python
{
    "class_name": "CentrifugalPump",
    "category": "equipment",
    "composition_attributes": ["nozzles", "rotor"],
    "reference_attributes": ["driver"],
    "data_attributes": ["designPower", "designSpeed"],
    "required_fields": ["tagName"],
    "schema": {...}
}
```

### Schema Generation

Pydantic FieldInfo is converted to JSON schema:

```python
def generate_class_schema(class_name: str) -> Dict:
    for field_name, field_info in cls.model_fields.items():
        schema = {
            "type": map_python_type_to_json(field_info.annotation),
            "description": field_info.description,
            "default": field_info.default if not callable else None
        }
```

## Benefits

1. **Complete Coverage**: All pyDEXPI classes automatically available
2. **Future-Proof**: New pyDEXPI classes automatically discovered
3. **Type Safety**: Schema validation based on actual class definitions
4. **Maintainability**: No hardcoded type lists to maintain
5. **Discoverability**: Tools to explore available classes and attributes

## Usage Examples

### Discovering Available Types

```python
# Via MCP tool
result = schema_list_classes(schema_type="dexpi", category="equipment")
# result["data"]["dexpi"]["count"] == 159

result = schema_list_classes(schema_type="dexpi", category="instrumentation")
# result["data"]["dexpi"]["count"] == 33
```

### Describing a Class

```python
# Via MCP tool
result = schema_describe_class(class_name="TubularHeatExchanger", schema_type="dexpi", include_inherited=True)
# result["data"] contains composition/reference/data attributes and JSON schema
```

### Adding Specialized Equipment

```python
# Previously unavailable types now accessible
dexpi_add_equipment(
    model_id="...",
    equipment_type="ThinFilmEvaporator",  # Dynamically discovered
    tag_name="E-101"
)
```

## Technical Constraints

1. **Python 3.10+ Required**: Uses modern Union type syntax (`Type | None`)
2. **Pydantic Dependency**: Relies on Pydantic model introspection
3. **Runtime Performance**: Discovery occurs once at server startup
4. **Memory Usage**: All class definitions loaded into memory

## Future Enhancements

1. **Lazy Loading**: Load class definitions on demand
2. **Schema Caching**: Cache generated schemas for performance
3. **Custom Type Extensions**: Support for user-defined equipment types
4. **Schema Versioning**: Track schema changes across pyDEXPI versions
