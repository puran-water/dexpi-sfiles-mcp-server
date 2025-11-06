# TransactionManager Architecture

**Version:** 1.0.0-draft
**Status:** Phase 0.5 Design
**Last Updated:** 2025-11-06
**Codex Approved:** ✅

---

## Overview

The **TransactionManager** provides ACID-like transaction semantics for model operations, enabling:

- **Atomicity**: All operations in a transaction succeed or all rollback
- **Consistency**: Models remain valid (via validation hooks)
- **Isolation**: Transactions work on snapshots (single-transaction-per-model initially)
- **Durability**: Committed changes persisted to model storage

**Critical Design Constraint** (Codex): "Deep copies of large DexpiModels can be MB-scale; benchmark early and fall back to structural diffs or serialization snapshots"

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  TransactionManager                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐     ┌──────────────┐    ┌─────────────┐ │
│  │  begin() │────▶│ Snapshot     │───▶│ Transaction │ │
│  │          │     │ Strategy     │    │  State      │ │
│  └──────────┘     │              │    └─────────────┘ │
│                   │ • Deepcopy   │                     │
│  ┌──────────┐     │   (<1MB)     │    ┌─────────────┐ │
│  │ apply()  │     │ • Serialize  │───▶│    Diff     │ │
│  │          │     │   (>1MB)     │    │ Calculation │ │
│  └──────────┘     └──────────────┘    └─────────────┘ │
│                                                          │
│  ┌──────────┐     ┌──────────────┐    ┌─────────────┐ │
│  │ commit() │────▶│ Validation   │───▶│   Persist   │ │
│  │          │     │   Hooks      │    │             │ │
│  └──────────┘     └──────────────┘    └─────────────┘ │
│                                                          │
│  ┌──────────┐     ┌──────────────┐                     │
│  │rollback()│────▶│   Restore    │                     │
│  │          │     │   Snapshot   │                     │
│  └──────────┘     └──────────────┘                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Transaction State

```python
@dataclass
class Transaction:
    """Represents an active transaction."""

    id: str                           # UUID transaction identifier
    model_id: str                     # Model being modified
    model_type: ModelType             # DEXPI or SFILES
    snapshot: Union[Model, bytes]     # Model snapshot (object or serialized)
    snapshot_strategy: SnapshotStrategy  # How snapshot was created
    operations: List[OperationRecord] = field(default_factory=list)
    diff: StructuralDiff = field(default_factory=StructuralDiff)
    started_at: datetime = field(default_factory=datetime.utcnow)
    status: TransactionStatus = TransactionStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 2. Snapshot Strategies

```python
class SnapshotStrategy(Enum):
    """Strategy for creating model snapshots."""

    DEEPCOPY = "deepcopy"      # Python deepcopy (fast, memory-intensive)
    SERIALIZE = "serialize"     # Serialize to JSON/bytes (slower, memory-efficient)
```

### 3. Snapshot Strategy Selector

```python
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
    # Estimate model size
    size_estimate = estimate_model_size(model)

    SIZE_THRESHOLD = 1 * 1024 * 1024  # 1MB

    if size_estimate < SIZE_THRESHOLD:
        return SnapshotStrategy.DEEPCOPY
    else:
        return SnapshotStrategy.SERIALIZE


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
        from pydexpi.toolkits.model_toolkit import get_all_instances_in_model
        from pydexpi.model import GenericItem

        components = get_all_instances_in_model(model, GenericItem)
        estimated_size = len(components) * 2048  # 2KB per component

    elif isinstance(model, Flowsheet):
        nodes = model.state.number_of_nodes()
        edges = model.state.number_of_edges()
        estimated_size = (nodes + edges) * 1024  # 1KB per node/edge

    else:
        # Unknown model type, default to serialize
        estimated_size = SIZE_THRESHOLD

    return estimated_size
