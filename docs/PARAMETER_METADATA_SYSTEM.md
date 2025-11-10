# Parameter Metadata System Documentation

**Created**: January 9, 2025
**Sprint**: Bug Surfacing Sprint (Day 1)
**Component**: PFD Expansion Engine

## Overview

The Parameter Metadata System was implemented during the Bug Surfacing Sprint to ensure safe, traceable parameter handling in BFD→PFD template expansion. It replaced unsafe eval() fallback patterns with explicit token parsing and parameter resolution.

## Key Features

### 1. Safe Condition Evaluation

**Before (Unsafe)**:
```python
# Condition string passed directly to eval()
try:
    return eval(condition, {"__builtins__": {}}, {})
except:
    return True  # Silent fallback - masks bugs!
```

**After (Safe)**:
```python
# Token parsing BEFORE evaluation
CONDITION_TOKEN_PATTERN = re.compile(r"\$\{([^}|]+)(?:\|([^}]+))?\}")

def _evaluate_condition(condition, parameters):
    # Parse ${param|default} tokens first
    token_only = CONDITION_TOKEN_PATTERN.fullmatch(condition)
    if token_only:
        value = self._resolve_condition_token(token_only, parameters)
        return self._condition_value_to_bool(value)

    # Then handle comparison expressions
    # Raises ValueError on invalid syntax instead of silent fallback
```

### 2. Parameter Resolution Flow

**Three-Stage Resolution**:

```python
# Stage 1: Template Defaults
template.parameters = {
    'mechanical_rake': {'default': 'mechanical_rake', 'type': 'string'},
    'do_control': {'default': True, 'type': 'boolean'}
}

# Stage 2: Runtime Overrides
runtime_parameters = {'do_control': False}

# Stage 3: Merge (runtime overrides defaults)
resolved_parameters = {
    'mechanical_rake': 'mechanical_rake',  # From template default
    'do_control': False                     # From runtime override
}
```

Implementation:
```python
def _resolve_parameter_values(self, template, runtime_parameters):
    """Merge template defaults with runtime overrides."""
    resolved = {}

    # Start with template defaults
    for name, spec in template.parameters.items():
        resolved[name] = spec.default

    # Runtime parameters override defaults
    resolved.update(runtime_parameters)
    return resolved
```

### 3. Expansion Metadata Tracking

Every BFD→PFD expansion now records complete parameter information:

```python
metadata = {
    'source_bfd_block': 'PRIMARY_CLARIFICATION',
    'process_unit_id': 'primary_clarifier',
    'area_number': 100,
    'train_count': 2,
    'template_used': 'src/config/process_templates/library/101/primary_clarifier.yaml',
    'components_used': ['Tank', 'Mixer', 'BallValve'],
    'equipment_count': 8,
    'connection_count': 12,
    'parameters': {                    # ← NEW: Effective parameters
        'mechanical_rake': 'mechanical_rake',
        'do_control': False,
        'surface_area': 450.0
    }
}
```

**Benefits**:
- **Traceability**: Know exactly which parameter values were used
- **Debugging**: Understand why equipment was included/excluded
- **Auditability**: Track parameter changes through git history
- **Reproducibility**: Re-expand with exact same parameters

## Supported Condition Syntax

### 1. Boolean Parameter Tokens

```yaml
equipment:
  - id: "do_sensor"
    condition: "${do_control|true}"  # Include if do_control param is truthy
```

**Truthy Values**: `"true"`, `"yes"`, `"1"`, `"on"`, `True`, `1`

### 2. Comparison Expressions

```yaml
equipment:
  - id: "mechanical_rake"
    condition: "rake_type == 'mechanical'"  # Include if rake_type equals 'mechanical'
```

**Supported Operators**: `==`, `!=`

### 3. Parameter Substitution

```yaml
equipment:
  - id: "${pump_type|centrifugal}_pump"  # Resolves to "centrifugal_pump"
    default_params:
      capacity: "${design_flow|100}"      # Resolves to "100" if not provided
```

## Error Handling (Fail Loudly)

All parameter evaluation errors now **fail loudly** instead of silently:

### Invalid Condition Syntax

```python
# Before: Silent fallback to True
condition = "${invalid syntax"
# Silently returns True

# After: Raises ValueError
raise ValueError(
    f"Invalid condition expression: '{condition}'. "
    f"Conditions must be simple comparisons (==, !=) "
    f"or parameter tokens ${{param|default}}"
)
```

### Unsupported Operators

```python
# Before: Silent fallback to True
condition = "value > 10"
# Silently returns True

# After: Raises ValueError
raise ValueError(
    f"Unsupported condition format: '{condition}'. "
    f"Supported formats: '${{param|default}}', 'param == value', 'param != value'"
)
```

## Implementation Details

### Token Pattern Matching

```python
CONDITION_TOKEN_PATTERN = re.compile(r"\$\{([^}|]+)(?:\|([^}]+))?\}")

# Matches:
"${param}"              → groups: ('param', None)
"${param|default}"      → groups: ('param', 'default')

# Does not match:
"param == value"        → None (not a token, try comparison)
"${invalid"             → None (malformed)
```

### Token Resolution

```python
def _resolve_condition_token(self, match, parameters, original):
    """Resolve ${param|default} to actual value."""
    param_name = match.group(1)
    default_val = match.group(2)

    if param_name in parameters:
        return parameters[param_name]

    if default_val is not None:
        return default_val

    # No value and no default - fail loudly
    raise ValueError(
        f"Parameter '{param_name}' not found in {list(parameters.keys())} "
        f"and no default provided in condition: '{original}'"
    )
```

### Boolean Conversion

