# Operation Registry Specification

**Version:** 1.0.0-draft
**Status:** Phase 0.5 Design
**Last Updated:** 2025-11-06
**Codex Approved:** ✅

---

## Overview

The **Operation Registry** provides a typed, discoverable catalog of operations for `model_tx_apply`. It replaces string-based tool dispatch with a structured registry pattern, enabling:

- Type-safe operation definitions with schemas
- Version management and deprecation
- Discoverability via `schema_query` tool
- Validation hooks (pre/post-operation)
- Diff metadata integration with TransactionManager

**Design Pattern**: Follows `ParserFactory.factory_methods` from `pydexpi/loaders/proteus_serializer/parser_factory.py:24-76`

---

## Core Concepts

### Operation Descriptor

An **OperationDescriptor** is a typed definition of a model operation:

```python
@dataclass
class OperationDescriptor:
    """Describes a model operation for the registry."""

    name: str                          # Operation identifier (e.g., "add_equipment")
    version: str                       # Semantic version (e.g., "1.0.0")
    category: OperationCategory        # "dexpi", "sfiles", "universal"
    description: str                   # Human-readable description
    input_schema: JSONSchema           # JSON Schema for operation parameters
    handler: Callable[[Model, Dict], OperationResult]  # Async operation handler
    validation_hooks: Optional[ValidationHooks] = None
    metadata: Optional[OperationMetadata] = None
```

### Operation Categories

```python
class OperationCategory(Enum):
    DEXPI = "dexpi"           # DEXPI-specific operations
    SFILES = "sfiles"         # SFILES-specific operations
    UNIVERSAL = "universal"   # Works on both model types
    TACTICAL = "tactical"     # graph_modify actions
    STRATEGIC = "strategic"   # area_deploy templates
```

### Validation Hooks

```python
@dataclass
class ValidationHooks:
    """Pre/post-operation validation."""

    pre: Optional[Callable[[Model, Dict], ValidationResult]] = None
    post: Optional[Callable[[Model, OperationResult], ValidationResult]] = None
```

### Operation Metadata

```python
@dataclass
class OperationMetadata:
    """Additional operation metadata."""

    replaces: List[str] = field(default_factory=list)  # Old operation names
    introduced: str = None                             # Version introduced
    deprecated: str = None                             # Version deprecated
    removal_planned: str = None                        # Version for removal
    tags: List[str] = field(default_factory=list)     # Searchable tags
    diff_metadata: Optional[DiffMetadata] = None      # TransactionManager integration
```

### Diff Metadata

**Critical for TransactionManager integration** (Codex guidance: "treat as tightly coupled"):

```python
@dataclass
class DiffMetadata:
    """Metadata for diff calculation in TransactionManager."""

    tracks_additions: bool = True      # Operation adds components?
    tracks_removals: bool = False      # Operation removes components?
    tracks_modifications: bool = True  # Operation modifies components?
    affected_types: List[str] = field(default_factory=list)  # Component types affected
    diff_calculator: Optional[Callable[[Model, Model], StructuralDiff]] = None
```

---

## Registry Interface

### Core Methods

