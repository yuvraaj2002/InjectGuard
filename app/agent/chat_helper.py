"""POST /chat helper: score the user message, then run the BankOps agent (or reject)."""

from __future__ import annotations

import logging

from app.agent.baseline import BaselineAgent, ChatResult
from app.config import DEFAULT_USER_ID, INJECTION_THRESHOLD, OLLAMA_MODEL
from app.container import AppContainer

logger = logging.getLogger(__name__)

BANKOPS_TOOL_NAMES = [
    "search_policies",
    "read_dispute",
    "get_account",
    "list_payees",
    "transfer_funds",
    "issue_refund",
]


def handle_chat(
    message: str,
    *,
    user_id: str = DEFAULT_USER_ID,
    model: str = OLLAMA_MODEL,
    container: AppContainer | None = None,
) -> ChatResult:
    """User message → decision model → reject or continue to the agent.

    ``Verdict.injection`` is already ``confidence >= INJECTION_THRESHOLD``.
    On injection we stop the whole turn and return a refusal; otherwise we run BankOps.
    ContentGuard (guard.py) is intentionally not used here yet.
    """
    resolved_user_id = (user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    owns_container = container is None
    services = container or AppContainer.build()

    try:
        verdict = services.decision_model.score(message, source="user_input")

        if verdict.injection and verdict.confidence >= INJECTION_THRESHOLD:
            logger.warning(
                "Rejected user message confidence=%.3f threshold=%.3f reason=%s",
                verdict.confidence,
                INJECTION_THRESHOLD,
                verdict.reason,
            )
            return ChatResult(
                reply=(
                    "Request blocked: the message looks like a prompt injection/jailbreak "
                    f"({verdict.reason})."
                ),
                model=model,
                available_tools=list(BANKOPS_TOOL_NAMES),
                user_id=resolved_user_id,
                tool_calls=[],
                blocked=True,
            )

        logger.info(
            "Allowed user message confidence=%.3f threshold=%.3f",
            verdict.confidence,
            INJECTION_THRESHOLD,
        )
        return BaselineAgent(model=model, user_id=resolved_user_id).chat(message)
    finally:
        if owns_container:
            services.close()
