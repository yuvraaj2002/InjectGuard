"""Solution 1: decision / guard model on untrusted text."""

from defenses.s1_detection.decision_model_inference import (
    DecisionModel,
    DecisionModelClient,
    Verdict,
    score_text,
)

__all__ = [
    "DecisionModel",
    "DecisionModelClient",
    "Verdict",
    "score_text",
]
