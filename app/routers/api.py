import logging

from fastapi import APIRouter, Depends, HTTPException

from app.agent.baseline import BaselineAgent
from app.agent.chat_helper import handle_chat
from app.config import (
    DEFAULT_USER_ID,
    INPUT_CLASSIFIER_MODEL,
    OLLAMA_MODEL,
)
from app.container import AppContainer
from app.deps import get_container
from app.playground import list_playground_options
from app.schemas import (
    ChatRequest,
    ChatResponse,
    GuardEventTrace,
    GuardLayerInfo,
    HealthResponse,
    PlaygroundClassifyRequest,
    PlaygroundClassifyResponse,
    PlaygroundOptionsResponse,
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
            enabled=True,
            description="Input classifier scores the user message before the agent runs.",
        ),
        GuardLayerInfo(
            id="retrieved_context",
            label="Retrieved context",
            enabled=True,
            description="Scores search_policies / read_dispute / get_account / list_payees text before it re-enters context.",
        ),
        GuardLayerInfo(
            id="tool_output",
            label="Tool output",
            enabled=True,
            description="Scores other tool results (e.g. transfer_funds / issue_refund) before re-entry.",
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
        decision_model=INPUT_CLASSIFIER_MODEL,
        guard_layers=_guard_layers(),
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    container: AppContainer = Depends(get_container),
) -> ChatResponse:
    user_id = (payload.user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    logger.info("Chat request received user_id=%s message=%s", user_id, payload.message)
    try:
        result = handle_chat(payload.message, user_id=user_id, container=container)
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
        plan=result.plan,
        facts=result.facts,
        blocked=result.blocked,
    )


@router.get("/playground/options", response_model=PlaygroundOptionsResponse)
def playground_options() -> PlaygroundOptionsResponse:
    """Jailbreak families and the messages to send to POST /playground/classify."""
    options = list_playground_options()
    logger.info("Playground options listed count=%s", len(options))
    return PlaygroundOptionsResponse(options=options)


@router.post("/playground/classify", response_model=PlaygroundClassifyResponse)
def playground_classify(
    payload: PlaygroundClassifyRequest,
    container: AppContainer = Depends(get_container),
) -> PlaygroundClassifyResponse:
    """Score a labeled message with the S1 input classifier. Does not run the agent."""
    attempt_type = payload.type.strip()
    message = payload.message.strip()
    logger.info("Playground classify type=%s message=%s", attempt_type, message)
    try:
        verdict = container.input_classifier.score(message, source="user_input")
    except Exception as exc:  # noqa: BLE001 - surface classifier failures cleanly
        logger.exception("Playground classifier failed")
        raise HTTPException(
            status_code=502,
            detail=f"Input classifier failed: {exc}",
        ) from exc

    logger.info(
        "Playground classify ready type=%s injection=%s confidence=%.3f",
        attempt_type,
        verdict.injection,
        verdict.confidence,
    )
    return PlaygroundClassifyResponse(
        type=attempt_type,
        message=message,
        injection=verdict.injection,
        confidence=verdict.confidence,
        reason=verdict.reason,
        model=verdict.model,
        source=verdict.source,
        latency_ms=verdict.latency_ms,
    )
