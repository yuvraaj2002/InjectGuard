from __future__ import annotations

import json
import logging
from typing import Any

from app.config import DEFAULT_USER_ID, DISPUTES_PATH

logger = logging.getLogger(__name__)

READ_DISPUTE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_dispute",
        "description": (
            "Read customer disputes assigned to the current BankOps operator. "
            "Pass dispute_id to open one case, or query for keyword search. "
            "Call with no arguments to list the operator's open disputes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dispute_id": {
                    "type": "string",
                    "description": "Exact dispute id, e.g. dispute-003.",
                },
                "query": {
                    "type": "string",
                    "description": "Keyword filter over subject/body. Omit to list all assigned disputes.",
                },
            },
            "required": [],
        },
    },
}


def read_dispute(
    user_id: str = DEFAULT_USER_ID,
    dispute_id: str | None = None,
    query: str | None = None,
) -> str:
    """Read disputes for one operator. user_id comes from the API session, not the model."""
    if not DISPUTES_PATH.exists():
        logger.warning("Disputes file missing: %s", DISPUTES_PATH)
        return "No disputes available."

    all_disputes: list[dict[str, Any]] = json.loads(DISPUTES_PATH.read_text(encoding="utf-8"))
    mine = [d for d in all_disputes if str(d.get("assignee", "")).strip() == user_id.strip()]
    if not mine:
        return f"No disputes assigned to user_id={user_id!r}."

    def render(dispute: dict[str, Any]) -> str:
        return (
            f"id: {dispute.get('id')}\n"
            f"assignee: {dispute.get('assignee')}\n"
            f"customer_name: {dispute.get('customer_name')}\n"
            f"account_id: {dispute.get('account_id')}\n"
            f"subject: {dispute.get('subject')}\n"
            f"amount: {dispute.get('amount')} {dispute.get('currency', '')}\n"
            f"status: {dispute.get('status')}\n"
            f"body:\n{dispute.get('body', '')}"
        )

    if dispute_id:
        for dispute in mine:
            if dispute.get("id") == dispute_id:
                logger.info("read_dispute user_id=%s id=%s", user_id, dispute_id)
                return render(dispute)
        # Exists but not assigned to this user?
        if any(d.get("id") == dispute_id for d in all_disputes):
            logger.info("read_dispute user_id=%s id=%s forbidden", user_id, dispute_id)
            return f"Dispute {dispute_id} is not assigned to user_id={user_id!r}."
        logger.info("read_dispute user_id=%s id=%s not found", user_id, dispute_id)
        return f"Dispute not found: {dispute_id}"

    if query:
        tokens = {token.lower() for token in query.split() if token.strip()}
        matches: list[dict[str, Any]] = []
        for dispute in mine:
            haystack = " ".join(
                [
                    str(dispute.get("id", "")),
                    str(dispute.get("customer_name", "")),
                    str(dispute.get("account_id", "")),
                    str(dispute.get("subject", "")),
                    str(dispute.get("body", "")),
                ]
            ).lower()
            if not tokens or all(token in haystack for token in tokens):
                matches.append(dispute)
        logger.info("read_dispute user_id=%s query=%r matches=%s", user_id, query, len(matches))
        if not matches:
            return f"No disputes matched query={query!r} for user_id={user_id!r}."
        return "\n\n---\n\n".join(render(dispute) for dispute in matches)

    logger.info("read_dispute user_id=%s list_all count=%s", user_id, len(mine))
    lines = [
        f"{d.get('id')}: {d.get('subject')} [{d.get('status')}] amount={d.get('amount')} {d.get('currency', '')}"
        for d in mine
    ]
    return f"Open disputes for {user_id}:\n" + "\n".join(lines)
