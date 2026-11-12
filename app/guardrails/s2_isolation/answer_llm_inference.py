"""Answer LLM: structured facts → operator-facing prose.

No tools. No raw tool output. This model is on the privileged side of the
split: it writes the reply after the executor has finished, using only the
fields the quarantined model returned.
"""

from __future__ import annotations

import logging
from typing import Any

import ollama

from app.config import OLLAMA_HOST, OLLAMA_MODEL
from app.guardrails.s2_isolation.prompt import ANSWER_SYSTEM_PROMPT, build_answer_user_message

logger = logging.getLogger(__name__)


class AnswerLLM:
    """One Ollama client. answer() per finished plan. Never receives tools or raw text."""

    def __init__(
        self,
        *,
        model: str = OLLAMA_MODEL,
        host: str = OLLAMA_HOST,
        system_prompt: str = ANSWER_SYSTEM_PROMPT,
    ) -> None:
        self.model = model or OLLAMA_MODEL
        self.system_prompt = system_prompt
        self._client = ollama.Client(host=host)

    def answer(self, user_request: str, facts: list[dict[str, Any]]) -> str:
        """Write the reply from the user request and structured facts."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": build_answer_user_message(user_request, facts)},
        ]
        logger.info("AnswerLLM writing reply model=%s facts=%s", self.model, len(facts))
        # No tools= argument. This model must not be able to call functions.
        response = self._client.chat(model=self.model, messages=messages)
        reply = (response.message.content or "").strip()
        logger.info("AnswerLLM reply chars=%s", len(reply))
        return reply or "No reply generated from the structured facts."