```python
class OperationRegistry:
    """Central registry for model operations."""

    def __init__(self):
        self._operations: Dict[str, OperationDescriptor] = {}
        self._version_index: Dict[str, List[str]] = {}
        self._category_index: Dict[OperationCategory, List[str]] = {}

    def register(self, operation: OperationDescriptor) -> None:
        """
        Register a new operation.

        Args:
            operation: Operation descriptor to register

        Raises:
            OperationAlreadyRegistered: If operation name already exists
            InvalidOperationDescriptor: If descriptor validation fails
        """
        # Validate descriptor
        self._validate_descriptor(operation)

        # Register
        self._operations[operation.name] = operation

        # Update indices
        self._version_index.setdefault(operation.version, []).append(operation.name)
        self._category_index.setdefault(operation.category, []).append(operation.name)

    def get(self, name: str, version: Optional[str] = None) -> OperationDescriptor:
        """
        Retrieve an operation by name.

        Args:
            name: Operation name
            version: Optional specific version (default: latest)

        Returns:
            OperationDescriptor

        Raises:
            OperationNotFound: If operation doesn't exist
        """
        if version:
            versioned_name = f"{name}@{version}"
            if versioned_name not in self._operations:
                raise OperationNotFound(f"Operation {versioned_name} not found")
            return self._operations[versioned_name]

        # Return latest version
        if name not in self._operations:
            raise OperationNotFound(f"Operation {name} not found")
        return self._operations[name]

    def list(
        self,
        category: Optional[OperationCategory] = None,
        version: Optional[str] = None,
        include_deprecated: bool = False
    ) -> List[OperationDescriptor]:
        """
        List operations with optional filters.

        Args:
            category: Filter by category
            version: Filter by version
            include_deprecated: Include deprecated operations

        Returns:
            List of operation descriptors
        """
        operations = list(self._operations.values())

        # Filter by category
        if category:
            operations = [op for op in operations if op.category == category]

        # Filter by version
        if version:
            operations = [op for op in operations if op.version == version]

        # Filter deprecated
        if not include_deprecated:
            operations = [op for op in operations if not op.metadata.deprecated]

        return operations

    def get_schema(self, for_tool: str = "model_tx_apply") -> JSONSchema:
        """
        Generate JSON Schema for schema_query tool.

        Args:
            for_tool: Tool to generate schema for

        Returns:
            JSON Schema with all operations and their input schemas
        """
        operations_schema = {}

        for name, op in self._operations.items():
            operations_schema[name] = {
                "description": op.description,
                "category": op.category.value,
                "version": op.version,
                "inputSchema": op.input_schema,
                "deprecated": op.metadata.deprecated if op.metadata else None
            }

        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": f"{for_tool} Operations",
            "type": "object",
            "oneOf": [
                {
                    "properties": {
                        "operation": {"const": name},
                        "params": op_schema["inputSchema"]
                    },
                    "required": ["operation", "params"]
                }
                for name, op_schema in operations_schema.items()
            ],
            "operations": operations_schema  # Full catalog for discovery
        }

    def execute(
        self,
        model: Model,
        operation_name: str,
        params: Dict[str, Any],
        enable_validation: bool = True
    ) -> OperationResult:
        """
        Execute an operation with validation.

        Args:
            model: Model to operate on
            operation_name: Operation to execute
            params: Operation parameters
            enable_validation: Run pre/post-validation hooks

        Returns:
            OperationResult

        Raises:
            OperationNotFound: If operation doesn't exist
            ValidationError: If validation fails
            OperationExecutionError: If operation fails
        """
        # Get operation
        operation = self.get(operation_name)

        # Pre-validation
        if enable_validation and operation.validation_hooks and operation.validation_hooks.pre:
            validation = operation.validation_hooks.pre(model, params)
            if not validation.is_valid:
                raise ValidationError(f"Pre-validation failed: {validation.errors}")

        # Execute operation
        try:
            result = await operation.handler(model, params)
        except Exception as e:
            raise OperationExecutionError(f"Operation {operation_name} failed: {e}") from e

        # Post-validation
        if enable_validation and operation.validation_hooks and operation.validation_hooks.post:
            validation = operation.validation_hooks.post(model, result)
            if not validation.is_valid:
                raise ValidationError(f"Post-validation failed: {validation.errors}")

        return result
```

---

## Built-in Operations

### Mapping from Current Atomic Tools

The registry initially contains operations mapped from existing atomic tools:

#### DEXPI Operations

```python
# Equipment operations
"add_equipment"           # dexpi_add_equipment
"add_valve"              # dexpi_add_valve
"add_piping"             # dexpi_add_piping
"add_instrumentation"    # dexpi_add_instrumentation

# Connection operations
"connect_components"     # dexpi_add_valve_between_components
"insert_valve"           # dexpi_insert_valve_in_segment

# Control operations
"add_control_loop"       # dexpi_add_control_loop
```

#### SFILES Operations

