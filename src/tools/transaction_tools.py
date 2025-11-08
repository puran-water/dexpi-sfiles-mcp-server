"""Transaction management tools - Phase 4 consolidation.

Provides MCP wrappers around TransactionManager for ACID operations
on DEXPI and SFILES models.

These tools enable:
- Atomic multi-operation changes
- Rollback on failure
- Diff preview before commit
- Validation integration
"""

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from mcp import Tool
from ..managers.transaction_manager import TransactionManager
from ..utils.response import success_response, error_response

logger = logging.getLogger(__name__)


class TransactionTools:
    """Transaction lifecycle operations (begin/apply/commit)."""

    def __init__(
        self,
        dexpi_store: Dict[str, Any],
        sfiles_store: Dict[str, Any]
    ):
        """Initialize with model stores.

        Args:
            dexpi_store: Dictionary storing DEXPI models
            sfiles_store: Dictionary storing SFILES flowsheets
        """
        self.dexpi_models = dexpi_store
        self.flowsheets = sfiles_store
        self.tx_manager = TransactionManager(dexpi_store, sfiles_store)

    def get_tools(self) -> List[Tool]:
        """Return transaction management tools."""
        return [
            Tool(
                name="model_tx_begin",
                description="Start a transaction on a model for atomic multi-operation changes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "ID of model to lock for transaction"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Optional transaction metadata (client info, session ID, etc.)",
                            "properties": {
                                "client": {"type": "string"},
                                "session": {"type": "string"},
                                "purpose": {"type": "string"}
                            }
                        }
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="model_tx_apply",
                description="Apply one or more operations within an active transaction - Uses operation registry for type-safe dispatch",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "transaction_id": {
                            "type": "string",
                            "description": "Active transaction ID from model_tx_begin"
                        },
                        "operations": {
                            "type": "array",
                            "description": "List of operations to apply atomically",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "operation": {
                                        "type": "string",
                                        "description": "Operation name from registry (e.g., 'dexpi_add_equipment', 'sfiles_add_unit', 'template_instantiate_dexpi')"
                                    },
                                    "params": {
                                        "type": "object",
                                        "description": "Operation-specific parameters (see operation registry spec)"
                                    }
                                },
                                "required": ["operation", "params"]
                            },
                            "minItems": 1
                        }
                    },
                    "required": ["transaction_id", "operations"]
                }
            ),
            Tool(
                name="model_tx_commit",
                description="Commit or rollback a transaction - Returns diff and validation summary",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "transaction_id": {
                            "type": "string",
                            "description": "Transaction ID to finalize"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["commit", "rollback"],
                            "description": "Action to perform",
                            "default": "commit"
                        },
                        "validate": {
                            "type": "boolean",
                            "description": "Run validation before commit",
                            "default": False
                        }
                    },
                    "required": ["transaction_id"]
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Standardized response
        """
        handlers = {
            "model_tx_begin": self._begin_transaction,
            "model_tx_apply": self._apply_operations,
            "model_tx_commit": self._commit_transaction
        }

        handler = handlers.get(name)
        if not handler:
            return error_response(
                f"Unknown transaction tool: {name}",
                "UNKNOWN_TOOL"
            )

        try:
            return await handler(arguments)
        except Exception as e:
            logger.exception(f"Error in {name}")
            return error_response(
                str(e),
                "TOOL_EXECUTION_ERROR",
                details={"tool": name, "arguments": arguments}
            )

    async def _begin_transaction(self, args: dict) -> dict:
        """Start a new transaction.

        Args:
            args: {
                "model_id": str,
                "metadata": dict (optional)
            }

        Returns:
            Success response with transaction_id and snapshot strategy
        """
        model_id = args["model_id"]
        metadata = args.get("metadata")

        try:
            tx_id = await self.tx_manager.begin(model_id, metadata=metadata)

            # Get transaction details for observability
            tx = self.tx_manager.transactions[tx_id]

            return success_response({
                "transaction_id": tx_id,
                "model_id": model_id,
                "snapshot_strategy": tx.snapshot_strategy.value,
                "started_at": tx.started_at.isoformat(),
                "metadata": tx.metadata
            })

        except Exception as e:
            # TransactionManager raises specific exceptions
            # Convert exception name to snake_case for consistency
            error_code = self._exception_to_error_code(e)
            return error_response(
                str(e),
                error_code,
                details={"model_id": model_id}
            )

    async def _apply_operations(self, args: dict) -> dict:
        """Apply operations within a transaction.

        Args:
            args: {
                "transaction_id": str,
                "operations": [
                    {"operation": str, "params": dict},
                    ...
                ]
            }

        Returns:
            Success response with operations applied and current state
        """
        tx_id = args["transaction_id"]
        operations = args["operations"]

        try:
            # Apply each operation in sequence
            results = []
            for op in operations:
                operation_name = op["operation"]
                params = op["params"]

                # TransactionManager.apply handles operation registry lookup
                result = await self.tx_manager.apply(
                    tx_id,
                    operation_name=operation_name,
                    params=params
                )

                # Convert OperationResult to dict for JSON serialization
                result_dict = asdict(result) if hasattr(result, '__dataclass_fields__') else result

                results.append({
                    "operation": operation_name,
                    "result": result_dict
                })

            # Get current transaction status
            status = await self.tx_manager.get_status(tx_id)

            return success_response({
                "transaction_id": tx_id,
                "operations_applied": len(results),
                "results": results,
                "transaction_status": status
            })

        except Exception as e:
            error_code = self._exception_to_error_code(e)
            return error_response(
                str(e),
                error_code,
                details={
                    "transaction_id": tx_id,
                    "operations_count": len(operations)
                }
            )

    async def _commit_transaction(self, args: dict) -> dict:
        """Commit or rollback a transaction.

        Args:
            args: {
                "transaction_id": str,
                "action": "commit" | "rollback",
                "validate": bool
            }

        Returns:
            Success response with commit result or rollback confirmation
        """
        tx_id = args["transaction_id"]
        action = args.get("action", "commit")
        validate = args.get("validate", False)

        try:
            if action == "rollback":
                await self.tx_manager.rollback(tx_id)
                return success_response({
                    "transaction_id": tx_id,
                    "action": "rollback",
                    "message": "Transaction rolled back successfully"
                })

            else:  # commit
                result = await self.tx_manager.commit(tx_id, validate=validate)

                # Convert CommitResult to response format
                response_data = {
                    "transaction_id": result.transaction_id,
                    "operations_applied": result.operations_applied,
                    "diff": {
                        "added": result.diff.added,
                        "modified": result.diff.modified,
                        "removed": result.diff.removed,
                        "is_empty": result.diff.is_empty()
                    }
                }

                # Include validation results if requested
                if result.validation:
                    response_data["validation"] = {
                        "is_valid": result.validation.is_valid,
                        "errors": result.validation.errors,
                        "warnings": result.validation.warnings
                    }

                return success_response(response_data)

        except Exception as e:
            error_code = self._exception_to_error_code(e)
            return error_response(
                str(e),
                error_code,
                details={
                    "transaction_id": tx_id,
                    "action": action
                }
            )

    def _exception_to_error_code(self, exception: Exception) -> str:
        """
        Convert exception class name to snake_case error code for consistency.

        Examples:
            ModelNotFound -> MODEL_NOT_FOUND
            TransactionAlreadyActive -> TRANSACTION_ALREADY_ACTIVE
        """
        import re
        # Convert CamelCase to snake_case
        name = type(exception).__name__
        # Insert underscores before capitals and convert to uppercase
        snake_case = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).upper()
        return snake_case
