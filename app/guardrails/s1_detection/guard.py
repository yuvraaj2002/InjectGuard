"""Apply the S1 classifier at input / retrieval / tool-output boundaries."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Protocol

from app.config import GUARD_CONTENT_ACTION, GUARD_RETRIEVED_CONTEXT, GUARD_TOOL_OUTPUT
from app.guardrails.s1_detection.decision_model_inference import Verdict

logger = logging.getLogger(__name__)
RETRIEVAL_TOOLS = frozenset(
    {"search_policies", "read_dispute", "get_account", "list_payees"}
)
GuardAction = Literal["allow", "block", "drop", "flag"]


class TextScorer(Protocol):
    """Anything with DecisionModel / InputClassifier's ``score`` shape."""

    def score(self, text: str, *, source: str = "unknown") -> Verdict: ...


@dataclass(frozen=True)
class GuardEvent:
    layer: Literal["user_input", "retrieved_context", "tool_output"]
    action: GuardAction
    injection: bool
    confidence: float
    reason: str
    tool_name: str | None = None


class ContentGuard:
    """Scores text with an S1 classifier and applies block/drop/flag policy.

    v1 chat path uses ``InputClassifier`` only for user input. Retrieved /
    tool-output scoring stays behind toggles until those stages are enabled.
    """

    def __init__(
        self,
        *,
        classifier: TextScorer,
        guard_retrieved_context: bool = GUARD_RETRIEVED_CONTEXT,
        guard_tool_output: bool = GUARD_TOOL_OUTPUT,
        content_action: str = GUARD_CONTENT_ACTION,
    ) -> None:
        self.classifier = classifier
        self.guard_retrieved_context = guard_retrieved_context
        self.guard_tool_output = guard_tool_output
        self.content_action = content_action.strip().lower()

    def close(self) -> None:
        # Classifier lifetime is owned by AppContainer (or the caller that opened it).
        pass

    def check_user_input(self, text: str) -> tuple[str | None, GuardEvent | None]:
        """Return (blocked_reply, event). blocked_reply is set when input is blocked."""
        verdict = self.classifier.score(text, source="user_input")
        if not verdict.injection:
            return None, GuardEvent(
                layer="user_input",
                action="allow",
                injection=False,
                confidence=verdict.confidence,
                reason=verdict.reason,
            )

        event = GuardEvent(
            layer="user_input",
            action="block",
            injection=True,
            confidence=verdict.confidence,
            reason=verdict.reason,
        )
        logger.warning(
            "S1 blocked user_input confidence=%.3f reason=%s",
            verdict.confidence,
            verdict.reason,
        )
        reply = (
            "Request blocked by the InjectGuard S1 input classifier: the user message "
            f"looks like a prompt injection/jailbreak ({verdict.reason})."
        )
        return reply, event

    def filter_tool_output(self, tool_name: str, output: str) -> tuple[str, GuardEvent | None]:
        """Score retrieval/tool text; drop or flag when injection is detected."""
        is_retrieval = tool_name in RETRIEVAL_TOOLS
        if is_retrieval and not self.guard_retrieved_context:
            return output, None
        if not is_retrieval and not self.guard_tool_output:
            return output, None

        layer: Literal["retrieved_context", "tool_output"] = (
            "retrieved_context" if is_retrieval else "tool_output"
        )
        verdict = self.classifier.score(output, source=layer)
        if not verdict.injection:
            return output, GuardEvent(
                layer=layer,
                action="allow",
                injection=False,
                confidence=verdict.confidence,
                reason=verdict.reason,
                tool_name=tool_name,
            )

        if self.content_action == "flag":
            logger.warning(
                "S1 flagged %s tool=%s confidence=%.3f (content still passed through)",
                layer,
                tool_name,
                verdict.confidence,
            )
            return output, GuardEvent(
                layer=layer,
                action="flag",
                injection=True,
                confidence=verdict.confidence,
                reason=verdict.reason,
                tool_name=tool_name,
            )

        filtered = (
            f"[BLOCKED by S1 input classifier: suspected prompt injection in {layer} "
            f"from tool `{tool_name}` ({verdict.reason}). Content withheld from the model.]"
        )
        logger.warning("S1 dropped %s tool=%s confidence=%.3f", layer, tool_name, verdict.confidence)
        return filtered, GuardEvent(
            layer=layer,
            action="drop",
            injection=True,
            confidence=verdict.confidence,
            reason=verdict.reason,
            tool_name=tool_name,
        )