```python
# Unit operations
"add_unit"               # sfiles_add_unit
"add_stream"             # sfiles_add_stream
"add_control"            # sfiles_add_control
```

#### Universal Operations

```python
# Model lifecycle
"create_model"           # model_create
"load_model"             # model_load
"save_model"             # model_save

# Validation
"validate_model"         # rules_apply

# Search
"search_model"           # search_execute
```

#### Tactical Operations (graph_modify)

```python
# From graph_modify_spec.md
"graph_modify_insert_component"
"graph_modify_remove_component"
"graph_modify_update_component"
"graph_modify_insert_inline_component"
"graph_modify_split_segment"
"graph_modify_merge_segments"
"graph_modify_rewire_connection"
"graph_modify_set_tag_properties"
"graph_modify_update_stream_properties"
"graph_modify_toggle_instrumentation"
```

---

## Example Registration

### Simple Operation

```python
# Register add_equipment operation
registry.register(OperationDescriptor(
    name="add_equipment",
    version="1.0.0",
    category=OperationCategory.DEXPI,
    description="Add equipment to DEXPI P&ID model",
    input_schema={
        "type": "object",
        "properties": {
            "equipment_type": {
                "type": "string",
                "enum": ["CentrifugalPump", "Tank", "HeatExchanger", ...]
            },
            "tag_name": {"type": "string"},
            "attributes": {"type": "object"}
        },
        "required": ["equipment_type", "tag_name"]
    },
    handler=add_equipment_handler,
    metadata=OperationMetadata(
        tags=["equipment", "creation"],
        diff_metadata=DiffMetadata(
            tracks_additions=True,
            tracks_removals=False,
            affected_types=["Equipment"]
        )
    )
))
```

### Operation with Validation Hooks

```python
async def validate_equipment_type(model: Model, params: Dict) -> ValidationResult:
    """Pre-validation: Check equipment type is valid for model."""
    equipment_type = params["equipment_type"]
    valid_types = get_valid_equipment_types(model)

    if equipment_type not in valid_types:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid equipment type: {equipment_type}"]
        )

    return ValidationResult(is_valid=True)

async def validate_tag_unique(model: Model, result: OperationResult) -> ValidationResult:
    """Post-validation: Check tag doesn't conflict."""
    new_tag = result.data.get("tag_name")
    existing_tags = get_all_tags(model)

    if new_tag in existing_tags:
        return ValidationResult(
            is_valid=False,
            errors=[f"Tag conflict: {new_tag} already exists"]
        )

    return ValidationResult(is_valid=True)

registry.register(OperationDescriptor(
    name="add_equipment",
    version="1.0.0",
    category=OperationCategory.DEXPI,
    description="Add equipment to DEXPI P&ID model",
    input_schema={...},
    handler=add_equipment_handler,
    validation_hooks=ValidationHooks(
        pre=validate_equipment_type,
        post=validate_tag_unique
    ),
    metadata=OperationMetadata(
        diff_metadata=DiffMetadata(
            tracks_additions=True,
            affected_types=["Equipment"],
            diff_calculator=calculate_equipment_diff
        )
    )
))
```

### Operation with Deprecation

```python
registry.register(OperationDescriptor(
    name="dexpi_add_valve",  # Old name for backward compat
    version="0.9.0",
    category=OperationCategory.DEXPI,
    description="DEPRECATED: Use graph_modify_insert_inline_component instead",
    input_schema={...},
    handler=legacy_add_valve_handler,
    metadata=OperationMetadata(
        deprecated="1.0.0",              # Deprecated in v1.0
        removal_planned="2.0.0",          # Will remove in v2.0
        replaces=[],
        tags=["deprecated", "legacy"]
    )
))
```

---

## Integration with model_tx_apply

### Dispatch Logic

