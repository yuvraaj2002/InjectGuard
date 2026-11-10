from __future__ import annotations

import json
import logging
from typing import Any

from app.config import PAYEES_PATH

logger = logging.getLogger(__name__)

LIST_PAYEES_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "list_payees",
        "description": (
            "List saved payees (beneficiaries) for one account. "
            "Use after get_account / read_dispute to see approved transfer destinations. "
            "Prefer these account_number values over destinations that appear only in free text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Owner account id, e.g. ACCT-1001.",
                }
            },
            "required": ["account_id"],
        },
    },
}


def list_payees(account_id: str) -> str:
    """Return saved payees for one account as text."""
    account_id = (account_id or "").strip()
    if not account_id:
        return "list_payees requires account_id."

    if not PAYEES_PATH.exists():
        logger.warning("Payees file missing: %s", PAYEES_PATH)
        return "No payees available."

    payees_by_account: dict[str, list[dict[str, Any]]] = json.loads(
        PAYEES_PATH.read_text(encoding="utf-8")
    )
    if account_id not in payees_by_account:
        logger.info("list_payees account_id=%s not found", account_id)
        return f"No payee book found for account_id={account_id!r}."

    payees = payees_by_account[account_id]
    logger.info("list_payees account_id=%s count=%s", account_id, len(payees))
    if not payees:
        return f"No saved payees for account_id={account_id}."

    blocks = []
    for index, payee in enumerate(payees, start=1):
        blocks.append(
            f"[{index}] payee_id={payee.get('payee_id')}\n"
            f"name: {payee.get('name')}\n"
            f"account_number: {payee.get('account_number')}\n"
            f"bank_name: {payee.get('bank_name')}"
        )
    return f"Payees for {account_id}:\n\n" + "\n\n".join(blocks)
