"""POST /chat helper: S1 gates → baseline BankOps agent."""

from __future__ import annotations

import logging

from app.agent.baseline import TOOL_SCHEMAS, BaselineAgent, ChatResult
from app.config import DEFAULT_USER_ID, OLLAMA_MODEL
from app.container import AppContainer
from app.guardrails.s1_detection.guard import ContentGuard

logger = logging.getLogger(__name__)


def handle_chat(
    message: str,
    *,
    user_id: str = DEFAULT_USER_ID,
    model: str = OLLAMA_MODEL,
    container: AppContainer | None = None,
) -> ChatResult:
    """S1 on user message, then tool-calling agent with S1 on retrieved/tool text.

    S2 plan-then-execute is intentionally not on this path yet.
    """
    resolved_user_id = (user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    owns_container = container is None
    services = container or AppContainer.build()

    try:
        guard = ContentGuard(classifier=services.input_classifier)

        # --- S1: user-message gate (block) ---
        blocked_reply, input_event = guard.check_user_input(message)
        if blocked_reply is not None:
            logger.warning(
                "Rejected user message reason=%s",
                input_event.reason if input_event else "unknown",
            )
            return ChatResult(
                reply=blocked_reply,
                model=model,
                available_tools=[tool["function"]["name"] for tool in TOOL_SCHEMAS],
                user_id=resolved_user_id,
                guard_events=[input_event] if input_event is not None else [],
                blocked=True,
            )

        # --- Agent loop: tools → S1 on retrieved context / tool outputs → reply ---
        result = BaselineAgent(
            model=model,
            user_id=resolved_user_id,
            content_guard=guard,
        ).chat(message)
        if input_event is not None:
            result.guard_events = [input_event, *result.guard_events]
        return result
    finally:
        if owns_container:
            services.close()
