"""Privileged planner LLM (P-LLM): user request + tool schemas → pinned AgentPlan."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import ollama
from pydantic import ValidationError

from app.config import MAX_PLAN_STEPS, OLLAMA_HOST, OLLAMA_MODEL, PLANNER_MODEL
from app.tools.email_tool import EMAIL_TOOL_SCHEMAS
from app.tools.get_account import GET_ACCOUNT_TOOL
from app.tools.list_payees import LIST_PAYEES_TOOL
from app.tools.read_dispute import READ_DISPUTE_TOOL
from app.tools.search_policies import SEARCH_POLICIES_TOOL
from app.tools.ticket_tools import TICKET_TOOL_SCHEMAS
from defenses.s2_isolation.prompt import PLANNER_SYSTEM_PROMPT, build_planner_user_message, format_tool_catalog
from defenses.s2_isolation.schema import ALLOWED_TOOLS, SENSITIVE_PARAMS, AgentPlan, is_variable_ref

logger = logging.getLogger(__name__)
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


@dataclass
class PlannerResult:
    plan: AgentPlan | None
    raw_text: str
    model: str
    valid: bool
    errors: list[str] = field(default_factory=list)


def default_tool_catalog() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for schema in (
        SEARCH_POLICIES_TOOL,
        READ_DISPUTE_TOOL,
        GET_ACCOUNT_TOOL,
        LIST_PAYEES_TOOL,
        *EMAIL_TOOL_SCHEMAS,
        *TICKET_TOOL_SCHEMAS,
    ):
        function = schema.get("function") or {}
        tools.append({"name": function.get("name", ""), "description": function.get("description", ""), "parameters": function.get("parameters", {})})
    return tools


def extract_json_object(text: str) -> dict[str, Any]:
    """Best-effort JSON object extraction from model output."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("empty planner output")

    fence = _JSON_FENCE_RE.search(cleaned)
    if fence:
        cleaned = fence.group(1).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object found in planner output")
    parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("planner JSON root must be an object")
    return parsed


def validate_plan(plan: AgentPlan, *, max_steps: int = MAX_PLAN_STEPS) -> list[str]:
    """Structural checks beyond Pydantic. $variables are allowed as Q-LLM slots."""
    errors: list[str] = []
    warnings: list[str] = []
    if len(plan.steps) > max_steps:
        errors.append(f"too many steps: {len(plan.steps)} > {max_steps}")

    for index, step in enumerate(plan.steps):
        if step.tool not in ALLOWED_TOOLS:
            errors.append(f"step[{index}]: unknown tool {step.tool!r}")
        sensitive = SENSITIVE_PARAMS.get(step.tool, frozenset())
        for key, value in step.args.items():
            if key in sensitive and isinstance(value, str) and not is_variable_ref(value):
                warnings.append(f"step[{index}].args.{key}: literal sensitive value (needs allowlist/HITL in S3)")

    return errors + [f"warning: {item}" for item in warnings]


class PlannerLLM:
    """Privileged planner: schemas + user text → AgentPlan. No tool execution."""

    def __init__(self, *, model: str = PLANNER_MODEL, host: str = OLLAMA_HOST, system_prompt: str = PLANNER_SYSTEM_PROMPT, tools: list[dict[str, Any]] | None = None, max_steps: int = MAX_PLAN_STEPS) -> None:
        self.model = model or OLLAMA_MODEL
        self.system_prompt = system_prompt
        self.tools = tools if tools is not None else default_tool_catalog()
        self.max_steps = max_steps
        self._client = ollama.Client(host=host)

    def plan(self, user_request: str) -> PlannerResult:
        catalog = format_tool_catalog(self.tools)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": build_planner_user_message(user_request, catalog)},
        ]
        logger.info("PlannerLLM requesting plan model=%s", self.model)
        response = self._client.chat(model=self.model, messages=messages)
        raw = (response.message.content or "").strip()
        logger.info("PlannerLLM raw output chars=%s", len(raw))

        errors: list[str] = []
        try:
            agent_plan = AgentPlan.model_validate(extract_json_object(raw))
        except (ValueError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning("PlannerLLM parse/validate failed: %s", exc)
            return PlannerResult(plan=None, raw_text=raw, model=self.model, valid=False, errors=[str(exc)])

        if len(agent_plan.steps) > self.max_steps:
            errors.append(f"truncating plan from {len(agent_plan.steps)} to {self.max_steps}")
            agent_plan = agent_plan.model_copy(update={"steps": agent_plan.steps[: self.max_steps]})

        errors.extend(validate_plan(agent_plan, max_steps=self.max_steps))
        hard_errors = [err for err in errors if not err.startswith("warning:")]
        return PlannerResult(plan=agent_plan, raw_text=raw, model=self.model, valid=len(hard_errors) == 0, errors=errors)


def plan_to_dict(plan: AgentPlan) -> dict[str, Any]:
    return plan.model_dump()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    planner = PlannerLLM()
    for sample in ["How do I reset my password?", "Read email-003 and summarize it.", "List open tickets."]:
        print("\n===", sample)
        result = planner.plan(sample)
        print("valid=", result.valid, "errors=", result.errors)
        print(json.dumps(plan_to_dict(result.plan), indent=2) if result.plan else result.raw_text[:500])
