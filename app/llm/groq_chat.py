"""Groq chat completions used by the planner, quarantine model, and answer model.

Callers need the finished message, so this collects the completion instead of
yielding stream chunks. Generation settings match the Groq Qwen sample:
temperature 0.6, top_p 0.95, max_completion_tokens 2048, reasoning_effort default.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from groq import Groq

from app.config import (
    GROQ_MAX_COMPLETION_TOKENS,
    GROQ_MODEL,
    GROQ_REASONING_EFFORT,
    GROQ_TEMPERATURE,
    GROQ_TOP_P,
)

_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)


def _client() -> Groq:
    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not set. Add it to .env in the project root.")
    return Groq()


def _params(model: str) -> dict[str, Any]:
    return {
        "model": model or GROQ_MODEL,
        "temperature": GROQ_TEMPERATURE,
        "max_completion_tokens": GROQ_MAX_COMPLETION_TOKENS,
        "top_p": GROQ_TOP_P,
        "reasoning_effort": GROQ_REASONING_EFFORT,
        "stream": False,
    }


def _visible(text: str | None) -> str:
    return _THINK_RE.sub("", text or "").strip()


def complete(
    messages: list[dict[str, Any]],
    *,
    model: str = GROQ_MODEL,
    max_completion_tokens: int | None = None,
) -> str:
    """Return the assistant text for a chat that has no tools."""
    params = _params(model)
    if max_completion_tokens is not None:
        params["max_completion_tokens"] = max_completion_tokens
    completion = _client().chat.completions.create(messages=messages, **params)
    return _visible(completion.choices[0].message.content)


@dataclass
class GroqToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class GroqTurn:
    content: str
    tool_calls: list[GroqToolCall] = field(default_factory=list)
    raw_message: dict[str, Any] = field(default_factory=dict)


def complete_with_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    model: str = GROQ_MODEL,
) -> GroqTurn:
    """One tool-calling turn. Append ``raw_message`` before the tool results."""
    completion = _client().chat.completions.create(
        messages=messages,
        tools=tools,
        tool_choice="auto",
        **_params(model),
    )
    message = completion.choices[0].message
    calls: list[GroqToolCall] = []
    for call in message.tool_calls or []:
        raw_args = call.function.arguments or "{}"
        try:
            parsed = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
        except json.JSONDecodeError:
            parsed = {"query": raw_args}
        if not isinstance(parsed, dict):
            parsed = {"query": str(parsed)}
        calls.append(
            GroqToolCall(id=call.id or "", name=call.function.name, arguments=parsed)
        )
    return GroqTurn(
        content=_visible(message.content),
        tool_calls=calls,
        raw_message=message.model_dump(exclude_none=True),
    )