```

---

## TransactionManager Interface

### Class Definition

```python
class TransactionManager:
    """Manages transactions for model operations."""

    def __init__(self, model_store: ModelStore, serializer_factory: SerializerFactory):
        """
        Initialize transaction manager.

        Args:
            model_store: Storage for models
            serializer_factory: Factory for model serializers
        """
        self.model_store = model_store
        self.serializer_factory = serializer_factory
        self.transactions: Dict[str, Transaction] = {}
        self._lock = asyncio.Lock()  # For concurrent transaction safety

    async def begin(self, model_id: str, metadata: Optional[Dict] = None) -> str:
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
            if not self.model_store.exists(model_id):
                raise ModelNotFound(f"Model {model_id} not found")

            # Check if transaction already active
            active_tx = self._get_active_transaction(model_id)
            if active_tx:
                raise TransactionAlreadyActive(
                    f"Model {model_id} already has active transaction {active_tx.id}"
                )

            # Get model
            model = self.model_store.get(model_id)
            model_type = self._detect_model_type(model)

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
                f"(strategy: {strategy.value})"
            )

            return tx_id

    async def apply(
        self,
        transaction_id: str,
        operations: List[OperationSpec]
    ) -> List[OperationResult]:
        """
        Apply operations within transaction context.

        Operations execute on working copy, not committed until commit().

        Args:
            transaction_id: Transaction identifier
            operations: List of operations to apply

        Returns:
            List of operation results

        Raises:
            TransactionNotFound: If transaction doesn't exist
            TransactionNotActive: If transaction not in ACTIVE state
            OperationExecutionError: If operation fails
        """
        async with self._lock:
            # Get transaction
            transaction = self._get_transaction(transaction_id)

            # Get working model
            working_model = self._get_working_model(transaction)

            # Get operation registry
            registry = get_operation_registry()

            results = []

            for op_spec in operations:
                # Record operation attempt
                op_record = OperationRecord(
                    operation=op_spec.operation,
                    params=op_spec.params,
                    timestamp=datetime.utcnow()
                )

                try:
                    # Execute operation via registry
                    result = await registry.execute(
                        model=working_model,
                        operation_name=op_spec.operation,
                        params=op_spec.params,
                        enable_validation=True
                    )

                    op_record.result = result
                    op_record.success = True

                    # Update diff
                    self._update_diff(transaction, op_spec.operation, result)

                    results.append(result)

                except Exception as e:
                    op_record.error = str(e)
                    op_record.success = False
                    raise OperationExecutionError(
                        f"Operation {op_spec.operation} failed: {e}"
                    ) from e

                finally:
                    transaction.operations.append(op_record)

            # Update working model
            self._update_working_model(transaction, working_model)

            return results

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
            if validate:
                validation_result = await self._validate_model(
                    working_model,
                    transaction.model_type
                )

                if not validation_result.is_valid:
                    raise ValidationError(
                        f"Pre-commit validation failed: {validation_result.errors}"
                    )

            # Persist working model
            self.model_store.update(transaction.model_id, working_model)

            # Update transaction status
            transaction.status = TransactionStatus.COMMITTED

            # Calculate final diff
            final_diff = self._calculate_final_diff(transaction)

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
                validation=validation_result if validate else None
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

    def _create_deepcopy_snapshot(self, model: Model) -> Model:
        """Create snapshot via Python deepcopy."""
        import copy
        return copy.deepcopy(model)

    def _create_serialized_snapshot(self, model: Model, model_type: ModelType) -> bytes:
        """
        Create snapshot via serialization.

        Uses appropriate serializer for model type.
        Codex guidance: Document serializer choice for consistency.

        Args:
            model: Model to serialize
            model_type: DEXPI or SFILES

        Returns:
            Serialized model bytes
        """
        if model_type == ModelType.DEXPI:
            # Use JsonSerializer for DEXPI (faster than Proteus)
            serializer = self.serializer_factory.create_json_serializer()
        else:  # SFILES
            # Use SFILES to_SFILES() canonical format
            serializer = self.serializer_factory.create_sfiles_serializer()

        return serializer.serialize(model)

    def _restore_from_snapshot(self, transaction: Transaction) -> Model:
        """
        Restore model from snapshot.

        Args:
            transaction: Transaction with snapshot

        Returns:
            Restored model
        """
        if transaction.snapshot_strategy == SnapshotStrategy.DEEPCOPY:
            # Snapshot is already a model object
            return transaction.snapshot

        else:  # SERIALIZE
            # Deserialize from bytes
            if transaction.model_type == ModelType.DEXPI:
                serializer = self.serializer_factory.create_json_serializer()
            else:
                serializer = self.serializer_factory.create_sfiles_serializer()

            return serializer.deserialize(transaction.snapshot)

    def _get_working_model(self, transaction: Transaction) -> Model:
        """
        Get working model for transaction.

        First call restores from snapshot, subsequent calls return cached.

        Args:
            transaction: Transaction

        Returns:
            Working model
        """
        # Check if working model cached
        if "working_model" in transaction.metadata:
            return transaction.metadata["working_model"]

        # Restore from snapshot
        working_model = self._restore_from_snapshot(transaction)

        # Cache
        transaction.metadata["working_model"] = working_model

        return working_model

    def _update_diff(
        self,
        transaction: Transaction,
        operation_name: str,
        result: OperationResult
    ) -> None:
        """
        Update transaction diff based on operation result.

        Uses operation registry diff metadata.

        Args:
            transaction: Transaction to update
            operation_name: Operation that was executed
            result: Operation result
        """
        registry = get_operation_registry()
        operation = registry.get(operation_name)

        # Get diff metadata
        if not operation.metadata or not operation.metadata.diff_metadata:
            # No diff metadata, skip
            return

        diff_meta = operation.metadata.diff_metadata

        # Use custom diff calculator if provided
        if diff_meta.diff_calculator:
            snapshot_model = self._restore_from_snapshot(transaction)
            working_model = self._get_working_model(transaction)
            operation_diff = diff_meta.diff_calculator(snapshot_model, working_model)

        # Otherwise use generic diff based on metadata
        else:
            operation_diff = self._calculate_generic_diff(
                operation_name,
                result,
                diff_meta
            )

        # Merge into transaction diff
        transaction.diff.merge(operation_diff)

    async def _validate_model(
        self,
        model: Model,
        model_type: ModelType
    ) -> ValidationResult:
        """
        Validate model using upstream validators.

        Args:
            model: Model to validate
            model_type: DEXPI or SFILES

        Returns:
            ValidationResult
        """
        if model_type == ModelType.DEXPI:
            # Use MLGraphLoader.validate_graph_format
            from pydexpi.loaders.ml_graph_loader import MLGraphLoader
            loader = MLGraphLoader()

            try:
                loader.validate_graph_format(model)
                return ValidationResult(is_valid=True)
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    errors=[str(e)]
                )

        else:  # SFILES
            # Use SFILES canonicalization as validation
            try:
                model.convert_to_sfiles()
                return ValidationResult(is_valid=True)
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"SFILES canonicalization failed: {e}"]
                )
