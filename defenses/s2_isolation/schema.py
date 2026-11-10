"""Structured plan (P-LLM) and extraction schema (Q-LLM)."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_TOOLS: frozenset[str] = frozenset(
    {
        "search_policies",
        "read_dispute",
        "get_account",
        "read_email",
        "send_email",
        "read_ticket",
        "create_ticket",
    }
)

# Must not be filled from untrusted retrieved text without policy later.
SENSITIVE_PARAMS: dict[str, frozenset[str]] = {
    "send_email": frozenset({"to"}),
    "create_ticket": frozenset({"assignee"}),
}

_VAR_RE = re.compile(r"^\$[A-Za-z_][A-Za-z0-9_]*$")
PlanStatus = Literal["ok", "invalid", "empty"]


class PlanStep(BaseModel):
    """One planned tool call. Args may be literals or $variable placeholders."""

    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    save_as: str | None = Field(default=None, description="Variable name (no $) for this step's result.")

    @field_validator("tool")
    @classmethod
    def tool_must_be_known(cls, value: str) -> str:
        name = value.strip()
        if name not in ALLOWED_TOOLS:
            raise ValueError(f"unknown tool: {value!r}")
        return name

    @field_validator("save_as")
    @classmethod
    def save_as_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lstrip("$")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", cleaned):
            raise ValueError(f"invalid save_as: {value!r}")
        return cleaned


class AgentPlan(BaseModel):
    """Pinned control-flow plan. Fixed before untrusted content is read."""

    goal: str = Field(default="", description="Short restatement of the user goal.")
    steps: list[PlanStep] = Field(default_factory=list)
    notes: str | None = Field(default=None, description="Optional planner rationale (not executed).")

    @field_validator("steps")
    @classmethod
    def limit_steps(cls, value: list[PlanStep]) -> list[PlanStep]:
        if len(value) > 8:
            raise ValueError("plan exceeds max 8 steps")
        return value


def is_variable_ref(value: Any) -> bool:
    return isinstance(value, str) and bool(_VAR_RE.match(value.strip()))


class ExtractedContent(BaseModel):
    """Schema-validated facts from untrusted text (Q-LLM output). No tools."""

    summary: str = Field(default="", description="Neutral summary of the content.")
    key_points: list[str] = Field(default_factory=list)
    title: str | None = Field(default=None, description="Suggested short title if relevant.")
    project: str | None = Field(default=None, description="Mentioned project if any.")
    severity: str | None = Field(default=None, description="Mentioned severity if any.")
    # Data only — must NOT be trusted for write-tool sensitive params later.
    mentioned_emails: list[str] = Field(default_factory=list)
    mentioned_people: list[str] = Field(default_factory=list)

    def to_variables(self, *, prefix: str = "extract") -> dict[str, str]:
        base = prefix.lstrip("$") or "extract"
        return {
            f"{base}_summary": self.summary,
            f"{base}_key_points": "; ".join(self.key_points),
            f"{base}_title": self.title or "",
            f"{base}_project": self.project or "",
            f"{base}_severity": self.severity or "",
            f"{base}_mentioned_emails": ", ".join(self.mentioned_emails),
            f"{base}_mentioned_people": ", ".join(self.mentioned_people),
        }
