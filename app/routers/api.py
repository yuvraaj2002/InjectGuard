import logging

from fastapi import APIRouter, HTTPException

from app.agent.baseline import BaselineAgent, run_chat
from app.config import OLLAMA_MODEL
from app.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ToolCallTrace,
    ToolInfo,
    ToolsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    logger.info("Health check requested")
    return HealthResponse(status="ok")


@router.get("/tools", response_model=ToolsResponse)
def list_tools() -> ToolsResponse:
    agent = BaselineAgent()
    tools = [ToolInfo(**tool) for tool in agent.list_tools()]
    logger.info("Tools listed count=%s", len(tools))
    return ToolsResponse(model=OLLAMA_MODEL, tools=tools)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    logger.info("Chat request received: %s", payload.message)
    try:
        result = run_chat(payload.message)
    except Exception as exc:  # noqa: BLE001 - surface local Ollama failures cleanly
        logger.exception("Chat backend failed")
        raise HTTPException(
            status_code=502,
            detail=f"Chat backend failed: {exc}",
        ) from exc

    logger.info(
        "Chat response ready (%s chars, %s tool calls)",
        len(result.reply),
        len(result.tool_calls),
    )
    return ChatResponse(
        message=payload.message,
        reply=result.reply,
        model=result.model,
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
    )