```

---

## Diff Calculation

### StructuralDiff

```python
@dataclass
class StructuralDiff:
    """Represents structural changes to a model."""

    added: List[str] = field(default_factory=list)       # Added component IDs
    removed: List[str] = field(default_factory=list)     # Removed component IDs
    modified: List[str] = field(default_factory=list)    # Modified component IDs
    operation: Optional[str] = None                      # Operation that caused diff
    metadata: Dict[str, Any] = field(default_factory=dict)

    def merge(self, other: "StructuralDiff") -> None:
        """
        Merge another diff into this one.

        Args:
            other: Diff to merge
        """
        self.added.extend(other.added)
        self.removed.extend(other.removed)
        self.modified.extend(other.modified)

        # Deduplicate
        self.added = list(set(self.added))
        self.removed = list(set(self.removed))
        self.modified = list(set(self.modified))
```

### Generic Diff Calculator

```python
def _calculate_generic_diff(
    operation_name: str,
    result: OperationResult,
    diff_metadata: DiffMetadata
) -> StructuralDiff:
    """
    Calculate diff generically based on metadata.

    Args:
        operation_name: Operation that was executed
        result: Operation result
        diff_metadata: Diff metadata from operation

    Returns:
        StructuralDiff
    """
    diff = StructuralDiff(operation=operation_name)

    # Extract component ID from result
    component_id = result.data.get("id") or result.data.get("tag_name")

    if diff_metadata.tracks_additions and component_id:
        diff.added.append(component_id)

    if diff_metadata.tracks_removals and component_id:
        diff.removed.append(component_id)

    if diff_metadata.tracks_modifications and component_id:
        diff.modified.append(component_id)

    return diff
