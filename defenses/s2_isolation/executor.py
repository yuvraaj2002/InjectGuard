"""Deterministic plan executor: walks a pinned AgentPlan and calls real tools.

No LLM here. `$var` placeholders resolve from a simple dict; Q-LLM fills them later.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from app.tools.email_tool import read_email, send_email
from app.tools.search_docs import format_hits, search_docs
from app.tools.ticket_tools import create_ticket, read_ticket
from defenses.s2_isolation.schema import ALLOWED_TOOLS, AgentPlan, PlanStep, is_variable_ref

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


def _dispatch_tool(name: str, arguments: dict[str, Any]) -> str:
    """Call one known tool. Same surface as the baseline agent."""
    if name == "search_docs":
        return format_hits(search_docs(str(arguments.get("query", "")).strip()))

    if name == "read_email":
        return read_email(email_id=_optional_str(arguments.get("email_id")), query=_optional_str(arguments.get("query")))

    if name == "send_email":
        to = str(arguments.get("to", "")).strip()
        subject = str(arguments.get("subject", "")).strip()
        body = str(arguments.get("body", "")).strip()
        if not to or not subject or not body:
            return "send_email requires to, subject, and body."
        return send_email(to=to, subject=subject, body=body)

    if name == "read_ticket":
        return read_ticket(ticket_id=_optional_str(arguments.get("ticket_id")), query=_optional_str(arguments.get("query")))

    if name == "create_ticket":
        title = str(arguments.get("title", "")).strip()
        project = str(arguments.get("project", "")).strip()
        severity = str(arguments.get("severity", "")).strip()
        summary = str(arguments.get("summary", "")).strip()
        assignee = _optional_str(arguments.get("assignee"))
        if not title or not project or not severity or not summary:
            return "create_ticket requires title, project, severity, and summary."
        return create_ticket(title=title, project=project, severity=severity, summary=summary, assignee=assignee)

    return f"Unknown tool: {name}"


class PlanExecutor:
    """Walk a pinned plan step-by-step and execute tools in order."""

    def __init__(self, *, tool_runner: Callable[[str, dict[str, Any]], str] | None = None, stop_on_error: bool = True) -> None:
        self._run_tool = tool_runner or _dispatch_tool
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

        logger.info("PlanExecutor step[%s] %s args=%s", index, step.tool, resolved)
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
    demo = AgentPlan(goal="Read a known email", steps=[PlanStep(tool="read_email", args={"email_id": "email-003"}, save_as="email_raw")])
    outcome = PlanExecutor().execute(demo)
    print("ok=", outcome.ok)
    for step in outcome.steps:
        print(f"[{step.index}] {step.tool} ok={step.ok} error={step.error}")
        print(step.output[:400], "\n---")
    if "email_raw" in outcome.variables:
        print("saved variable email_raw chars=", len(outcome.variables["email_raw"]))
