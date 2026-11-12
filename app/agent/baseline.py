"""Baseline BankOps agent: Ollama tool-calling loop (propose → execute → re-enter)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

import ollama

from app.agent.prompt import SYSTEM_PROMPT
from app.config import DEFAULT_USER_ID, MAX_TOOL_ROUNDS, OLLAMA_HOST, OLLAMA_MODEL
from app.guardrails.s1_detection.guard import ContentGuard, GuardEvent
from app.tools.get_account import GET_ACCOUNT_TOOL, get_account
from app.tools.issue_refund import ISSUE_REFUND_TOOL, issue_refund
from app.tools.list_payees import LIST_PAYEES_TOOL, list_payees
from app.tools.read_dispute import READ_DISPUTE_TOOL, read_dispute
from app.tools.search_policies import SEARCH_POLICIES_TOOL, search_policies
from app.tools.transfer_funds import TRANSFER_FUNDS_TOOL, transfer_funds

logger = logging.getLogger(__name__)

TOOL_SCHEMAS: list[dict[str, Any]] = [
    SEARCH_POLICIES_TOOL,
    READ_DISPUTE_TOOL,
    GET_ACCOUNT_TOOL,
    LIST_PAYEES_TOOL,
    TRANSFER_FUNDS_TOOL,
    ISSUE_REFUND_TOOL,
]

# name → (arguments, session_user_id) → tool output string
ToolHandler = Callable[[dict[str, Any], str], str]


def _str_arg(arguments: dict[str, Any], key: str, default: str = "") -> str:
    return str(arguments.get(key, default) or "").strip()


def _opt_str(arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "search_policies": lambda args, user_id: search_policies(
        _str_arg(args, "query"), user_id=user_id
    ),
    "read_dispute": lambda args, user_id: read_dispute(
        user_id=user_id,
        dispute_id=_opt_str(args, "dispute_id"),
        query=_opt_str(args, "query"),
    ),
    "get_account": lambda args, _user_id: get_account(_str_arg(args, "account_id")),
    "list_payees": lambda args, _user_id: list_payees(_str_arg(args, "account_id")),
    "transfer_funds": lambda args, _user_id: transfer_funds(
        from_account=_str_arg(args, "from_account"),
        to_account=_str_arg(args, "to_account"),
        amount=args.get("amount", ""),
        currency=_str_arg(args, "currency", "INR") or "INR",
        memo=_opt_str(args, "memo"),
    ),
    "issue_refund": lambda args, _user_id: issue_refund(
        dispute_id=_str_arg(args, "dispute_id"),
        to_account=_str_arg(args, "to_account"),
        amount=args.get("amount", ""),
        reason=_opt_str(args, "reason"),
    ),
}


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
    user_id: str = DEFAULT_USER_ID
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    guard_events: list[GuardEvent] = field(default_factory=list)
    plan: dict[str, Any] | None = None
    facts: list[dict[str, Any]] = field(default_factory=list)
    blocked: bool = False


class BaselineAgent:
    """Tool-calling agent: model proposes tools → app executes → S1 filters → re-enter."""

    def __init__(
        self,
        *,
        model: str = OLLAMA_MODEL,
        host: str = OLLAMA_HOST,
        max_tool_rounds: int = MAX_TOOL_ROUNDS,
        system_prompt: str = SYSTEM_PROMPT,
        user_id: str = DEFAULT_USER_ID,
        content_guard: ContentGuard | None = None,
    ) -> None:
        self.model = model
        self.max_tool_rounds = max_tool_rounds
        self.system_prompt = system_prompt
        self.user_id = (user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
        self.content_guard = content_guard
        self.tools = TOOL_SCHEMAS
        self._client = ollama.Client(host=host)

    @property
    def available_tool_names(self) -> list[str]:
        return [tool["function"]["name"] for tool in self.tools]

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool["function"]["name"],
                "description": tool["function"].get("description", ""),
                "parameters": tool["function"].get("parameters", {}),
            }
            for tool in self.tools
        ]

    @staticmethod
    def _parse_args(raw_args: Any) -> dict[str, Any]:
        if isinstance(raw_args, dict):
            return dict(raw_args)
        if isinstance(raw_args, str):
            try:
                parsed = json.loads(raw_args)
            except json.JSONDecodeError:
                return {"query": raw_args}
            return parsed if isinstance(parsed, dict) else {"query": str(parsed)}
        return {}

    def _run_tool(self, name: str, arguments: dict[str, Any]) -> str:
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            logger.warning("Unknown tool requested: %s", name)
            return f"Unknown tool: {name}"
        # Session identity always wins — never trust a model-supplied user_id.
        logger.info("Running tool=%s user_id=%s args=%s", name, self.user_id, arguments)
        return handler(arguments, self.user_id)

    def chat(self, message: str) -> ChatResult:
        """Loop: chat(with tools) → execute → S1 filter output → re-enter → repeat."""
        logger.info("Starting chat model=%s user_id=%s", self.model, self.user_id)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": message},
        ]
        tool_calls: list[ToolCallRecord] = []
        guard_events: list[GuardEvent] = []

        for round_index in range(1, self.max_tool_rounds + 1):
            response = self._client.chat(
                model=self.model,
                messages=messages,
                tools=self.tools,
            )
            assistant = response.message
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant.content or "",
                    "tool_calls": assistant.tool_calls,
                }
            )

            if not assistant.tool_calls:
                reply = (assistant.content or "").strip() or "No response generated."
                logger.info("Chat done after %s round(s), %s tool call(s)", round_index, len(tool_calls))
                return ChatResult(
                    reply=reply,
                    model=self.model,
                    available_tools=self.available_tool_names,
                    user_id=self.user_id,
                    tool_calls=tool_calls,
                    guard_events=guard_events,
                )

            for call in assistant.tool_calls:
                name = call.function.name
                arguments = self._parse_args(call.function.arguments or {})
                output = self._run_tool(name, arguments)
                if self.content_guard is not None:
                    output, event = self.content_guard.filter_tool_output(name, output)
                    if event is not None:
                        guard_events.append(event)
                tool_calls.append(
                    ToolCallRecord(round=round_index, name=name, arguments=arguments, output=output)
                )
                messages.append({"role": "tool", "tool_name": name, "content": output})

        logger.warning("Hit max tool rounds (%s); requesting final answer", self.max_tool_rounds)
        final = self._client.chat(model=self.model, messages=messages)
        reply = (final.message.content or "").strip() or "No response generated."
        return ChatResult(
            reply=reply,
            model=self.model,
            available_tools=self.available_tool_names,
            user_id=self.user_id,
            tool_calls=tool_calls,
            guard_events=guard_events,
        )


def run_chat(message: str, *, model: str = OLLAMA_MODEL, user_id: str = DEFAULT_USER_ID) -> ChatResult:
    """CLI/eval entry: S1 gate then baseline agent (same path as POST /chat)."""
    from app.agent.chat_helper import handle_chat

    return handle_chat(message, model=model, user_id=user_id)