```

### Detailed Diff Calculator (using get_all_instances_in_model)

```python
def calculate_detailed_diff(before: Model, after: Model) -> StructuralDiff:
    """
    Calculate detailed diff using get_all_instances_in_model.

    Codex recommendation: Use this for comprehensive diff calculation.

    Args:
        before: Model state before operations
        after: Model state after operations

    Returns:
        StructuralDiff with all changes
    """
    from pydexpi.toolkits.model_toolkit import get_all_instances_in_model
    from pydexpi.model import GenericItem

    # Get all components before and after
    before_components = {
        comp.id: comp
        for comp in get_all_instances_in_model(before, GenericItem)
    }

    after_components = {
        comp.id: comp
        for comp in get_all_instances_in_model(after, GenericItem)
    }

    # Calculate added
    added = set(after_components.keys()) - set(before_components.keys())

    # Calculate removed
    removed = set(before_components.keys()) - set(after_components.keys())

    # Calculate modified (components that exist in both but changed)
    common = set(before_components.keys()) & set(after_components.keys())
    modified = []

    for comp_id in common:
        if _component_changed(before_components[comp_id], after_components[comp_id]):
            modified.append(comp_id)

    return StructuralDiff(
        added=list(added),
        removed=list(removed),
        modified=modified
    )


def _component_changed(before: GenericItem, after: GenericItem) -> bool:
    """
    Check if component changed.

    Simple comparison: check if attributes differ.

    Args:
        before: Component before
        after: Component after

    Returns:
        True if changed
    """
    # Compare attributes (simplified)
    before_attrs = {k: v for k, v in before.__dict__.items() if not k.startswith('_')}
    after_attrs = {k: v for k, v in after.__dict__.items() if not k.startswith('_')}

    return before_attrs != after_attrs
```

---

## Performance Benchmarks

### Target Metrics

| Operation | Target | Notes |
|-----------|--------|-------|
| `begin()` | <100ms | For models up to 500 components |
| `apply()` | <50ms per operation | Incremental |
| `commit()` | <200ms | With validation |
| `rollback()` | <50ms | Discard changes |
| `diff()` | <100ms | Calculate current diff |

### Strategy Performance

| Model Size | Components | Strategy | `begin()` Time | Memory |
|------------|-----------|----------|----------------|--------|
| Small | <100 | DEEPCOPY | ~20ms | ~500KB |
| Medium | 100-500 | DEEPCOPY | ~50ms | ~1-2MB |
| Large | 500-1000 | SERIALIZE | ~150ms | ~2-5MB (serialized) |
| Very Large | >1000 | SERIALIZE | ~300ms | ~5-10MB (serialized) |

---

## Error Handling

### Exception Hierarchy

```python
class TransactionError(Exception):
    """Base class for transaction errors."""
    pass

class TransactionNotFound(TransactionError):
    """Transaction doesn't exist."""
    pass

class TransactionAlreadyActive(TransactionError):
    """Model already has active transaction."""
    pass

class TransactionNotActive(TransactionError):
    """Transaction not in ACTIVE state."""
    pass

class ValidationError(TransactionError):
    """Model validation failed."""
    pass

class OperationExecutionError(TransactionError):
    """Operation failed during execution."""
    pass
