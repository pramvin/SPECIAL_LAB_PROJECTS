"""Allowlisted financial diagnostics; never a second financial ledger."""
import json
import logging
import uuid

from fastapi import HTTPException

logger = logging.getLogger("planwise.financial")
OPERATIONS = frozenset(("wallet.deposit", "wallet.withdraw", "positions.open", "positions.close"))
REASONS = frozenset(("invalid_idempotency_key", "idempotency_conflict", "position_unavailable",
                     "database_contention", "unexpected_failure", "market_data_unavailable"))


class RequestError(HTTPException):
    def __init__(self, status_code, detail, reason_code, headers=None):
        super().__init__(status_code, detail, headers)
        self.financial_reason = reason_code


def emit_failure(operation, user_id, error) -> None:
    """Called only after connection/transaction contexts unwind; logging is best effort."""
    try:
        if isinstance(error, HTTPException):
            status = error.status_code
            reason = getattr(error, "financial_reason", None)
        else:
            status = getattr(error, "financial_status", 500)
            reason = getattr(error, "financial_reason", "unexpected_failure")
        if operation not in OPERATIONS or reason not in REASONS:
            return
        event = {
            "operation": operation,
            "user_id": user_id if isinstance(user_id, int) else None,
            "status": status,
            "reason_code": reason,
            "correlation_id": uuid.uuid4().hex,
        }
        logger.warning(json.dumps(event, separators=(",", ":")), exc_info=False, stack_info=False)
    except Exception:
        # A broken handler must not replace the original API outcome.
        pass
