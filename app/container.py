"""App-scoped service container — build once at FastAPI boot, pass around by reference."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from defenses.s1_detection.decision_model_inference import DecisionModel
from defenses.s1_detection.guard import ContentGuard

logger = logging.getLogger(__name__)


@dataclass
class AppContainer:
    """Holds long-lived services shared across a single API process.

    Build this at server startup (composition root). Hand the same object into
    routers/helpers so they use ``container.decision_model`` instead of
    constructing a new client on every request.
    """

    decision_model: DecisionModel
    content_guard: ContentGuard

    @classmethod
    def build(cls) -> AppContainer:
        decision_model = DecisionModel()
        decision_model.open()
        # Input gate lives in handle_chat; this guard is for later content stages.
        content_guard = ContentGuard(decision_model=decision_model, guard_input=False)
        logger.info(
            "AppContainer ready decision_model=%s threshold=%.3f",
            decision_model.model,
            decision_model.threshold,
        )
        return cls(decision_model=decision_model, content_guard=content_guard)

    def close(self) -> None:
        self.content_guard.close()
        logger.info("AppContainer closed")