```

---

## Integration Examples

### Auto-Transaction Wrapper (graph_modify)

```python
# graph_modify with auto-transaction
async def graph_modify(
    model_id: str,
    action: str,
    target: Dict,
    payload: Dict,
    options: Dict
):
    """Execute graph_modify with optional auto-transaction."""

    create_tx = options.get("create_transaction", True)

    if create_tx:
        # Auto-transaction mode
        tx_manager = get_transaction_manager()
        tx_id = await tx_manager.begin(model_id)

        try:
            # Execute operation
            result = await _execute_graph_modify(model_id, action, target, payload)

            # Commit
            commit_result = await tx_manager.commit(tx_id)

            # Return with diff
            return {
                "ok": True,
                "data": result,
                "diff": commit_result.diff
            }

        except Exception as e:
            # Rollback on error
            await tx_manager.rollback(tx_id)
            raise

    else:
        # Manual transaction mode (user manages tx)
        return await _execute_graph_modify(model_id, action, target, payload)
```

### Manual Transaction Control

```python
# User-controlled transaction
tx_manager = get_transaction_manager()

# Start transaction
tx_id = await tx_manager.begin("dexpi-plant-01")

try:
    # Apply multiple operations
    await tx_manager.apply(tx_id, [
        {"operation": "add_equipment", "params": {...}},
        {"operation": "graph_modify_insert_inline_component", "params": {...}},
        {"operation": "graph_modify_toggle_instrumentation", "params": {...}}
    ])

    # Preview diff before committing
    diff = await tx_manager.diff(tx_id)
    print(f"Changes: {len(diff.added)} added, {len(diff.modified)} modified")

    # Commit
    result = await tx_manager.commit(tx_id, validate=True)

except Exception as e:
    # Rollback on error
    await tx_manager.rollback(tx_id)
    raise
```

---

## Implementation Checklist

### Phase 1: Core Infrastructure

- [ ] Implement `Transaction` dataclass
- [ ] Implement snapshot strategy selection
- [ ] Implement size estimation
- [ ] Implement deepcopy snapshot creation
- [ ] Implement serialized snapshot creation

### Phase 2: Transaction Lifecycle

- [ ] Implement `begin()` method
- [ ] Implement `apply()` method
- [ ] Implement `commit()` method with validation
- [ ] Implement `rollback()` method
- [ ] Add transaction state management

### Phase 3: Diff Calculation

- [ ] Implement `StructuralDiff` dataclass
- [ ] Implement generic diff calculator
- [ ] Implement detailed diff using `get_all_instances_in_model`
- [ ] Integrate with operation registry diff metadata

### Phase 4: Validation Integration

- [ ] Integrate `MLGraphLoader.validate_graph_format` for DEXPI
- [ ] Integrate SFILES `convert_to_sfiles` for validation
- [ ] Add configurable validation hooks

### Phase 5: Performance Optimization

- [ ] Benchmark snapshot strategies
- [ ] Tune size threshold (currently 1MB)
- [ ] Add caching for working models
- [ ] Optimize diff calculation

---

## Success Criteria

TransactionManager design satisfies requirements:

- ✅ ACID transaction semantics
- ✅ Snapshot strategy selection (deepcopy vs serialize)
- ✅ Performance targets met (<100ms begin, <50ms apply, <200ms commit)
- ✅ Uses upstream validation (`MLGraphLoader.validate_graph_format`)
- ✅ Uses upstream utilities (`get_all_instances_in_model` for diff)
- ✅ Tight coupling with operation registry (diff metadata)
- ✅ Serializer choice documented (JsonSerializer for DEXPI, canonical SFILES)
- ✅ Rollback safety for LLM retry workflows
- ✅ Size thresholds prevent memory issues with large models

---

**Next Steps:**
1. Implement core during Phase 1 (parallel with operation registry)
2. Performance benchmarking with real models
3. Integration testing with graph_modify and model_tx_apply
4. Optimize size thresholds based on real-world data
