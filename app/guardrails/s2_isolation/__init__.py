"""Solution 2: architectural isolation (planner / quarantine / executor)."""

from app.guardrails.s2_isolation.executor import ExecutionResult, PlanExecutor, StepResult
from app.guardrails.s2_isolation.privileged_llm_inference import PrivilegedLLM, PrivilegedPlanResult
from app.guardrails.s2_isolation.quarantined_llm_inference import QuarantineResult, QuarantinedLLM
from app.guardrails.s2_isolation.schema import AgentPlan, ExtractedContent, PlanStep

PlannerLLM = PrivilegedLLM
PlannerResult = PrivilegedPlanResult

__all__ = [
    "AgentPlan",
    "ExecutionResult",
    "ExtractedContent",
    "PlanExecutor",
    "PlanStep",
    "PlannerLLM",
    "PlannerResult",
    "PrivilegedLLM",
    "PrivilegedPlanResult",
    "QuarantineResult",
    "QuarantinedLLM",
    "StepResult",
]
