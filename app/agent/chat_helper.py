"""POST /chat helper: S1 user gate → privileged LLM plan. Plan is not executed."""

from __future__ import annotations

import logging

from app.agent.baseline import TOOL_SCHEMAS, ChatResult
from app.config import DEFAULT_USER_ID, OLLAMA_MODEL
from app.container import AppContainer
from app.guardrails.s1_detection.guard import ContentGuard
from app.guardrails.s2_isolation.privileged_llm_inference import PrivilegedLLM, PrivilegedPlanResult
from app.guardrails.s2_isolation.schema import AgentPlan

logger = logging.getLogger(__name__)


def handle_chat(
    message: str,
    *,
    user_id: str = DEFAULT_USER_ID,
    model: str = OLLAMA_MODEL,
    container: AppContainer | None = None,
) -> ChatResult:
    """S1 on the user message, then a privileged LLM plan. Tools are not run."""
    resolved_user_id = (user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    owns_container = container is None
    services = container or AppContainer.build()

    try:
        guard = ContentGuard(classifier=services.input_classifier)

        blocked_reply, input_event = guard.check_user_input(message)
        if blocked_reply is not None:
            logger.warning(
                "Rejected user message reason=%s",
                input_event.reason if input_event else "unknown",
            )
            return ChatResult(
                reply=blocked_reply,
                model=model,
                available_tools=[tool["function"]["name"] for tool in TOOL_SCHEMAS],
                user_id=resolved_user_id,
                guard_events=[input_event] if input_event is not None else [],
                blocked=True,
            )

        planned = PrivilegedLLM(model=model).plan(message)
        logger.info(
            "Privileged plan ready valid=%s steps=%s errors=%s",
            planned.valid,
            len(planned.plan.steps) if planned.plan else 0,
            planned.errors,
        )
        return ChatResult(
            reply=_format_plan_reply(planned),
            model=planned.model,
            available_tools=[tool["function"]["name"] for tool in TOOL_SCHEMAS],
            user_id=resolved_user_id,
            guard_events=[input_event] if input_event is not None else [],
            plan=_plan_payload(planned),
        )
    finally:
        if owns_container:
            services.close()


def _plan_payload(result: PrivilegedPlanResult) -> dict:
    payload: dict = {
        "valid": result.valid,
        "errors": result.errors,
    }
    if result.plan is not None:
        payload.update(result.plan.model_dump())
    if result.plan is None or not result.plan.steps:
        payload["raw_text"] = result.raw_text
    return payload


def _format_plan_reply(result: PrivilegedPlanResult) -> str:
    plan: AgentPlan | None = result.plan
    if plan is None:
        detail = "\n".join(result.errors) or "no JSON plan"
        return f"Privileged LLM did not return a valid plan.\n{detail}"

    lines = [f"Plan (not executed): {plan.goal or 'untitled'}"]
    if not plan.steps:
        lines.append("(no steps)")
    for index, step in enumerate(plan.steps, start=1):
        args = ", ".join(f"{key}={value}" for key, value in step.args.items())
        save = f" → ${step.save_as}" if step.save_as else ""
        lines.append(f"{index}. {step.tool}({args}){save}")
    if plan.notes:
        lines.append(f"Notes: {plan.notes}")
    if result.errors:
        lines.append("Notes from checks: " + "; ".join(result.errors))
    return "\n".join(lines)
