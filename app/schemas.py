from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, examples=["How do I reset my password?"])


class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolsResponse(BaseModel):
    model: str
    tools: list[ToolInfo]


class ToolCallTrace(BaseModel):
    round: int
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output: str


class ChatResponse(BaseModel):
    message: str
    reply: str
    model: str
    available_tools: list[str]
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