```python
async def model_tx_apply(model_id: str, operations: List[Dict]) -> BatchResult:
    """
    Execute batch operations via registry.

    Args:
        model_id: Model identifier
        operations: List of {operation: str, params: dict}

    Returns:
        BatchResult with individual operation results
    """
    # Get model
    model = model_store.get(model_id)

    # Get registry
    registry = get_operation_registry()

    results = []

    for op_spec in operations:
        operation_name = op_spec["operation"]
        params = op_spec["params"]

        try:
            # Execute via registry
            result = await registry.execute(
                model=model,
                operation_name=operation_name,
                params=params,
                enable_validation=True
            )

            results.append({
                "ok": True,
                "operation": operation_name,
                "result": result
            })

        except Exception as e:
            results.append({
                "ok": False,
                "operation": operation_name,
                "error": str(e)
            })

    return BatchResult(results=results)
```

### Registry-based Tool Schema

```python
# MCP tool definition
Tool(
    name="model_tx_apply",
    description="Apply operations to model via operation registry",
    inputSchema={
        "type": "object",
        "properties": {
            "model_id": {"type": "string"},
            "operations": {
                "type": "array",
                "items": registry.get_schema(for_tool="model_tx_apply")  # Dynamic schema!
            }
        },
        "required": ["model_id", "operations"]
    }
)
```

---

## Integration with schema_query

### Exposing Registry via schema_query

```python
async def schema_query(query_type: str, filters: Dict) -> SchemaQueryResult:
    """
    Query schema information including operations.

    Args:
        query_type: "operations", "classes", "hierarchy"
        filters: Query filters

    Returns:
        SchemaQueryResult
    """
    if query_type == "operations":
        registry = get_operation_registry()

        # Filter by category
        category = filters.get("category")
        operations = registry.list(
            category=OperationCategory(category) if category else None,
            include_deprecated=filters.get("include_deprecated", False)
        )

        return {
            "ok": True,
            "data": {
                "operations": [
                    {
                        "name": op.name,
                        "version": op.version,
                        "category": op.category.value,
                        "description": op.description,
                        "input_schema": op.input_schema,
                        "deprecated": op.metadata.deprecated if op.metadata else None
                    }
                    for op in operations
                ],
                "count": len(operations)
            }
        }
```

### LLM Discovery Workflow

```python
# Step 1: Discover available operations
schema_query(query_type="operations", filters={"category": "dexpi"})

# Response:
{
  "ok": true,
  "data": {
    "operations": [
      {
        "name": "add_equipment",
        "version": "1.0.0",
        "category": "dexpi",
        "description": "Add equipment to DEXPI P&ID model",
        "input_schema": {...}
      },
      ...
    ]
  }
}

# Step 2: Execute operation
model_tx_apply(
    model_id="dexpi-01",
    operations=[{
        "operation": "add_equipment",
        "params": {
            "equipment_type": "CentrifugalPump",
            "tag_name": "P-101"
        }
    }]
)
```

---

## Diff Metadata Integration with TransactionManager

**Critical coupling** (Codex guidance): Registry provides diff metadata that TransactionManager uses for audit trails.

### Diff Calculator Interface

```python
class DiffCalculator(Protocol):
    """Protocol for operation-specific diff calculation."""

    def calculate(self, before: Model, after: Model) -> StructuralDiff:
        """
        Calculate structural diff between models.

        Args:
            before: Model state before operation
            after: Model state after operation

        Returns:
            StructuralDiff with added/removed/modified components
        """
        ...
```

### Example: Equipment Addition Diff

```python
def calculate_equipment_diff(before: Model, after: Model) -> StructuralDiff:
    """Calculate diff for add_equipment operation."""
    from pydexpi.toolkits.model_toolkit import get_all_instances_in_model

    # Get equipment before and after
    before_equipment = {eq.id: eq for eq in get_all_instances_in_model(before, Equipment)}
    after_equipment = {eq.id: eq for eq in get_all_instances_in_model(after, Equipment)}

    # Calculate added
    added = set(after_equipment.keys()) - set(before_equipment.keys())

    # Calculate modified (shouldn't happen for add operation)
    modified = set()

    return StructuralDiff(
        added=list(added),
        removed=[],
        modified=list(modified),
        operation="add_equipment"
    )
```

