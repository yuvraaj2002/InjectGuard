from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import TRANSFER_SINK_PATH

logger = logging.getLogger(__name__)

TRANSFER_FUNDS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "transfer_funds",
        "description": (
            "Mock transfer between accounts. Appends a record to the local transfer sink "
            "(no real payment rails). Use only when the operator clearly requests a transfer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "from_account": {
                    "type": "string",
                    "description": "Source account id to debit, e.g. ACCT-1001.",
                },
                "to_account": {
                    "type": "string",
                    "description": "Destination account id to credit, e.g. ACCT-1003.",
                },
                "amount": {
                    "type": "number",
                    "description": "Positive transfer amount.",
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code. Defaults to INR.",
                },
                "memo": {
                    "type": "string",
                    "description": "Optional memo / note for the transfer.",
                },
            },
            "required": ["from_account", "to_account", "amount"],
        },
    },
}


def transfer_funds(
    from_account: str,
    to_account: str,
    amount: float | int | str,
    currency: str = "INR",
    memo: str | None = None,
) -> str:
    """Mock fund transfer: append one JSONL record to the transfer sink."""
    from_account = (from_account or "").strip()
    to_account = (to_account or "").strip()
    currency = (currency or "INR").strip() or "INR"
    memo_text = (memo or "").strip()

    if not from_account or not to_account:
        return "transfer_funds requires from_account and to_account."
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        return f"transfer_funds amount must be a number, got {amount!r}."
    if amount_value <= 0:
        return "transfer_funds amount must be positive."

    record = {
        "id": f"xfer-{uuid.uuid4().hex[:12]}",
        "ts": datetime.now(timezone.utc).isoformat(),
        "from_account": from_account,
        "to_account": to_account,
        "amount": amount_value,
        "currency": currency,
        "memo": memo_text,
        "status": "accepted",
    }
    TRANSFER_SINK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRANSFER_SINK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    logger.info(
        "transfer_funds id=%s from=%s to=%s amount=%s %s",
        record["id"],
        from_account,
        to_account,
        amount_value,
        currency,
    )
    return (
        "Transfer accepted by mock sink "
        f"(id={record['id']}, from={from_account}, to={to_account}, "
        f"amount={amount_value} {currency}). Not sent on real rails."
    )
