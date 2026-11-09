from __future__ import annotations

import json
from typing import Any

import ollama

from app.config import OLLAMA_HOST, OLLAMA_MODEL
from app.tools.search_docs import format_hits, search_docs

SYSTEM_PROMPT = """You are OpsPilot, an internal support/ops assistant.

Use the search_docs tool to look up company documentation before answering
policy, access, password, ticket, or VPN questions. Prefer retrieved docs over
guessing. Keep answers concise and practical.
"""

SEARCH_DOCS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_docs",
        "description": (
            "Keyword search over internal markdown docs. "
            "Use for password reset, VPN, tickets, API notes, and similar topics."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords to search for in internal docs.",
                }
            },
            "required": ["query"],
        },
    },
}


def _client() -> ollama.Client:
    return ollama.Client(host=OLLAMA_HOST)


def _run_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "search_docs":
        query = str(arguments.get("query", "")).strip()
        hits = search_docs(query)
        # Intentionally naive: raw retrieved text goes straight back to the model.
        return format_hits(hits)
    return f"Unknown tool: {name}"


def run_chat(message: str, *, model: str = OLLAMA_MODEL) -> str:
    """Vulnerable baseline: tool outputs are concatenated into context with no guards."""
    client = _client()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]

    # One tool round-trip is enough for this skeleton.
    first = client.chat(
        model=model,
        messages=messages,
        tools=[SEARCH_DOCS_TOOL],
    )
    assistant_message = first.message
    messages.append(
        {
            "role": "assistant",
            "content": assistant_message.content or "",
            "tool_calls": assistant_message.tool_calls,
        }
    )

    if not assistant_message.tool_calls:
        return (assistant_message.content or "").strip() or "No response generated."

    for tool_call in assistant_message.tool_calls:
        name = tool_call.function.name
        raw_args = tool_call.function.arguments or {}
        if isinstance(raw_args, str):
            try:
                arguments = json.loads(raw_args)
            except json.JSONDecodeError:
                arguments = {"query": raw_args}
        else:
            arguments = dict(raw_args)

        tool_result = _run_tool(name, arguments)
        messages.append(
            {
                "role": "tool",
                "tool_name": name,
                "content": tool_result,
            }
        )

    final = client.chat(
        model=model,
        messages=messages,
        tools=[SEARCH_DOCS_TOOL],
    )
    return (final.message.content or "").strip() or "No response generated."
