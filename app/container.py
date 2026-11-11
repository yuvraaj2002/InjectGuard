"""App-scoped service container — build once at FastAPI boot, pass around by reference."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.guardrails.s1_detection.input_classifier_inference import InputClassifier

logger = logging.getLogger(__name__)


@dataclass
class AppContainer:
    """Holds long-lived services shared across a single API process.

    Build at server startup. Hand the same object into routers/helpers so they
    reuse ``container.input_classifier`` instead of constructing clients per request.
    """

    input_classifier: InputClassifier

    @classmethod
    def build(cls) -> AppContainer:
        input_classifier = InputClassifier()
        input_classifier.open()
        logger.info("AppContainer ready input_classifier=%s", input_classifier.model)
        return cls(input_classifier=input_classifier)

    def close(self) -> None:
        self.input_classifier.close()
        logger.info("AppContainer closed")
