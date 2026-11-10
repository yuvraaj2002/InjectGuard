import logging

from fastapi import APIRouter, HTTPException

from app.agent.baseline import BaselineAgent, run_chat
from app.config import (
    DECISION_MODEL,
    DEFAULT_USER_ID,
    GUARD_INPUT,
    GUARD_RETRIEVED_CONTEXT,
    GUARD_TOOL_OUTPUT,
    OLLAMA_MODEL,
)
from app.schemas import (
    ChatRequest,
    ChatResponse,
    GuardEventTrace,
    GuardLayerInfo,
    HealthResponse,
    ToolCallTrace,
    ToolInfo,
    ToolsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _guard_layers() -> list[GuardLayerInfo]:
    return [
        GuardLayerInfo(
            id="user_input",
            label="User input",
            enabled=GUARD_INPUT,
            description="Decision model scores the user message before the agent runs.",
        ),
        GuardLayerInfo(
            id="retrieved_context",
            label="Retrieved context",
            enabled=GUARD_RETRIEVED_CONTEXT,
            description="Scores search_policies / read_dispute / get_account / list_payees text before it enters context.",
        ),
        GuardLayerInfo(
            id="tool_output",
            label="Tool output",
            enabled=GUARD_TOOL_OUTPUT,
            description="Scores other tool results (e.g. transfer_funds / issue_refund confirmations) before re-entry.",
        ),
    ]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    logger.info("Health check requested")
    return HealthResponse(status="ok")


@router.get("/tools", response_model=ToolsResponse)
def list_tools() -> ToolsResponse:
    agent = BaselineAgent()
    tools = [ToolInfo(**tool) for tool in agent.list_tools()]
    logger.info("Tools listed count=%s", len(tools))
    return ToolsResponse(
        model=OLLAMA_MODEL,
        tools=tools,
        decision_model=DECISION_MODEL,
        guard_layers=_guard_layers(),
    )


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    user_id = (payload.user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    logger.info("Chat request received user_id=%s message=%s", user_id, payload.message)
    try:
        result = run_chat(payload.message, user_id=user_id)
    except Exception as exc:  # noqa: BLE001 - surface local Ollama failures cleanly
        logger.exception("Chat backend failed")
        raise HTTPException(
            status_code=502,
            detail=f"Chat backend failed: {exc}",
        ) from exc

    logger.info(
        "Chat response ready user_id=%s (%s chars, %s tool calls, %s guard events, blocked=%s)",
        result.user_id,
        len(result.reply),
        len(result.tool_calls),
        len(result.guard_events),
        result.blocked,
    )
    return ChatResponse(
        message=payload.message,
        reply=result.reply,
        model=result.model,
        user_id=result.user_id,
        available_tools=result.available_tools,
        tool_calls=[
            ToolCallTrace(
                round=call.round,
                name=call.name,
                arguments=call.arguments,
                output=call.output,
            )
            for call in result.tool_calls
        ],
        guard_events=[
            GuardEventTrace(
                layer=event.layer,
                action=event.action,
                injection=event.injection,
                confidence=event.confidence,
                reason=event.reason,
                tool_name=event.tool_name,
            )
            for event in result.guard_events
        ],
        blocked=result.blocked,
    )