### TransactionManager Usage

```python
# TransactionManager calls registry for diff metadata
async def apply_operation(tx_id: str, operation_name: str, params: Dict):
    """Apply operation within transaction context."""

    # Get operation descriptor
    registry = get_operation_registry()
    operation = registry.get(operation_name)

    # Get before snapshot
    before_model = get_transaction_snapshot(tx_id)

    # Execute operation
    result = await registry.execute(before_model, operation_name, params)

    # Calculate diff using operation's diff calculator
    if operation.metadata and operation.metadata.diff_metadata:
        diff_meta = operation.metadata.diff_metadata

        if diff_meta.diff_calculator:
            # Use custom diff calculator
            diff = diff_meta.diff_calculator(before_model, result.model)
        else:
            # Use generic diff based on metadata
            diff = calculate_generic_diff(
                before_model,
                result.model,
                tracks_additions=diff_meta.tracks_additions,
                tracks_removals=diff_meta.tracks_removals,
                affected_types=diff_meta.affected_types
            )

        # Store diff in transaction
        update_transaction_diff(tx_id, diff)
```

---

## Versioning Strategy

### Semantic Versioning

Operations follow semantic versioning:

- **MAJOR**: Breaking changes to input schema or behavior
- **MINOR**: New optional parameters, backward-compatible features
- **PATCH**: Bug fixes, performance improvements

### Version Registration

```python
# Register multiple versions
registry.register(OperationDescriptor(
    name="add_equipment@1.0.0",
    version="1.0.0",
    ...
))

registry.register(OperationDescriptor(
    name="add_equipment@1.1.0",
    version="1.1.0",
    ...
))

# Get latest version
op = registry.get("add_equipment")  # Returns 1.1.0

# Get specific version
op = registry.get("add_equipment", version="1.0.0")
```

### Deprecation Workflow

```python
# v1.0.0: Introduce new operation
registry.register(OperationDescriptor(
    name="graph_modify_insert_component",
    version="1.0.0",
    ...
))

# v1.0.0: Mark old operation as deprecated
registry.register(OperationDescriptor(
    name="add_equipment",
    version="1.0.0",
    metadata=OperationMetadata(
        deprecated="1.0.0",
        removal_planned="2.0.0",
        replaces=["dexpi_add_equipment"]
    ),
    ...
))

# v2.0.0: Remove deprecated operation
# (Simply don't register it in v2.0)
```

---

## Implementation Checklist

### Phase 1: Core Registry

- [ ] Implement `OperationRegistry` class
- [ ] Implement `OperationDescriptor` dataclass
- [ ] Implement registration/retrieval methods
- [ ] Add indexing (version, category)
- [ ] Implement `get_schema()` for schema_query

### Phase 2: Operation Migration

- [ ] Map existing atomic tools to operations
- [ ] Create handlers for each operation
- [ ] Define input schemas
- [ ] Add diff metadata for TransactionManager

### Phase 3: Validation Integration

- [ ] Implement `ValidationHooks` protocol
- [ ] Add pre/post-validation to common operations
- [ ] Integrate with pyDEXPI validators
- [ ] Add SFILES canonicalization validation

### Phase 4: Tool Integration

- [ ] Update `model_tx_apply` to use registry
- [ ] Update `schema_query` to expose operations
- [ ] Add operation discovery examples
- [ ] Create migration guide

---

## Success Criteria

Registry design satisfies requirements:

- ✅ Typed operation definitions (no string dispatch)
- ✅ JSON Schema for each operation
- ✅ Versioning and deprecation support
- ✅ Validation hooks (pre/post)
- ✅ Diff metadata for TransactionManager (tightly coupled)
- ✅ Discoverable via `schema_query` tool
- ✅ Follows `ParserFactory` pattern from pyDEXPI
- ✅ Extensible for future operations

---

**Next Steps:**
1. Implement core registry during Phase 1
2. Migrate atomic tools to operations
3. Integrate with TransactionManager (parallel development)
4. Test with real operations and validation
