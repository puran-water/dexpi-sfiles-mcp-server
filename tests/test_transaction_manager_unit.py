"""
Unit tests for TransactionManager data structures and utilities.

These tests don't require pyDEXPI/SFILES2 to be installed.
"""

from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# Test Data Structures
# ============================================================================

def test_structural_diff_is_empty():
    """Test StructuralDiff.is_empty() method."""
    from src.managers.transaction_manager import StructuralDiff

    # Empty diff
    diff = StructuralDiff()
    assert diff.is_empty()

    # Diff with additions
    diff.added.append("T-101")
    assert not diff.is_empty()

    # Diff with removals
    diff2 = StructuralDiff()
    diff2.removed.append("P-102")
    assert not diff2.is_empty()

    # Diff with modifications
    diff3 = StructuralDiff()
    diff3.modified.append("V-103")
    assert not diff3.is_empty()


def test_validation_result_is_valid():
    """Test ValidationResult with no errors."""
    from src.managers.transaction_manager import ValidationResult

    result = ValidationResult(is_valid=True)
    assert result.is_valid
    assert len(result.errors) == 0
    assert len(result.warnings) == 0


def test_validation_result_with_errors():
    """Test ValidationResult with errors."""
    from src.managers.transaction_manager import ValidationResult

    result = ValidationResult(
        is_valid=False,
        errors=["Error 1", "Error 2"],
        warnings=["Warning 1"]
    )

    assert not result.is_valid
    assert len(result.errors) == 2
    assert len(result.warnings) == 1
    assert "Error 1" in result.errors


def test_operation_record_creation():
    """Test OperationRecord dataclass."""
    from src.managers.transaction_manager import OperationRecord

    op = OperationRecord(
        operation="add_equipment",
        params={"tag_name": "T-101"},
        timestamp=datetime.utcnow(),
        success=True,
        result={"status": "success"}
    )

    assert op.operation == "add_equipment"
    assert op.params["tag_name"] == "T-101"
    assert op.success is True
    assert op.error is None


def test_commit_result_structure():
    """Test CommitResult dataclass."""
    from src.managers.transaction_manager import CommitResult, StructuralDiff

    diff = StructuralDiff(
        added=["T-101", "P-102"],
        removed=["V-103"],
        modified=[]
    )

    result = CommitResult(
        transaction_id="tx-123",
        diff=diff,
        operations_applied=3
    )

    assert result.transaction_id == "tx-123"
    assert result.operations_applied == 3
    assert len(result.diff.added) == 2
    assert len(result.diff.removed) == 1


def test_transaction_status_enum():
    """Test TransactionStatus enum."""
    from src.managers.transaction_manager import TransactionStatus

    assert TransactionStatus.ACTIVE.value == "active"
    assert TransactionStatus.COMMITTED.value == "committed"
    assert TransactionStatus.ROLLED_BACK.value == "rolled_back"
    assert TransactionStatus.FAILED.value == "failed"


def test_snapshot_strategy_enum():
    """Test SnapshotStrategy enum."""
    from src.managers.transaction_manager import SnapshotStrategy

    assert SnapshotStrategy.DEEPCOPY.value == "deepcopy"
    assert SnapshotStrategy.SERIALIZE.value == "serialize"


def test_model_type_enum():
    """Test ModelType enum."""
    from src.managers.transaction_manager import ModelType

    assert ModelType.DEXPI.value == "dexpi"
    assert ModelType.SFILES.value == "sfiles"


# ============================================================================
# Test Exceptions
# ============================================================================

def test_exception_hierarchy():
    """Test exception inheritance."""
    from src.managers.transaction_manager import (
        TransactionError,
        TransactionNotFound,
        TransactionAlreadyActive,
        ValidationError,
        ModelNotFound
    )

    # All should inherit from TransactionError
    assert issubclass(TransactionNotFound, TransactionError)
    assert issubclass(TransactionAlreadyActive, TransactionError)
    assert issubclass(ValidationError, TransactionError)
    assert issubclass(ModelNotFound, TransactionError)

    # TransactionError should inherit from Exception
    assert issubclass(TransactionError, Exception)


def test_exception_messages():
    """Test exception message formatting."""
    from src.managers.transaction_manager import (
        TransactionNotFound,
        ModelNotFound,
        ValidationError
    )

    exc1 = TransactionNotFound("Transaction tx-123 not found")
    assert "tx-123" in str(exc1)

    exc2 = ModelNotFound("Model model-456 not found")
    assert "model-456" in str(exc2)

    exc3 = ValidationError("Validation failed: invalid connection")
    assert "invalid connection" in str(exc3)


# ============================================================================
# Test Constants
# ============================================================================

def test_size_threshold_constant():
    """Test SIZE_THRESHOLD constant."""
    from src.managers.transaction_manager import SIZE_THRESHOLD

    assert SIZE_THRESHOLD == 1 * 1024 * 1024  # 1MB
    assert SIZE_THRESHOLD == 1048576  # bytes


if __name__ == "__main__":
    # Run tests manually if pytest not available
    import sys

    tests = [
        test_structural_diff_is_empty,
        test_validation_result_is_valid,
        test_validation_result_with_errors,
        test_operation_record_creation,
        test_commit_result_structure,
        test_transaction_status_enum,
        test_snapshot_strategy_enum,
        test_model_type_enum,
        test_exception_hierarchy,
        test_exception_messages,
        test_size_threshold_constant,
    ]

    failed = 0
    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{len(tests) - failed}/{len(tests)} tests passed")
    sys.exit(0 if failed == 0 else 1)
