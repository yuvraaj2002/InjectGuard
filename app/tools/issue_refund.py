from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import REFUND_SINK_PATH

logger = logging.getLogger(__name__)

ISSUE_REFUND_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "issue_refund",
        "description": (
            "Mock refund for a dispute. Appends a record to the local refund sink "
            "(no real payment rails). Prefer the dispute's structured account_id as to_account."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dispute_id": {
                    "type": "string",
                    "description": "Dispute being refunded, e.g. dispute-001.",
                },
                "to_account": {
                    "type": "string",
                    "description": "Destination account id for the refund.",
                },
                "amount": {
                    "type": "number",
                    "description": "Positive refund amount.",
                },
                "reason": {
                    "type": "string",
                    "description": "Optional refund reason / note.",
                },
            },
            "required": ["dispute_id", "to_account", "amount"],
        },
    },
}


def issue_refund(
    dispute_id: str,
    to_account: str,
    amount: float | int | str,
    reason: str | None = None,
) -> str:
    """Mock refund: append one JSONL record to the refund sink."""
    dispute_id = (dispute_id or "").strip()
    to_account = (to_account or "").strip()
    reason_text = (reason or "").strip()

    if not dispute_id or not to_account:
        return "issue_refund requires dispute_id and to_account."
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        return f"issue_refund amount must be a number, got {amount!r}."
    if amount_value <= 0:
        return "issue_refund amount must be positive."

    record = {
        "id": f"rfnd-{uuid.uuid4().hex[:12]}",
        "ts": datetime.now(timezone.utc).isoformat(),
        "dispute_id": dispute_id,
        "to_account": to_account,
        "amount": amount_value,
        "currency": "INR",
        "reason": reason_text,
        "status": "accepted",
    }
    REFUND_SINK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REFUND_SINK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    logger.info(
        "issue_refund id=%s dispute=%s to=%s amount=%s",
        record["id"],
        dispute_id,
        to_account,
        amount_value,
    )
    return (
        "Refund accepted by mock sink "
        f"(id={record['id']}, dispute={dispute_id}, to={to_account}, "
        f"amount={amount_value} INR). Not sent on real rails."
    )
