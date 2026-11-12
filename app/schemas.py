from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, examples=["What is our refund policy for unauthorized UPI?"])
    # Stand-in for identity resolved from an auth token. Not chosen by the model.
    user_id: str = Field(default="op-001", min_length=1, examples=["op-001"])


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
    action: Literal["allow", "block", "drop"]
    injection: bool
    confidence: float
    reason: str
    tool_name: str | None = None


class ChatResponse(BaseModel):
    message: str
    reply: str = Field(description="Final operator-facing reply from the answer model.")
    model: str
    user_id: str = "op-001"
    available_tools: list[str]
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    guard_events: list[GuardEventTrace] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    facts: list[dict[str, Any]] = Field(default_factory=list)
    blocked: bool = False
