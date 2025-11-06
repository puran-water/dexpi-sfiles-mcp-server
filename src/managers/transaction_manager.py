"""
TransactionManager - ACID transactions for model operations.

Provides atomicity, consistency, isolation, and durability for model modifications.
Based on specification: docs/architecture/transaction_manager.md

Design decisions:
- Snapshot strategy: deepcopy <1MB, serialize ≥1MB (Codex recommendation)
- Size estimation: get_all_instances_in_model for DEXPI (model_toolkit.py:102-199)
- Validation: MLGraphLoader.validate_graph_format for DEXPI (ml_graph_loader.py:80-103)
- Serialization: JsonSerializer for DEXPI, canonical SFILES format for SFILES
"""

import asyncio
import copy
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydexpi.dexpi_classes.dexpiModel import DexpiModel
from pydexpi.dexpi_classes.dexpiBaseModels import DexpiBaseModel
from pydexpi.loaders import JsonSerializer
from pydexpi.loaders.ml_graph_loader import MLGraphLoader
from pydexpi.toolkits import model_toolkit as mt

from ..adapters.sfiles_adapter import get_flowsheet_class

logger = logging.getLogger(__name__)

# Type aliases
Model = Union[DexpiModel, Any]  # Any for Flowsheet until we import it


# ============================================================================
# Enums
# ============================================================================

class ModelType(Enum):
    """Model type identifier."""
    DEXPI = "dexpi"
    SFILES = "sfiles"


class SnapshotStrategy(Enum):
    """Strategy for creating model snapshots."""
    DEEPCOPY = "deepcopy"      # Python deepcopy (fast, memory-intensive)
    SERIALIZE = "serialize"     # Serialize to JSON/bytes (slower, memory-efficient)


class TransactionStatus(Enum):
    """Transaction lifecycle states."""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class OperationRecord:
    """Record of an operation executed within a transaction."""
    operation: str
    params: Dict[str, Any]
    timestamp: datetime
    success: bool = False
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class StructuralDiff:
    """Structural differences between model states."""
    added: List[str] = field(default_factory=list)      # Added component IDs
    removed: List[str] = field(default_factory=list)    # Removed component IDs
    modified: List[str] = field(default_factory=list)   # Modified component IDs
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_empty(self) -> bool:
        """Check if diff has any changes."""
        return not (self.added or self.removed or self.modified)


