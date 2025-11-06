"""
Operation Registry for engineering-mcp-server.

Provides typed, discoverable catalog of model operations.
"""

from .operation_registry import (
    OperationRegistry,
    OperationDescriptor,
    OperationCategory,
    OperationResult,
    ValidationHooks,
    OperationMetadata,
    DiffMetadata,
    # Exceptions
    OperationNotFound,
    OperationRegistryError,
    SchemaValidationError,
    # Singleton
    get_operation_registry,
)

__all__ = [
    'OperationRegistry',
    'OperationDescriptor',
    'OperationCategory',
    'OperationResult',
    'ValidationHooks',
    'OperationMetadata',
    'DiffMetadata',
    # Exceptions
    'OperationNotFound',
    'OperationRegistryError',
    'SchemaValidationError',
    # Singleton
    'get_operation_registry',
]
