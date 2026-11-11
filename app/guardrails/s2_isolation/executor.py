"""Deterministic plan executor: walks a pinned AgentPlan and calls real tools.

No LLM here. `$var` placeholders resolve from a simple dict; Q-LLM fills them later.
Session user_id is injected into read tools by the executor, not by the plan/model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from app.config import DEFAULT_USER_ID
from app.tools.get_account import get_account
from app.tools.issue_refund import issue_refund
from app.tools.list_payees import list_payees
from app.tools.read_dispute import read_dispute
from app.tools.search_policies import search_policies
from app.tools.transfer_funds import transfer_funds
from app.guardrails.s2_isolation.schema import ALLOWED_TOOLS, AgentPlan, PlanStep, is_variable_ref

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    index: int
    tool: str
    args: dict[str, Any]
    output: str
    save_as: str | None = None
    ok: bool = True
    error: str | None = None


@dataclass
class ExecutionResult:
    goal: str
    steps: list[StepResult] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)
    ok: bool = True
    stopped_at: int | None = None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dispatch_tool(name: str, arguments: dict[str, Any], *, user_id: str = DEFAULT_USER_ID) -> str:
    """Call one known tool. Same surface as the baseline agent."""
    if name == "search_policies":
        return search_policies(str(arguments.get("query", "")).strip(), user_id=user_id)

    if name == "read_dispute":
        return read_dispute(
            user_id=user_id,
            dispute_id=_optional_str(arguments.get("dispute_id")),
            query=_optional_str(arguments.get("query")),
        )

    if name == "get_account":
        return get_account(str(arguments.get("account_id", "")).strip())

    if name == "list_payees":
        return list_payees(str(arguments.get("account_id", "")).strip())

    if name == "transfer_funds":
        return transfer_funds(
            from_account=str(arguments.get("from_account", "")).strip(),
            to_account=str(arguments.get("to_account", "")).strip(),
            amount=arguments.get("amount", ""),
            currency=str(arguments.get("currency", "INR")).strip() or "INR",
            memo=_optional_str(arguments.get("memo")),
        )

    if name == "issue_refund":
        return issue_refund(
            dispute_id=str(arguments.get("dispute_id", "")).strip(),
            to_account=str(arguments.get("to_account", "")).strip(),
            amount=arguments.get("amount", ""),
            reason=_optional_str(arguments.get("reason")),
        )

    return f"Unknown tool: {name}"


class PlanExecutor:
    """Walk a pinned plan step-by-step and execute tools in order."""

    def __init__(
        self,
        *,
        tool_runner: Callable[[str, dict[str, Any]], str] | None = None,
        stop_on_error: bool = True,
        user_id: str = DEFAULT_USER_ID,
    ) -> None:
        self.user_id = (user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
        self._run_tool = tool_runner or (lambda name, args: _dispatch_tool(name, args, user_id=self.user_id))
        self.stop_on_error = stop_on_error

    def resolve_args(self, args: dict[str, Any], variables: dict[str, str]) -> tuple[dict[str, Any], str | None]:
        """Replace `$name` values from variables. Returns (resolved, error)."""
        resolved: dict[str, Any] = {}
        for key, value in args.items():
            if is_variable_ref(value):
                name = str(value).strip()[1:]
                if name not in variables:
                    return {}, f"unresolved variable ${name}"
                resolved[key] = variables[name]
            else:
                resolved[key] = value
        return resolved, None

    def run_step(self, step: PlanStep, *, index: int, variables: dict[str, str]) -> StepResult:
        if step.tool not in ALLOWED_TOOLS:
            return StepResult(index=index, tool=step.tool, args=dict(step.args), output="", save_as=step.save_as, ok=False, error=f"unknown tool: {step.tool}")

        resolved, err = self.resolve_args(step.args, variables)
        if err is not None:
            return StepResult(index=index, tool=step.tool, args=dict(step.args), output="", save_as=step.save_as, ok=False, error=err)

        logger.info("PlanExecutor step[%s] %s args=%s user_id=%s", index, step.tool, resolved, self.user_id)
        try:
            output = self._run_tool(step.tool, resolved)
        except Exception as exc:  # noqa: BLE001 — surface tool failures as step errors
            logger.exception("PlanExecutor step[%s] %s failed", index, step.tool)
            return StepResult(index=index, tool=step.tool, args=resolved, output="", save_as=step.save_as, ok=False, error=str(exc))

        if step.save_as:
            variables[step.save_as] = output
        return StepResult(index=index, tool=step.tool, args=resolved, output=output, save_as=step.save_as, ok=True)

    def execute(self, plan: AgentPlan, *, initial_variables: dict[str, str] | None = None) -> ExecutionResult:
        """Execute every step in order. Does not call any LLM."""
        variables: dict[str, str] = dict(initial_variables or {})
        results: list[StepResult] = []

        for index, step in enumerate(plan.steps):
            result = self.run_step(step, index=index, variables=variables)
            results.append(result)
            if not result.ok and self.stop_on_error:
                return ExecutionResult(goal=plan.goal, steps=results, variables=variables, ok=False, stopped_at=index)

        return ExecutionResult(goal=plan.goal, steps=results, variables=variables, ok=all(s.ok for s in results), stopped_at=None)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo = AgentPlan(goal="List my disputes", steps=[PlanStep(tool="read_dispute", args={}, save_as="queue")])
    outcome = PlanExecutor(user_id="op-001").execute(demo)
    print("ok=", outcome.ok)
    for step in outcome.steps:
        print(f"[{step.index}] {step.tool} ok={step.ok} error={step.error}")
        print(step.output[:400], "\n---")
