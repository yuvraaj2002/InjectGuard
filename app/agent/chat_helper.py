"""POST /chat helper: S1 decision gate on the user message, then the BankOps agent."""

from __future__ import annotations

import logging

from app.agent.baseline import BaselineAgent, ChatResult
from app.config import (
    DEFAULT_USER_ID,
    GUARD_INPUT,
    INJECTION_THRESHOLD,
    OLLAMA_MODEL,
)
from app.container import AppContainer
from defenses.s1_detection.guard import GuardEvent

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
    """Score the user message first; only run the agent when it passes the confidence gate.

    Confidence policy: System One returns ``noul`` ∈ [0, 1] = P(injection).
    We treat ``noul >= INJECTION_THRESHOLD`` as a jailbreak/injection and block.

    Pass the process-level ``AppContainer`` from FastAPI so we reuse the opened
    decision-model client instead of constructing one per request. Scripts/evals
    may omit it; we then build a short-lived container for that call.
    """
    resolved_user_id = (user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    owns_container = container is None
    services = container or AppContainer.build()
    guard_events: list[GuardEvent] = []

    try:
        if GUARD_INPUT:
            verdict = services.decision_model.score(message, source="user_input")

            if verdict.injection:
                event = GuardEvent(
                    layer="user_input",
                    action="block",
                    injection=True,
                    confidence=verdict.confidence,
                    reason=verdict.reason,
                )
                guard_events.append(event)
                logger.warning(
                    "S1 blocked user_input noul=%.3f threshold=%.3f reason=%s",
                    verdict.confidence,
                    INJECTION_THRESHOLD,
                    verdict.reason,
                )
                return ChatResult(
                    reply=(
                        "Request blocked by the InjectGuard S1 decision model: "
                        f"the user message looks like a prompt injection/jailbreak ({verdict.reason})."
                    ),
                    model=model,
                    available_tools=list(BANKOPS_TOOL_NAMES),
                    user_id=resolved_user_id,
                    tool_calls=[],
                    guard_events=guard_events,
                    blocked=True,
                )

            guard_events.append(
                GuardEvent(
                    layer="user_input",
                    action="allow",
                    injection=False,
                    confidence=verdict.confidence,
                    reason=verdict.reason,
                )
            )
            logger.info(
                "S1 allowed user_input noul=%.3f threshold=%.3f",
                verdict.confidence,
                INJECTION_THRESHOLD,
            )

        agent = BaselineAgent(
            model=model,
            user_id=resolved_user_id,
            content_guard=services.content_guard,
        )
        result = agent.chat(message)
        result.guard_events = [*guard_events, *result.guard_events]
        return result
    finally:
        if owns_container:
            services.close()
