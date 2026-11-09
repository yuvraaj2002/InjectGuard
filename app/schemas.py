from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, examples=["How do I reset my password?"])


class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class GuardLayerInfo(BaseModel):
    id: str
    label: str
    enabled: bool
    description: str


class ToolsResponse(BaseModel):
    model: str
    tools: list[ToolInfo]
    decision_model: str = ""
    guard_layers: list[GuardLayerInfo] = Field(default_factory=list)


class ToolCallTrace(BaseModel):
    round: int
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output: str


class GuardEventTrace(BaseModel):
    layer: Literal["user_input", "retrieved_context", "tool_output"]
    action: Literal["allow", "block", "drop", "flag"]
    injection: bool
    confidence: float
    reason: str
    tool_name: str | None = None


class ChatResponse(BaseModel):
    message: str
    reply: str
    model: str
    available_tools: list[str]
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    guard_events: list[GuardEventTrace] = Field(default_factory=list)
    blocked: bool = False
