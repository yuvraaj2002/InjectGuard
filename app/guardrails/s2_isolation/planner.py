"""Back-compat names for the privileged planner.

The client lives in ``privileged_llm_inference.py``. This module keeps the older
``PlannerLLM`` / ``PlannerResult`` names.
"""

from app.guardrails.s2_isolation.privileged_llm_inference import PrivilegedLLM as PlannerLLM
from app.guardrails.s2_isolation.privileged_llm_inference import PrivilegedPlanResult as PlannerResult

__all__ = ["PlannerLLM", "PlannerResult"]
