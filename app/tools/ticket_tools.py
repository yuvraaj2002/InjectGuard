from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import TICKETS_PATH, TICKET_SINK_PATH

logger = logging.getLogger(__name__)

ALLOWED_PROJECTS = ("ops", "it", "security")
ALLOWED_SEVERITIES = ("P1", "P2", "P3", "P4")

READ_TICKET_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_ticket",
        "description": (
            "Read synthetic support tickets. "
            "To list all tickets, call with NO arguments (do not pass query). "
            "Pass ticket_id to fetch one ticket. "
            "Pass query only for keyword search over title/summary (e.g. 'vpn', 'billing')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Exact ticket id, e.g. ticket-001.",
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Keyword filter for title/summary content. "
                        "Omit this field entirely to list all tickets."
                    ),
                },
            },
            "required": [],
        },
    },
}

CREATE_TICKET_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "create_ticket",
        "description": (
            "Create a support ticket in the local mock ticket sink. "
            "Required: title, project (ops|it|security), severity (P1-P4), summary. "
            "Optional assignee defaults to the project queue."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short ticket title.",
                },
                "project": {
                    "type": "string",
                    "description": "Project key: ops, it, or security.",
                },
                "severity": {
                    "type": "string",
                    "description": "Severity: P1, P2, P3, or P4.",
                },
                "summary": {
                    "type": "string",
                    "description": "Detailed ticket summary.",
                },
                "assignee": {
                    "type": "string",
                    "description": "Optional assignee. Defaults to <project>-queue.",
                },
            },
            "required": ["title", "project", "severity", "summary"],
        },
    },
}

TICKET_TOOL_SCHEMAS: list[dict[str, Any]] = [READ_TICKET_TOOL, CREATE_TICKET_TOOL]


def _load_tickets(path: Path = TICKETS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        logger.warning("Tickets file missing: %s", path)
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _format_ticket(ticket: dict[str, Any]) -> str:
    return (
        f"id: {ticket.get('id')}\n"
        f"title: {ticket.get('title')}\n"
        f"project: {ticket.get('project')}\n"
        f"severity: {ticket.get('severity')}\n"
        f"assignee: {ticket.get('assignee')}\n"
        f"reporter: {ticket.get('reporter')}\n"
        f"status: {ticket.get('status')}\n"
        f"summary:\n{ticket.get('summary', '')}"
    )


def read_ticket(
    ticket_id: str | None = None,
    query: str | None = None,
) -> str:
    """Read synthetic tickets. Untrusted content is returned raw (vulnerable baseline)."""
    tickets = _load_tickets()
    if not tickets:
        return "No tickets available."

    if ticket_id:
        for ticket in tickets:
            if ticket.get("id") == ticket_id:
                logger.info("read_ticket id=%s", ticket_id)
                return _format_ticket(ticket)
        logger.info("read_ticket id=%s not found", ticket_id)
        return f"Ticket not found: {ticket_id}"

    if query:
        tokens = {token.lower() for token in query.split() if token.strip()}
        matches: list[dict[str, Any]] = []
        for ticket in tickets:
            haystack = " ".join(
                [
                    str(ticket.get("id", "")),
                    str(ticket.get("title", "")),
                    str(ticket.get("project", "")),
                    str(ticket.get("summary", "")),
                    str(ticket.get("assignee", "")),
                ]
            ).lower()
            if tokens and all(token in haystack for token in tokens):
                matches.append(ticket)
            elif not tokens:
                matches.append(ticket)
        logger.info("read_ticket query=%r matches=%s", query, len(matches))
        if not matches:
            return f"No tickets matched query={query!r}."
        return "\n\n---\n\n".join(_format_ticket(ticket) for ticket in matches)

    logger.info("read_ticket list_all count=%s", len(tickets))
    summaries = [
        (
            f"{ticket.get('id')}: {ticket.get('title')} "
            f"[{ticket.get('project')}/{ticket.get('severity')}]"
        )
        for ticket in tickets
    ]
    return "Open tickets:\n" + "\n".join(summaries)


def create_ticket(
    title: str,
    project: str,
    severity: str,
    summary: str,
    assignee: str | None = None,
) -> str:
    """Mock create: append to a local JSONL sink. No real ticketing system."""
    project_key = project.strip().lower()
    severity_key = severity.strip().upper()

    if project_key not in ALLOWED_PROJECTS:
        return f"Invalid project={project!r}. Allowed: {', '.join(ALLOWED_PROJECTS)}."
    if severity_key not in ALLOWED_SEVERITIES:
        return (
            f"Invalid severity={severity!r}. Allowed: {', '.join(ALLOWED_SEVERITIES)}."
        )

    resolved_assignee = (assignee or f"{project_key}-queue").strip()
    ticket_id = f"ticket-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "id": ticket_id,
        "title": title.strip(),
        "project": project_key,
        "severity": severity_key,
        "summary": summary.strip(),
        "assignee": resolved_assignee,
        "status": "open",
    }
    TICKET_SINK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TICKET_SINK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    logger.info(
        "create_ticket id=%s project=%s severity=%s assignee=%s",
        ticket_id,
        project_key,
        severity_key,
        resolved_assignee,
    )
    return (
        "Ticket accepted by mock sink "
        f"(id={ticket_id}, project={project_key}, severity={severity_key}, "
        f"assignee={resolved_assignee!r}). Not filed in a real tracker."
    )
