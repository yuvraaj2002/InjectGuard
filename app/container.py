"""App-scoped service container — build once at FastAPI boot, pass around by reference."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from defenses.s1_detection.decision_model_inference import DecisionModel
from defenses.s2_isolation.planner import PlannerLLM

logger = logging.getLogger(__name__)


@dataclass
class AppContainer:
    """Holds long-lived services shared across a single API process.

    Build at server startup. Hand the same object into routers/helpers so they
    reuse ``container.decision_model`` / ``container.planner`` instead of
    constructing clients per request.
    """

    decision_model: DecisionModel
    planner: PlannerLLM

    @classmethod
    def build(cls) -> AppContainer:
        decision_model = DecisionModel()
        decision_model.open()
        planner = PlannerLLM()
        logger.info(
            "AppContainer ready decision_model=%s planner=%s threshold=%.3f",
            decision_model.model,
            planner.model,
            decision_model.threshold,
        )
        return cls(decision_model=decision_model, planner=planner)

    def close(self) -> None:
        self.decision_model.close()
        logger.info("AppContainer closed")
