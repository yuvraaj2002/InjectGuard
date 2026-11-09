from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import ollama
from rich import print

from app.agent.prompt import SYSTEM_PROMPT
from app.config import MAX_TOOL_ROUNDS, OLLAMA_HOST, OLLAMA_MODEL
from app.tools.email_tool import EMAIL_TOOL_SCHEMAS, read_email, send_email
from app.tools.search_docs import SEARCH_DOCS_TOOL, format_hits, search_docs
from app.tools.ticket_tools import TICKET_TOOL_SCHEMAS, create_ticket, read_ticket

logger = logging.getLogger(__name__)


@dataclass
class ToolCallRecord:
    round: int
    name: str
    arguments: dict[str, Any]
    output: str


@dataclass
class ChatResult:
    reply: str
    model: str
    available_tools: list[str]
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
        self.tools: list[dict[str, Any]] = [
            SEARCH_DOCS_TOOL,
            *EMAIL_TOOL_SCHEMAS,
            *TICKET_TOOL_SCHEMAS,
        ]
        self._client = ollama.Client(host=host)

    @property
    def available_tool_names(self) -> list[str]:
        return [tool["function"]["name"] for tool in self.tools]

    def list_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for tool in self.tools:
            function = tool["function"]
            tools.append(
                {
                    "name": function["name"],
                    "description": function.get("description", ""),
                    "parameters": function.get("parameters", {}),
                }
            )
        return tools

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
            email_id = _optional_str(arguments.get("email_id"))
            query = _optional_str(arguments.get("query"))
            logger.info("Running tool read_email email_id=%r query=%r", email_id, query)
            return read_email(email_id=email_id, query=query)

        if name == "send_email":
            to = str(arguments.get("to", "")).strip()
            subject = str(arguments.get("subject", "")).strip()
            body = str(arguments.get("body", "")).strip()
            logger.info("Running tool send_email to=%r subject=%r", to, subject)
            if not to or not subject or not body:
                return "send_email requires to, subject, and body."
            return send_email(to=to, subject=subject, body=body)

        if name == "read_ticket":
            ticket_id = _optional_str(arguments.get("ticket_id"))
            query = _optional_str(arguments.get("query"))
            logger.info("Running tool read_ticket ticket_id=%r query=%r", ticket_id, query)
            return read_ticket(ticket_id=ticket_id, query=query)

        if name == "create_ticket":
            title = str(arguments.get("title", "")).strip()
            project = str(arguments.get("project", "")).strip()
            severity = str(arguments.get("severity", "")).strip()
            summary = str(arguments.get("summary", "")).strip()
            assignee = _optional_str(arguments.get("assignee"))
            logger.info(
                "Running tool create_ticket title=%r project=%r severity=%r",
                title,
                project,
                severity,
            )
            if not title or not project or not severity or not summary:
                return "create_ticket requires title, project, severity, and summary."
            return create_ticket(
                title=title,
                project=project,
                severity=severity,
                summary=summary,
                assignee=assignee,
            )

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

    def chat(self, message: str) -> ChatResult:
        logger.info("Starting baseline chat with model=%s", self.model)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": message},
        ]
        tool_calls: list[ToolCallRecord] = []

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
                return ChatResult(
                    reply=reply,
                    model=self.model,
                    available_tools=self.available_tool_names,
                    tool_calls=tool_calls,
                )

            for tool_call in assistant_message.tool_calls:
                name = tool_call.function.name
                arguments = self._parse_tool_arguments(tool_call.function.arguments or {})
                logger.info("Model requested tool=%s args=%s", name, arguments)
                tool_result = self._run_tool(name, arguments)
                tool_calls.append(
                    ToolCallRecord(
                        round=round_index,
                        name=name,
                        arguments=arguments,
                        output=tool_result,
                    )
                )
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
        return ChatResult(
            reply=reply,
            model=self.model,
            available_tools=self.available_tool_names,
            tool_calls=tool_calls,
        )


def run_chat(message: str, *, model: str = OLLAMA_MODEL) -> ChatResult:
    """Convenience wrapper used by the API router."""
    return BaselineAgent(model=model).chat(message)
