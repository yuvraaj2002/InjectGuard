from __future__ import annotations

import json
import logging
from typing import Any

import ollama
from rich import print

from app.agent.prompt import SYSTEM_PROMPT
from app.config import MAX_TOOL_ROUNDS, OLLAMA_HOST, OLLAMA_MODEL
from app.tools.email_tool import EMAIL_TOOL_SCHEMAS, read_email, send_email
from app.tools.search_docs import SEARCH_DOCS_TOOL, format_hits, search_docs

logger = logging.getLogger(__name__)


class BaselineAgent:
    """Vulnerable baseline agent: tool outputs enter context with no guards."""

    def __init__(
        self,
        *,
        model: str = OLLAMA_MODEL,
        host: str = OLLAMA_HOST,
        max_tool_rounds: int = MAX_TOOL_ROUNDS,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self.model = model
        self.max_tool_rounds = max_tool_rounds
        self.system_prompt = system_prompt
        self.tools: list[dict[str, Any]] = [SEARCH_DOCS_TOOL, *EMAIL_TOOL_SCHEMAS]
        self._client = ollama.Client(host=host)

    @staticmethod
    def _parse_tool_arguments(raw_args: Any) -> dict[str, Any]:
        if isinstance(raw_args, str):
            try:
                parsed = json.loads(raw_args)
            except json.JSONDecodeError:
                return {"query": raw_args}
            return parsed if isinstance(parsed, dict) else {"query": str(parsed)}
        if isinstance(raw_args, dict):
            return dict(raw_args)
        return {}

    def _run_tool(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "search_docs":
            query = str(arguments.get("query", "")).strip()
            logger.info("Running tool search_docs query=%r", query)
            hits = search_docs(query)
            # Intentionally naive: raw retrieved text goes straight back to the model.
            return format_hits(hits)

        if name == "read_email":
            email_id = arguments.get("email_id")
            query = arguments.get("query")
            logger.info("Running tool read_email email_id=%r query=%r", email_id, query)
            return read_email(
                email_id=str(email_id).strip() if email_id else None,
                query=str(query).strip() if query else None,
            )

        if name == "send_email":
            to = str(arguments.get("to", "")).strip()
            subject = str(arguments.get("subject", "")).strip()
            body = str(arguments.get("body", "")).strip()
            logger.info("Running tool send_email to=%r subject=%r", to, subject)
            if not to or not subject or not body:
                return "send_email requires to, subject, and body."
            return send_email(to=to, subject=subject, body=body)

        logger.warning("Unknown tool requested: %s", name)
        return f"Unknown tool: {name}"

    def _print_model_response(self, round_index: int, assistant_message: Any) -> None:
        content = (assistant_message.content or "").strip()
        tool_calls = assistant_message.tool_calls or []
        print(f"[bold cyan]Model response (round {round_index})[/bold cyan]")
        if content:
            print(content)
        else:
            print("[dim]<empty content>[/dim]")
        if tool_calls:
            printed_calls = [
                {
                    "name": call.function.name,
                    "arguments": self._parse_tool_arguments(call.function.arguments or {}),
                }
                for call in tool_calls
            ]
            print("[bold yellow]tool_calls[/bold yellow]", printed_calls)

    def chat(self, message: str) -> str:
        logger.info("Starting baseline chat with model=%s", self.model)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": message},
        ]

        for round_index in range(1, self.max_tool_rounds + 1):
            logger.info("Calling Ollama (round %s/%s)", round_index, self.max_tool_rounds)
            response = self._client.chat(
                model=self.model,
                messages=messages,
                tools=self.tools,
            )
            assistant_message = response.message
            self._print_model_response(round_index, assistant_message)
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": assistant_message.tool_calls,
                }
            )

            if not assistant_message.tool_calls:
                reply = (assistant_message.content or "").strip() or "No response generated."
                logger.info("Baseline chat completed without further tool calls")
                return reply

            for tool_call in assistant_message.tool_calls:
                name = tool_call.function.name
                arguments = self._parse_tool_arguments(tool_call.function.arguments or {})
                logger.info("Model requested tool=%s args=%s", name, arguments)
                tool_result = self._run_tool(name, arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": tool_result,
                    }
                )

        logger.warning(
            "Reached max tool rounds (%s); asking for a final answer",
            self.max_tool_rounds,
        )
        final = self._client.chat(model=self.model, messages=messages)
        self._print_model_response(self.max_tool_rounds + 1, final.message)
        reply = (final.message.content or "").strip() or "No response generated."
        logger.info("Baseline chat completed after max tool rounds")
        return reply


def run_chat(message: str, *, model: str = OLLAMA_MODEL) -> str:
    """Convenience wrapper used by the API router."""
    return BaselineAgent(model=model).chat(message)
