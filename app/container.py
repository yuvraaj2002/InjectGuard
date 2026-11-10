"""App-scoped service container — build once at FastAPI boot, pass around by reference."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from defenses.s1_detection.decision_model_inference import DecisionModel

logger = logging.getLogger(__name__)


@dataclass
class AppContainer:
    """Holds long-lived services shared across a single API process.

    Build this at server startup (composition root). Hand the same object into
    routers/helpers so they use ``container.decision_model`` instead of
    constructing a new client on every request.
    """

    decision_model: DecisionModel

    @classmethod
    def build(cls) -> AppContainer:
        decision_model = DecisionModel()
        decision_model.open()
        logger.info(
            "AppContainer ready decision_model=%s threshold=%.3f",
            decision_model.model,
            decision_model.threshold,
        )
        return cls(decision_model=decision_model)

    def close(self) -> None:
        self.decision_model.close()
        logger.info("AppContainer closed")
