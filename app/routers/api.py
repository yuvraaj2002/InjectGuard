import logging

from fastapi import APIRouter, HTTPException

from app.agent.baseline import run_chat
from app.schemas import ChatRequest, ChatResponse, HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    logger.info("Health check requested")
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    logger.info("Chat request received: %s", payload.message)
    try:
        reply = run_chat(payload.message)
    except Exception as exc:  # noqa: BLE001 - surface local Ollama failures cleanly
        logger.exception("Chat backend failed")
        raise HTTPException(
            status_code=502,
            detail=f"Chat backend failed: {exc}",
        ) from exc

    logger.info("Chat response ready (%s chars)", len(reply))
    return ChatResponse(message=payload.message, reply=reply)