@dataclass
class ValidationResult:
    """Result of model validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class CommitResult:
    """Result of transaction commit."""
    transaction_id: str
    diff: StructuralDiff
    operations_applied: int
    validation: Optional[ValidationResult] = None


@dataclass
class Transaction:
    """Represents an active transaction."""
    id: str                                    # UUID transaction identifier
    model_id: str                              # Model being modified
    model_type: ModelType                      # DEXPI or SFILES
    snapshot: Union[Model, bytes]              # Model snapshot (object or serialized)
    snapshot_strategy: SnapshotStrategy        # How snapshot was created
    operations: List[OperationRecord] = field(default_factory=list)
    diff: StructuralDiff = field(default_factory=StructuralDiff)
    started_at: datetime = field(default_factory=lambda: datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow())
    status: TransactionStatus = TransactionStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    _working_model: Optional[Model] = None     # Cached working model


# ============================================================================
# Exceptions
# ============================================================================

class TransactionError(Exception):
    """Base exception for transaction errors."""
    pass


class TransactionNotFound(TransactionError):
    """Transaction does not exist."""
    pass


class TransactionAlreadyActive(TransactionError):
    """Model already has an active transaction."""
    pass


class TransactionNotActive(TransactionError):
    """Transaction is not in active state."""
    pass


class OperationExecutionError(TransactionError):
    """Operation execution failed."""
    pass


class ValidationError(TransactionError):
    """Model validation failed."""
    pass


class ModelNotFound(TransactionError):
    """Model does not exist in store."""
    pass


# ============================================================================
# Snapshot Strategy Selection
# ============================================================================

SIZE_THRESHOLD = 1 * 1024 * 1024  # 1MB


def estimate_model_size(model: Model) -> int:
    """
    Estimate model size in bytes.

    For DEXPI:
        Use get_all_instances_in_model() to count components
        Estimate: ~2KB per component average

    For SFILES:
        Count nodes + edges in NetworkX graph
        Estimate: ~1KB per node/edge average

    Args:
        model: Model to estimate

    Returns:
        Estimated size in bytes
    """
    if isinstance(model, DexpiModel):
        # Use upstream: pydexpi/toolkits/model_toolkit.py:102-199
        # Pass None to get all instances (or DexpiBaseModel for all DEXPI objects)
        components = mt.get_all_instances_in_model(model, None)
        estimated_size = len(components) * 2048  # 2KB per component

    else:
        # Assume SFILES Flowsheet
        try:
            nodes = model.state.number_of_nodes()
            edges = model.state.number_of_edges()
            estimated_size = (nodes + edges) * 1024  # 1KB per node/edge
        except AttributeError:
            # Unknown model type, default to serialize
            estimated_size = SIZE_THRESHOLD

    return estimated_size


def select_snapshot_strategy(model: Model) -> SnapshotStrategy:
    """
    Select appropriate snapshot strategy based on model size.

    Strategy:
    - DEEPCOPY: For small models (<1MB estimated size)
    - SERIALIZE: For large models (≥1MB estimated size)

    Args:
        model: Model to snapshot

    Returns:
        SnapshotStrategy
    """
    size_estimate = estimate_model_size(model)

    if size_estimate < SIZE_THRESHOLD:
        return SnapshotStrategy.DEEPCOPY
    else:
        return SnapshotStrategy.SERIALIZE


# ============================================================================
# TransactionManager
# ============================================================================

class TransactionManager:
    """
    Manages transactions for model operations.

    Provides ACID semantics:
    - Atomicity: All operations succeed or all rollback
    - Consistency: Models remain valid via validation hooks
    - Isolation: Transactions work on snapshots
    - Durability: Committed changes persisted to model storage

    Usage:
        tx_mgr = TransactionManager(dexpi_models, flowsheets)

        # Begin transaction
        tx_id = await tx_mgr.begin(model_id)

        # Apply operations
        await tx_mgr.apply(tx_id, operations)

        # Preview changes
        diff = await tx_mgr.diff(tx_id)

        # Commit or rollback
        result = await tx_mgr.commit(tx_id)
        # OR
        await tx_mgr.rollback(tx_id)
    """

    def __init__(
        self,
        dexpi_models: Dict[str, DexpiModel],
        flowsheets: Dict[str, Any]
    ):
        """
        Initialize transaction manager.

        Args:
            dexpi_models: Shared dictionary of DEXPI models
            flowsheets: Shared dictionary of SFILES flowsheets
        """
        self.dexpi_models = dexpi_models
        self.flowsheets = flowsheets
        self.transactions: Dict[str, Transaction] = {}
        self._lock = asyncio.Lock()

        # Initialize serializers
        self.json_serializer = JsonSerializer()
        self.graph_loader = MLGraphLoader()

        logger.info("TransactionManager initialized")

    # ========================================================================
    # Public API
    # ========================================================================

    async def begin(
        self,
        model_id: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Begin a new transaction.

        Creates snapshot of current model state.

        Args:
            model_id: Model identifier
            metadata: Optional transaction metadata

        Returns:
            transaction_id: UUID for this transaction

        Raises:
            ModelNotFound: If model doesn't exist
            TransactionAlreadyActive: If model already has active transaction
        """
        async with self._lock:
            # Check if model exists
            model, model_type = self._get_model(model_id)

            # Check if transaction already active
            active_tx = self._get_active_transaction(model_id)
            if active_tx:
                raise TransactionAlreadyActive(
                    f"Model {model_id} already has active transaction {active_tx.id}"
                )

            # Select snapshot strategy
            strategy = select_snapshot_strategy(model)

            # Create snapshot
            if strategy == SnapshotStrategy.DEEPCOPY:
                snapshot = self._create_deepcopy_snapshot(model)
            else:
                snapshot = self._create_serialized_snapshot(model, model_type)

            # Create transaction
            tx_id = str(uuid.uuid4())
            transaction = Transaction(
                id=tx_id,
                model_id=model_id,
                model_type=model_type,
                snapshot=snapshot,
                snapshot_strategy=strategy,
                metadata=metadata or {}
            )

            # Store transaction
            self.transactions[tx_id] = transaction

            logger.info(
                f"Transaction {tx_id} started for model {model_id} "
                f"(type: {model_type.value}, strategy: {strategy.value})"
            )

            return tx_id

    async def apply(
        self,
        transaction_id: str,
        operation_name: str,
        params: Dict[str, Any],
        executor: Optional[callable] = None
    ) -> Any:
        """
        Apply a single operation within transaction context.

        Args:
            transaction_id: Transaction identifier
            operation_name: Name of operation to execute
            params: Operation parameters
            executor: Optional callable to execute operation

        Returns:
            Operation result

        Raises:
            TransactionNotFound: If transaction doesn't exist
            TransactionNotActive: If transaction not in ACTIVE state
            OperationExecutionError: If operation fails
        """
        async with self._lock:
            # Get transaction
            transaction = self._get_transaction(transaction_id)

            if transaction.status != TransactionStatus.ACTIVE:
                raise TransactionNotActive(
                    f"Transaction {transaction_id} is not active (status: {transaction.status.value})"
                )

            # Get working model
            working_model = self._get_working_model(transaction)

            # Record operation attempt
            op_record = OperationRecord(
                operation=operation_name,
                params=params,
                timestamp=datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
            )

            try:
                # Execute operation
                if executor:
                    result = executor(working_model, params)
                else:
                    # For now, return success - will integrate with operation registry later
                    result = {"status": "success", "message": f"Operation {operation_name} applied"}

                op_record.result = result
                op_record.success = True

                # Update working model cache
                transaction._working_model = working_model

                # Update diff (simplified for now)
                self._update_diff(transaction, operation_name, params)

                return result

            except Exception as e:
                op_record.error = str(e)
                op_record.success = False
                raise OperationExecutionError(
                    f"Operation {operation_name} failed: {e}"
                ) from e

            finally:
                transaction.operations.append(op_record)

    async def commit(
        self,
        transaction_id: str,
        validate: bool = True
    ) -> CommitResult:
        """
        Commit transaction changes to model.

        Args:
            transaction_id: Transaction identifier
            validate: Run validation before commit (default: True)

        Returns:
            CommitResult with diff and validation results

        Raises:
            TransactionNotFound: If transaction doesn't exist
            ValidationError: If validation fails
        """
        async with self._lock:
            # Get transaction
            transaction = self._get_transaction(transaction_id)

            # Get working model
            working_model = self._get_working_model(transaction)

            # Validate before commit
            validation_result = None
            if validate:
                validation_result = await self._validate_model(
                    working_model,
                    transaction.model_type
                )

                if not validation_result.is_valid:
                    raise ValidationError(
                        f"Pre-commit validation failed: {validation_result.errors}"
                    )

            # Persist working model to store
            if transaction.model_type == ModelType.DEXPI:
                self.dexpi_models[transaction.model_id] = working_model
            else:
                self.flowsheets[transaction.model_id] = working_model

            # Update transaction status
            transaction.status = TransactionStatus.COMMITTED

            # Calculate final diff
            final_diff = transaction.diff

            logger.info(
                f"Transaction {transaction_id} committed "
                f"({len(transaction.operations)} operations, "
                f"{len(final_diff.added)} added, "
                f"{len(final_diff.modified)} modified, "
                f"{len(final_diff.removed)} removed)"
            )

            # Cleanup
            self._cleanup_transaction(transaction_id)

            return CommitResult(
                transaction_id=transaction_id,
                diff=final_diff,
                operations_applied=len(transaction.operations),
                validation=validation_result
            )

    async def rollback(self, transaction_id: str) -> None:
        """
        Rollback transaction, discarding all changes.

        Args:
            transaction_id: Transaction identifier

        Raises:
            TransactionNotFound: If transaction doesn't exist
        """
        async with self._lock:
            # Get transaction
            transaction = self._get_transaction(transaction_id)

            # Update status
            transaction.status = TransactionStatus.ROLLED_BACK

            logger.info(
                f"Transaction {transaction_id} rolled back "
                f"({len(transaction.operations)} operations discarded)"
            )

            # Cleanup
            self._cleanup_transaction(transaction_id)

    async def diff(self, transaction_id: str) -> StructuralDiff:
        """
        Get current diff for transaction (preview changes).

        Args:
            transaction_id: Transaction identifier

        Returns:
            StructuralDiff showing current changes

        Raises:
            TransactionNotFound: If transaction doesn't exist
        """
        transaction = self._get_transaction(transaction_id)
        return transaction.diff

    async def get_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get transaction status and metadata.

        Args:
            transaction_id: Transaction identifier

        Returns:
            Transaction status information

        Raises:
            TransactionNotFound: If transaction doesn't exist
        """
        transaction = self._get_transaction(transaction_id)

        return {
            "transaction_id": transaction.id,
            "model_id": transaction.model_id,
            "model_type": transaction.model_type.value,
            "status": transaction.status.value,
            "operations_count": len(transaction.operations),
            "started_at": transaction.started_at.isoformat(),
            "snapshot_strategy": transaction.snapshot_strategy.value,
            "diff": {
                "added": len(transaction.diff.added),
                "removed": len(transaction.diff.removed),
                "modified": len(transaction.diff.modified)
            }
        }

    # ========================================================================
    # Internal Helpers
    # ========================================================================

    def _get_model(self, model_id: str) -> tuple[Model, ModelType]:
        """Get model and determine type."""
        if model_id in self.dexpi_models:
            return self.dexpi_models[model_id], ModelType.DEXPI
        elif model_id in self.flowsheets:
            return self.flowsheets[model_id], ModelType.SFILES
        else:
            raise ModelNotFound(f"Model {model_id} not found")

    def _get_transaction(self, transaction_id: str) -> Transaction:
        """Get transaction by ID."""
        if transaction_id not in self.transactions:
            raise TransactionNotFound(f"Transaction {transaction_id} not found")
        return self.transactions[transaction_id]

    def _get_active_transaction(self, model_id: str) -> Optional[Transaction]:
        """Get active transaction for model, if any."""
        for tx in self.transactions.values():
            if tx.model_id == model_id and tx.status == TransactionStatus.ACTIVE:
                return tx
        return None

    def _get_working_model(self, transaction: Transaction) -> Model:
        """
        Get working copy of model for transaction.

        If cached, return cache. Otherwise, restore from snapshot.
        """
        if transaction._working_model is not None:
            return transaction._working_model

        # Restore from snapshot
        if transaction.snapshot_strategy == SnapshotStrategy.DEEPCOPY:
            # Snapshot is already a model object, deepcopy it
            working_model = copy.deepcopy(transaction.snapshot)
        else:
            # Deserialize snapshot
            working_model = self._deserialize_snapshot(
                transaction.snapshot,
                transaction.model_type
            )

        # Cache for next time
        transaction._working_model = working_model

        return working_model

    def _create_deepcopy_snapshot(self, model: Model) -> Model:
        """Create snapshot via Python deepcopy."""
        return copy.deepcopy(model)

    def _create_serialized_snapshot(
        self,
        model: Model,
        model_type: ModelType
    ) -> bytes:
        """
        Create snapshot via serialization.

        Args:
            model: Model to serialize
            model_type: DEXPI or SFILES

        Returns:
            Serialized model bytes
        """
        if model_type == ModelType.DEXPI:
            # Use JsonSerializer for DEXPI (pydexpi.loaders)
            json_str = self.json_serializer.serialize(model)
            return json_str.encode('utf-8')
        else:
            # Use SFILES to_SFILES() canonical format
            sfiles_str = model.to_SFILES()
            return sfiles_str.encode('utf-8')

    def _deserialize_snapshot(
        self,
        snapshot: bytes,
        model_type: ModelType
    ) -> Model:
        """
        Deserialize snapshot back to model.

        Args:
            snapshot: Serialized model bytes
            model_type: DEXPI or SFILES

        Returns:
            Deserialized model
        """
        if model_type == ModelType.DEXPI:
            # Deserialize DEXPI JSON
            json_str = snapshot.decode('utf-8')
            return self.json_serializer.deserialize(json_str)
        else:
            # Deserialize SFILES
            Flowsheet = get_flowsheet_class()
            sfiles_str = snapshot.decode('utf-8')
            return Flowsheet.from_SFILES(sfiles_str)

    async def _validate_model(
        self,
        model: Model,
        model_type: ModelType
    ) -> ValidationResult:
        """
        Validate model using upstream validators.

        For DEXPI: Use MLGraphLoader.validate_graph_format()
        For SFILES: Use convert_to_sfiles() canonicalization (implicit validation)

        Args:
            model: Model to validate
            model_type: DEXPI or SFILES

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        try:
            if model_type == ModelType.DEXPI:
                # Use upstream: pydexpi/loaders/ml_graph_loader.py:80-103
                is_valid = self.graph_loader.validate_graph_format(model)

                if not is_valid:
                    errors.append("DEXPI graph format validation failed")

            else:
                # SFILES: Try to canonicalize
                try:
                    model.convert_to_sfiles()  # Will raise if invalid
                except Exception as e:
                    errors.append(f"SFILES canonicalization failed: {e}")

            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {e}"],
                warnings=warnings
            )

    def _update_diff(
        self,
        transaction: Transaction,
        operation_name: str,
        params: Dict[str, Any]
    ) -> None:
        """
        Update transaction diff based on operation.

        Simplified version - tracks operations by name.
        Full implementation will use operation registry metadata.

        Args:
            transaction: Transaction to update
            operation_name: Operation that was executed
            params: Operation parameters
        """
        # Simple heuristic based on operation name
        if "add" in operation_name or "create" in operation_name:
            # Track as addition
            component_id = params.get("tag_name", "unknown")
            if component_id not in transaction.diff.added:
                transaction.diff.added.append(component_id)

        elif "delete" in operation_name or "remove" in operation_name:
            # Track as removal
            component_id = params.get("tag_name", params.get("component_id", "unknown"))
            if component_id not in transaction.diff.removed:
                transaction.diff.removed.append(component_id)

        else:
            # Track as modification
            component_id = params.get("tag_name", params.get("component_id", "unknown"))
            if component_id not in transaction.diff.modified and \
               component_id not in transaction.diff.added:
                transaction.diff.modified.append(component_id)

    def _cleanup_transaction(self, transaction_id: str) -> None:
        """
        Cleanup transaction resources.

        Args:
            transaction_id: Transaction to cleanup
        """
        if transaction_id in self.transactions:
            del self.transactions[transaction_id]
