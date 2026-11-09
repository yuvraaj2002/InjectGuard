"""Apply the S1 decision model at input / retrieval / tool-output boundaries."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from app.config import (
    GUARD_CONTENT_ACTION,
    GUARD_INPUT,
    GUARD_RETRIEVED_CONTEXT,
    GUARD_TOOL_OUTPUT,
)
from defenses.s1_detection.decision_model_inference import DecisionModel, Verdict

logger = logging.getLogger(__name__)

RETRIEVAL_TOOLS = frozenset({"search_docs", "read_email", "read_ticket"})

GuardAction = Literal["allow", "block", "drop", "flag"]


@dataclass(frozen=True)
class GuardEvent:
    layer: Literal["user_input", "retrieved_context", "tool_output"]
    action: GuardAction
    injection: bool
    confidence: float
    reason: str
    tool_name: str | None = None


class ContentGuard:
    """Scores text with DecisionModel and applies block/drop/flag policy."""

    def __init__(
        self,
        *,
        decision_model: DecisionModel | None = None,
        guard_input: bool = GUARD_INPUT,
        guard_retrieved_context: bool = GUARD_RETRIEVED_CONTEXT,
        guard_tool_output: bool = GUARD_TOOL_OUTPUT,
        content_action: str = GUARD_CONTENT_ACTION,
    ) -> None:
        self.decision_model = decision_model or DecisionModel()
        self.guard_input = guard_input
        self.guard_retrieved_context = guard_retrieved_context
        self.guard_tool_output = guard_tool_output
        self.content_action = content_action.strip().lower()

    def close(self) -> None:
        self.decision_model.close()

    def check_user_input(self, text: str) -> tuple[str | None, GuardEvent | None]:
        """Return (blocked_reply, event). blocked_reply is set when input is blocked."""
        if not self.guard_input:
            return None, None

        verdict = self.decision_model.score(text, source="user_input")
        if not verdict.injection:
            event = GuardEvent(
                layer="user_input",
                action="allow",
                injection=False,
                confidence=verdict.confidence,
                reason=verdict.reason,
            )
            return None, event

        event = GuardEvent(
            layer="user_input",
            action="block",
            injection=True,
            confidence=verdict.confidence,
            reason=verdict.reason,
        )
        logger.warning(
            "S1 blocked user_input noul=%.3f reason=%s",
            verdict.confidence,
            verdict.reason,
        )
        reply = (
            "Request blocked by the InjectGuard S1 decision model: the user "
            f"message looks like a prompt injection/jailbreak ({verdict.reason})."
        )
        return reply, event

    def filter_tool_output(
        self,
        tool_name: str,
        output: str,
    ) -> tuple[str, GuardEvent | None]:
        """Score retrieval/tool text; drop or flag when injection is detected."""
        is_retrieval = tool_name in RETRIEVAL_TOOLS
        if is_retrieval:
            if not self.guard_retrieved_context:
                return output, None
            layer: Literal["retrieved_context", "tool_output"] = "retrieved_context"
            source = "retrieved_context"
        else:
            if not self.guard_tool_output:
                return output, None
            layer = "tool_output"
            source = "tool_output"

        verdict = self.decision_model.score(output, source=source)
        if not verdict.injection:
            return output, GuardEvent(
                layer=layer,
                action="allow",
                injection=False,
                confidence=verdict.confidence,
                reason=verdict.reason,
                tool_name=tool_name,
            )

        action: GuardAction
        filtered = output
        if self.content_action == "flag":
            action = "flag"
            logger.warning(
                "S1 flagged %s tool=%s noul=%.3f (content still passed through)",
                layer,
                tool_name,
                verdict.confidence,
            )
        else:
            # default: drop
            action = "drop"
            filtered = (
                f"[BLOCKED by S1 decision model: suspected prompt injection in "
                f"{layer} from tool `{tool_name}` ({verdict.reason}). "
                "Content withheld from the model.]"
            )
            logger.warning(
                "S1 dropped %s tool=%s noul=%.3f",
                layer,
                tool_name,
                verdict.confidence,
            )

        return filtered, GuardEvent(
            layer=layer,
            action=action,
            injection=True,
            confidence=verdict.confidence,
            reason=verdict.reason,
            tool_name=tool_name,
        )
