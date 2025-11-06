"""
Operation Registry - Typed catalog of model operations.

Based on specification: docs/api/operation_registry_spec.md

Design pattern: Follows ParserFactory.factory_methods from
pydexpi/loaders/proteus_serializer/parser_factory.py:24-76

Provides:
- Type-safe operation definitions with JSON schemas
- Version management and deprecation
- Discoverability via schema_query
- Validation hooks (pre/post-operation)
- Diff metadata integration with TransactionManager
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from pydexpi.dexpi_classes.dexpiModel import DexpiModel

logger = logging.getLogger(__name__)

# Type aliases
Model = Union[DexpiModel, Any]  # Any for Flowsheet
JSONSchema = Dict[str, Any]


# ============================================================================
# Enums
# ============================================================================

class OperationCategory(Enum):
    """Operation categories."""
    DEXPI = "dexpi"           # DEXPI-specific operations
    SFILES = "sfiles"         # SFILES-specific operations
    UNIVERSAL = "universal"   # Works on both model types
    TACTICAL = "tactical"     # graph_modify actions
    STRATEGIC = "strategic"   # area_deploy templates


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class OperationResult:
    """Result of an operation execution."""
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationHooks:
    """Pre/post-operation validation."""
    pre: Optional[Callable[[Model, Dict], ValidationResult]] = None
    post: Optional[Callable[[Model, OperationResult], ValidationResult]] = None


@dataclass
class DiffMetadata:
    """
    Metadata for diff calculation in TransactionManager.

    Critical for TransactionManager integration (Codex: "treat as tightly coupled")
    """
    tracks_additions: bool = True      # Operation adds components?
    tracks_removals: bool = False      # Operation removes components?
    tracks_modifications: bool = True  # Operation modifies components?
    affected_types: List[str] = field(default_factory=list)  # Component types affected
    diff_calculator: Optional[Callable[[Model, Model], Any]] = None  # Custom diff logic


@dataclass
class OperationMetadata:
    """Additional operation metadata."""
    replaces: List[str] = field(default_factory=list)  # Old operation names
    introduced: str = None                             # Version introduced
    deprecated: str = None                             # Version deprecated
    removal_planned: str = None                        # Version for removal
    tags: List[str] = field(default_factory=list)     # Searchable tags
    diff_metadata: Optional[DiffMetadata] = None      # TransactionManager integration


@dataclass
class OperationDescriptor:
    """
    Describes a model operation for the registry.

    Follows ParserFactory pattern from pyDEXPI.
    """
    name: str                          # Operation identifier (e.g., "add_equipment")
    version: str                       # Semantic version (e.g., "1.0.0")
    category: OperationCategory        # DEXPI, SFILES, UNIVERSAL, etc.
    description: str                   # Human-readable description
    input_schema: JSONSchema           # JSON Schema for operation parameters
    handler: Callable[[Model, Dict], OperationResult]  # Operation handler
    validation_hooks: Optional[ValidationHooks] = None
    metadata: Optional[OperationMetadata] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = OperationMetadata()


# ============================================================================
# Exceptions
# ============================================================================

class OperationRegistryError(Exception):
    """Base exception for registry errors."""
    pass


class OperationNotFound(OperationRegistryError):
    """Operation not found in registry."""
    pass


class OperationAlreadyRegistered(OperationRegistryError):
    """Operation already registered."""
    pass


class InvalidOperationDescriptor(OperationRegistryError):
    """Invalid operation descriptor."""
    pass


class SchemaValidationError(OperationRegistryError):
    """Schema validation failed."""
    pass


# ============================================================================
# Operation Registry
# ============================================================================

class OperationRegistry:
    """
    Central registry for model operations.

    Provides typed, discoverable catalog following ParserFactory pattern.
    """

    def __init__(self):
        """Initialize registry."""
        self._operations: Dict[str, OperationDescriptor] = {}
        self._version_index: Dict[str, List[str]] = {}
        self._category_index: Dict[OperationCategory, List[str]] = {}

        logger.info("OperationRegistry initialized")

    # ========================================================================
    # Registration
    # ========================================================================

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

        # Check if already registered
        if operation.name in self._operations:
            raise OperationAlreadyRegistered(
                f"Operation '{operation.name}' already registered"
            )

        # Register
        self._operations[operation.name] = operation

        # Update indices
        self._version_index.setdefault(operation.version, []).append(operation.name)
        self._category_index.setdefault(operation.category, []).append(operation.name)

        logger.info(
            f"Registered operation: {operation.name} "
            f"(category: {operation.category.value}, version: {operation.version})"
        )

    def register_all(self, operations: List[OperationDescriptor]) -> None:
        """
        Register multiple operations at once.

        Args:
            operations: List of operation descriptors to register
        """
        for operation in operations:
            self.register(operation)

    # ========================================================================
    # Retrieval
    # ========================================================================

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
        if name not in self._operations:
            raise OperationNotFound(f"Operation '{name}' not found")

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
            operations = [
                op for op in operations
                if not op.metadata or not op.metadata.deprecated
            ]

        return operations

    def exists(self, name: str) -> bool:
        """Check if operation exists."""
        return name in self._operations

    # ========================================================================
    # Execution
    # ========================================================================

    async def execute(
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
            operation_name: Name of operation to execute
            params: Operation parameters
            enable_validation: Run pre/post validation hooks

        Returns:
            OperationResult

        Raises:
            OperationNotFound: If operation doesn't exist
            SchemaValidationError: If parameter validation fails
            ValidationError: If pre/post validation fails
        """
        # Get operation descriptor
        operation = self.get(operation_name)

        # Validate parameters against schema
        if operation.input_schema:
            self._validate_params(params, operation.input_schema, operation_name)

        # Pre-validation
        if enable_validation and operation.validation_hooks and operation.validation_hooks.pre:
            pre_result = operation.validation_hooks.pre(model, params)
            if not pre_result.is_valid:
                raise SchemaValidationError(
                    f"Pre-validation failed for {operation_name}: {pre_result.errors}"
                )

        # Execute operation
        result = operation.handler(model, params)

        # Post-validation
        if enable_validation and operation.validation_hooks and operation.validation_hooks.post:
            post_result = operation.validation_hooks.post(model, result)
            if not post_result.is_valid:
                raise SchemaValidationError(
                    f"Post-validation failed for {operation_name}: {post_result.errors}"
                )

        return result

    # ========================================================================
    # Schema Generation
    # ========================================================================

    def get_schema(self, for_tool: str = "model_tx_apply") -> JSONSchema:
        """
        Generate JSON Schema for schema_query tool.

        Args:
            for_tool: Tool to generate schema for

        Returns:
            JSON Schema for the tool
        """
        # Generate enum of all operation names
        operation_names = list(self._operations.keys())

        # Generate schema with oneOf for each operation's parameters
        schemas = []
        for op_name in operation_names:
            op = self._operations[op_name]
            schemas.append({
                "type": "object",
                "properties": {
                    "operation": {"const": op_name},
                    "params": op.input_schema
                },
                "required": ["operation", "params"]
            })

        return {
            "type": "object",
            "oneOf": schemas,
            "description": f"Operations available for {for_tool}"
        }

    def get_operation_docs(self, operation_name: str) -> Dict[str, Any]:
        """
        Get documentation for an operation.

        Args:
            operation_name: Name of operation

        Returns:
            Documentation dictionary

        Raises:
            OperationNotFound: If operation doesn't exist
        """
        operation = self.get(operation_name)

        return {
            "name": operation.name,
            "version": operation.version,
            "category": operation.category.value,
            "description": operation.description,
            "input_schema": operation.input_schema,
            "metadata": {
                "introduced": operation.metadata.introduced if operation.metadata else None,
                "deprecated": operation.metadata.deprecated if operation.metadata else None,
                "tags": operation.metadata.tags if operation.metadata else [],
            }
        }

    # ========================================================================
    # Internal Helpers
    # ========================================================================

    def _validate_descriptor(self, operation: OperationDescriptor) -> None:
        """
        Validate operation descriptor.

        Args:
            operation: Descriptor to validate

        Raises:
            InvalidOperationDescriptor: If validation fails
        """
        if not operation.name:
            raise InvalidOperationDescriptor("Operation name is required")

        if not operation.version:
            raise InvalidOperationDescriptor("Operation version is required")

        if not operation.description:
            raise InvalidOperationDescriptor("Operation description is required")

        if not operation.handler:
            raise InvalidOperationDescriptor("Operation handler is required")

        # Validate version format (simple semver check)
        version_parts = operation.version.split('.')
        if len(version_parts) != 3:
            raise InvalidOperationDescriptor(
                f"Invalid version format: {operation.version} (expected: X.Y.Z)"
            )

    def _validate_params(
        self,
        params: Dict[str, Any],
        schema: JSONSchema,
        operation_name: str
    ) -> None:
        """
        Validate parameters against JSON schema.

        Args:
            params: Parameters to validate
            schema: JSON schema to validate against
            operation_name: Operation name (for error messages)

        Raises:
            SchemaValidationError: If validation fails
        """
        # Simple validation - check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in params:
                raise SchemaValidationError(
                    f"Missing required parameter '{field}' for operation '{operation_name}'"
                )

        # Could add more sophisticated JSON Schema validation here
        # using jsonschema library, but keeping simple for now


# ============================================================================
# Singleton
# ============================================================================

_registry_instance: Optional[OperationRegistry] = None


def get_operation_registry() -> OperationRegistry:
    """
    Get singleton instance of operation registry.

    Returns:
        OperationRegistry singleton
    """
    global _registry_instance

    if _registry_instance is None:
        _registry_instance = OperationRegistry()

    return _registry_instance


def reset_operation_registry() -> None:
    """Reset singleton (for testing)."""
    global _registry_instance
    _registry_instance = None
