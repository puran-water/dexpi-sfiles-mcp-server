"""
Manager components for engineering-mcp-server.
"""

from .transaction_manager import (
    TransactionManager,
    Transaction,
    TransactionStatus,
    SnapshotStrategy,
    OperationRecord,
    StructuralDiff,
    CommitResult,
    ValidationResult,
    # Exceptions
    TransactionError,
    TransactionNotFound,
    TransactionAlreadyActive,
    TransactionNotActive,
    OperationExecutionError,
    ValidationError,
)

__all__ = [
    'TransactionManager',
    'Transaction',
    'TransactionStatus',
    'SnapshotStrategy',
    'OperationRecord',
    'StructuralDiff',
    'CommitResult',
    'ValidationResult',
    # Exceptions
    'TransactionError',
    'TransactionNotFound',
    'TransactionAlreadyActive',
    'TransactionNotActive',
    'OperationExecutionError',
    'ValidationError',
]
