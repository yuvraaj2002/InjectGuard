"""Answer LLM: structured facts → operator-facing prose.

No tools. No raw tool output. This model is on the privileged side of the
split: it writes the reply after the executor has finished, using only the
fields the quarantined model returned.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import GROQ_MODEL
from app.guardrails.s2_isolation.prompt import ANSWER_SYSTEM_PROMPT, build_answer_user_message
from app.llm.groq_chat import complete

logger = logging.getLogger(__name__)


class AnswerLLM:
    """Groq chat, one reply per finished plan. Never receives tools or raw text."""

    def __init__(
        self,
        *,
        model: str = GROQ_MODEL,
        system_prompt: str = ANSWER_SYSTEM_PROMPT,
    ) -> None:
        self.model = model or GROQ_MODEL
        self.system_prompt = system_prompt

    def answer(self, user_request: str, facts: list[dict[str, Any]]) -> str:
        """Write the reply from the user request and structured facts."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": build_answer_user_message(user_request, facts)},
        ]
        logger.info("AnswerLLM writing reply model=%s facts=%s", self.model, len(facts))
        # No tools. This model must not be able to call functions.
        reply = complete(messages, model=self.model)
        logger.info("AnswerLLM reply chars=%s", len(reply))
        return reply or "No reply generated from the structured facts."
