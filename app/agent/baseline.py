from __future__ import annotations

import json
import logging
from typing import Any

import ollama

from app.config import OLLAMA_HOST, OLLAMA_MODEL
from app.tools.search_docs import format_hits, search_docs

logger = logging.getLogger(__name__)

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
        logger.info("Running tool search_docs query=%r", query)
        hits = search_docs(query)
        # Intentionally naive: raw retrieved text goes straight back to the model.
        return format_hits(hits)
    logger.warning("Unknown tool requested: %s", name)
    return f"Unknown tool: {name}"


def run_chat(message: str, *, model: str = OLLAMA_MODEL) -> str:
    """Vulnerable baseline: tool outputs are concatenated into context with no guards."""
    logger.info("Starting baseline chat with model=%s", model)
    client = _client()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]

    # One tool round-trip is enough for this skeleton.
    logger.info("Calling Ollama (tool selection pass)")
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
        logger.info("Model answered without tool calls")
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

        logger.info("Model requested tool=%s args=%s", name, arguments)
        tool_result = _run_tool(name, arguments)
        messages.append(
            {
                "role": "tool",
                "tool_name": name,
                "content": tool_result,
            }
        )

    logger.info("Calling Ollama (final answer pass)")
    final = client.chat(
        model=model,
        messages=messages,
        tools=[SEARCH_DOCS_TOOL],
    )
    reply = (final.message.content or "").strip() or "No response generated."
    logger.info("Baseline chat completed")
    return reply