```python
TRUTHY_CONDITION_VALUES = {"true", "yes", "1", "on"}

def _condition_value_to_bool(self, value):
    """Convert parameter value to boolean for condition evaluation."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in TRUTHY_CONDITION_VALUES
    return bool(value)
```

## Usage Examples

### Example 1: Conditional Equipment

```yaml
# Template: aeration_tank.yaml
parameters:
  do_control:
    type: boolean
    default: true
    description: Include DO control loop

equipment:
  per_train:
    - id: "tank"
      type: "Tank"
      # Always included (no condition)

    - id: "do_sensor"
      type: "ProcessSignalGeneratingSystem"
      condition: "${do_control|true}"  # Only if do_control is True
```

```python
# Runtime call with defaults
result = engine.expand_bfd_block(
    bfd_block="AERATION",
    process_unit_id="aeration_tank",
    area_number=200
    # do_control defaults to True
)
# → Creates tank + DO sensor

# Runtime call with override
result = engine.expand_bfd_block(
    bfd_block="AERATION",
    process_unit_id="aeration_tank",
    area_number=200,
    parameters={'do_control': False}
)
# → Creates tank only (no DO sensor)
```

### Example 2: Parameter Substitution

```yaml
# Template: screening.yaml
parameters:
  mechanical_rake:
    type: string
    default: "mechanical_rake"
    description: Rake mechanism type

equipment:
  shared:
    - id: "influent_channel"
      type: "InfluentChannel"
      default_params:
        rake_type: "${mechanical_rake|none}"  # Resolves to "mechanical_rake"
```

```python
result = engine.expand_bfd_block(
    bfd_block="SCREENING",
    process_unit_id="screening",
    area_number=100,
    parameters={'mechanical_rake': 'traveling_screen'}
)
# metadata['parameters'] = {'mechanical_rake': 'traveling_screen'}
# Equipment created with rake_type="traveling_screen"
```

### Example 3: Comparison Conditions

```yaml
equipment:
  - id: "fine_bubble_diffusers"
    type: "CustomEquipment"
    condition: "aeration_type == 'fine_bubble'"
```

```python
# With fine bubble
result = engine.expand_bfd_block(
    parameters={'aeration_type': 'fine_bubble'}
)
# → Includes fine_bubble_diffusers

# With coarse bubble
result = engine.expand_bfd_block(
    parameters={'aeration_type': 'coarse_bubble'}
)
# → Excludes fine_bubble_diffusers
```

## Testing

### Unit Tests for Token Parsing

```python
def test_token_pattern_matching():
    pattern = CONDITION_TOKEN_PATTERN

    # Valid tokens
    assert pattern.fullmatch("${param}")
    assert pattern.fullmatch("${param|default}")

    # Invalid (not tokens)
    assert not pattern.fullmatch("param == value")
    assert not pattern.fullmatch("${invalid")
```

### Integration Tests for Parameter Resolution

```python
def test_parameter_resolution_with_defaults():
    """Test that template defaults are used when no runtime params provided."""
    result = engine.expand_bfd_block(
        bfd_block="TEST",
        process_unit_id="test_template",
        area_number=100
    )
    assert result.expansion_metadata['parameters']['do_control'] == True  # Default

def test_parameter_resolution_with_overrides():
    """Test that runtime params override template defaults."""
    result = engine.expand_bfd_block(
        bfd_block="TEST",
        process_unit_id="test_template",
        area_number=100,
        parameters={'do_control': False}
    )
    assert result.expansion_metadata['parameters']['do_control'] == False  # Override
```

### Regression Tests for Fail-Loud Behavior

```python
def test_invalid_condition_syntax_raises():
    """Test that invalid condition syntax raises ValueError instead of silent fallback."""
    with pytest.raises(ValueError, match="Invalid condition expression"):
        engine.expand_bfd_block(
            parameters={},
            # Template has condition: "${invalid syntax"
        )

def test_unsupported_operator_raises():
    """Test that unsupported operators raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported condition format"):
        engine.expand_bfd_block(
            # Template has condition: "value > 10"
        )
```

## Migration Guide

### For Template Authors

**Old (Unsafe)**:
```yaml
equipment:
  - id: "sensor"
    # No condition - included unconditionally
```

**New (Safe with Conditions)**:
```yaml
parameters:
  include_sensor:
    type: boolean
    default: true

equipment:
  - id: "sensor"
    condition: "${include_sensor|true}"  # Explicit control
```

### For API Users

**Old (No Parameter Tracking)**:
```python
result = engine.expand_bfd_block(
    bfd_block="AERATION",
    area_number=200
)
# No way to know which parameters were used
```

**New (Full Traceability)**:
```python
result = engine.expand_bfd_block(
    bfd_block="AERATION",
    area_number=200,
    parameters={'do_control': False}
)
# result.expansion_metadata['parameters'] shows exact values used
# Can reproduce expansion with same parameters
```

## Benefits Summary

1. **Security**: No unsafe eval() of untrusted condition strings
2. **Reliability**: Errors fail loudly instead of silent fallbacks
3. **Traceability**: Complete parameter audit trail
4. **Reproducibility**: Exact parameter values recorded in metadata
5. **Debuggability**: Clear error messages explain validation failures
6. **Testability**: Deterministic behavior enables comprehensive testing

## Related Files

- `src/tools/pfd_expansion_engine.py` - Core implementation
- `src/config/process_templates/library/` - Template definitions
- `tests/test_parameter_variations.py` - Parameter tests
- `tests/test_new_templates.py` - End-to-end expansion tests

## See Also

- [Bug Surfacing Sprint](../BUG_SURFACING_SPRINT.md) - Context for these changes
- [Template System](../TEMPLATE_SYSTEM.md) - Overall template architecture
- [SFILES Notation](../SFILES_NOTATION.md) - BFD/PFD concepts
