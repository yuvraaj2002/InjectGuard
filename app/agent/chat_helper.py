"""POST /chat helper: S1 input gate → baseline BankOps agent."""

from __future__ import annotations

import logging

from app.agent.baseline import BaselineAgent, ChatResult
from app.config import DEFAULT_USER_ID, OLLAMA_MODEL
from app.container import AppContainer

logger = logging.getLogger(__name__)


def handle_chat(
    message: str,
    *,
    user_id: str = DEFAULT_USER_ID,
    model: str = OLLAMA_MODEL,
    container: AppContainer | None = None,
) -> ChatResult:
    """S1 input classifier on the user message, then the baseline tool-calling agent.

    S2 plan-then-execute is intentionally not on this path yet.
    """
    resolved_user_id = (user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    owns_container = container is None
    services = container or AppContainer.build()

    try:
        # --- S1: user-message input classifier ---
        verdict = services.input_classifier.score(message, source="user_input")
        if verdict.injection:
            logger.warning(
                "Rejected user message score=%.3f reason=%s model=%s",
                verdict.confidence,
                verdict.reason,
                verdict.model,
            )
            agent = BaselineAgent(model=model, user_id=resolved_user_id)
            return ChatResult(
                reply=(
                    "Request blocked: the message looks like a prompt injection/jailbreak "
                    f"({verdict.reason})."
                ),
                model=model,
                available_tools=agent.available_tool_names,
                user_id=resolved_user_id,
                blocked=True,
            )

        return BaselineAgent(model=model, user_id=resolved_user_id).chat(message)
    finally:
        if owns_container:
            services.close()
