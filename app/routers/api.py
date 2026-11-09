from fastapi import APIRouter, HTTPException

from app.agent.baseline import run_chat
from app.schemas import ChatRequest, ChatResponse, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        reply = run_chat(payload.message)
    except Exception as exc:  # noqa: BLE001 - surface local Ollama failures cleanly
        raise HTTPException(
            status_code=502,
            detail=f"Chat backend failed: {exc}",
        ) from exc

    return ChatResponse(message=payload.message, reply=reply)
