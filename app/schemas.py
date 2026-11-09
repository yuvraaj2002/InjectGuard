from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, examples=["How do I reset my password?"])


class ChatResponse(BaseModel):
    reply: str = Field(
        examples=["This is a fixed placeholder response from OpsPilot."]
    )
    message: str
