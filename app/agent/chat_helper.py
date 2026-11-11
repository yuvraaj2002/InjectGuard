"""POST /chat helper: S1 input gate → S2 plan → execute pinned plan → reply."""

from __future__ import annotations

import logging

import ollama

from app.agent.baseline import ChatResult, ToolCallRecord
from app.config import DEFAULT_USER_ID, GUARD_INPUT, OLLAMA_HOST, OLLAMA_MODEL
from app.container import AppContainer
from defenses.s2_isolation.executor import PlanExecutor
from defenses.s2_isolation.planner import plan_to_dict

logger = logging.getLogger(__name__)

BANKOPS_TOOL_NAMES = [
    "search_policies",
    "read_dispute",
    "get_account",
    "list_payees",
    "transfer_funds",
    "issue_refund",
]

_ANSWER_SYSTEM = (
    "You are BankOps. Answer the operator using ONLY the pinned plan goal and the "
    "tool results below. Do not invent tool calls, accounts, or amounts. If results "
    "are incomplete, say what is missing."
)


def handle_chat(
    message: str,
    *,
    user_id: str = DEFAULT_USER_ID,
    model: str = OLLAMA_MODEL,
    container: AppContainer | None = None,
) -> ChatResult:
    """S1 score → S2 planner (schemas only) → deterministic executor → final answer LLM.

    The planner pins control flow before any tool runs. The executor sticks to that
    plan — no runtime ReAct tool picking. The final LLM has no tools; it only writes
    the operator-facing reply from execution results.
    """
    resolved_user_id = (user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    owns_container = container is None
    services = container or AppContainer.build()

    try:
        # --- S1: user-message input classifier (Prompt Guard) ---
        if GUARD_INPUT:
            verdict = services.input_classifier.score(message, source="user_input")
            if verdict.injection:
                logger.warning(
                    "Rejected user message score=%.3f reason=%s model=%s",
                    verdict.confidence,
                    verdict.reason,
                    verdict.model,
                )
                return ChatResult(
                    reply=(
                        "Request blocked: the message looks like a prompt injection/jailbreak "
                        f"({verdict.reason})."
                    ),
                    model=model,
                    available_tools=list(BANKOPS_TOOL_NAMES),
                    user_id=resolved_user_id,
                    blocked=True,
                )

        # --- S2: privileged planner (schemas + user text only; no tool execution) ---
        planner_result = services.planner.plan(message)
        if not planner_result.valid or planner_result.plan is None:
            errors = "; ".join(planner_result.errors) or "invalid or empty plan"
            logger.warning("Planner failed: %s", errors)
            return ChatResult(
                reply=f"Could not build a pinned plan for this request ({errors}).",
                model=planner_result.model,
                available_tools=list(BANKOPS_TOOL_NAMES),
                user_id=resolved_user_id,
                plan=None,
                blocked=False,
            )

        plan = planner_result.plan
        plan_dict = plan_to_dict(plan)
        logger.info("Pinned plan goal=%r steps=%s", plan.goal, [step.tool for step in plan.steps])

        # --- Stick to the plan: deterministic tool execution (no LLM choosing tools) ---
        execution = PlanExecutor(user_id=resolved_user_id).execute(plan)
        tool_calls = [
            ToolCallRecord(
                round=step.index + 1,
                name=step.tool,
                arguments=step.args,
                output=step.output if step.ok else f"ERROR: {step.error}",
            )
            for step in execution.steps
        ]

        if not execution.ok:
            failed = next((step for step in execution.steps if not step.ok), None)
            detail = f"{failed.tool}: {failed.error}" if failed else "unknown step error"
            logger.warning("Plan execution stopped: %s", detail)
            return ChatResult(
                reply=(
                    f"Pinned plan stopped during execution ({detail}). "
                    "Control flow was not rewritten; fix args / unresolved $variables and retry."
                ),
                model=planner_result.model,
                available_tools=list(BANKOPS_TOOL_NAMES),
                user_id=resolved_user_id,
                tool_calls=tool_calls,
                plan=plan_dict,
                blocked=False,
            )

        # --- Final answer: LLM with no tools, only plan goal + tool outputs ---
        reply = _answer_from_execution(message, plan.goal, tool_calls, model=model)
        return ChatResult(
            reply=reply,
            model=model,
            available_tools=list(BANKOPS_TOOL_NAMES),
            user_id=resolved_user_id,
            tool_calls=tool_calls,
            plan=plan_dict,
            blocked=False,
        )
    finally:
        if owns_container:
            services.close()


def _answer_from_execution(
    user_message: str,
    goal: str,
    tool_calls: list[ToolCallRecord],
    *,
    model: str,
) -> str:
    """No-tools LLM: turn execution traces into an operator reply."""
    if not tool_calls:
        return "Plan had no tool steps. Ask a more specific BankOps question."

    blocks: list[str] = [f"Goal: {goal}", f"Operator request: {user_message.strip()}", "", "Tool results:"]
    for call in tool_calls:
        blocks.append(f"[{call.round}] {call.name} args={call.arguments}")
        blocks.append(call.output)
        blocks.append("---")

    client = ollama.Client(host=OLLAMA_HOST)
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": _ANSWER_SYSTEM},
            {"role": "user", "content": "\n".join(blocks)},
        ],
    )
    return (response.message.content or "").strip() or "No response generated."
