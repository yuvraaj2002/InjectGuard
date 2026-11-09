from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import EMAILS_PATH, EMAIL_SINK_PATH

logger = logging.getLogger(__name__)

READ_EMAIL_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_email",
        "description": (
            "Read synthetic internal emails. "
            "To list all emails, call with NO arguments (do not pass query). "
            "Pass email_id to fetch one message. "
            "Pass query only for keyword search over subject/body (e.g. 'vpn', 'password')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "email_id": {
                    "type": "string",
                    "description": "Exact email id, e.g. email-001.",
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Keyword filter for subject/body content. "
                        "Omit this field entirely to list all emails."
                    ),
                },
            },
            "required": [],
        },
    },
}

SEND_EMAIL_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "send_email",
        "description": (
            "Send an email via the local mock sink (never real SMTP). "
            "Use only when the user asks to email someone."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address.",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line.",
                },
                "body": {
                    "type": "string",
                    "description": "Email body text.",
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
}

EMAIL_TOOL_SCHEMAS: list[dict[str, Any]] = [READ_EMAIL_TOOL, SEND_EMAIL_TOOL]


def _load_emails(path: Path = EMAILS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        logger.warning("Emails file missing: %s", path)
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _format_email(email: dict[str, Any]) -> str:
    return (
        f"id: {email.get('id')}\n"
        f"from: {email.get('from')}\n"
        f"to: {email.get('to')}\n"
        f"subject: {email.get('subject')}\n"
        f"body:\n{email.get('body', '')}"
    )


def read_email(
    email_id: str | None = None,
    query: str | None = None,
) -> str:
    """Read synthetic emails. Untrusted content is returned raw (vulnerable baseline)."""
    emails = _load_emails()
    if not emails:
        return "No emails available."

    if email_id:
        for email in emails:
            if email.get("id") == email_id:
                logger.info("read_email id=%s", email_id)
                return _format_email(email)
        logger.info("read_email id=%s not found", email_id)
        return f"Email not found: {email_id}"

    if query:
        tokens = {token.lower() for token in query.split() if token.strip()}
        matches: list[dict[str, Any]] = []
        for email in emails:
            haystack = " ".join(
                [
                    str(email.get("id", "")),
                    str(email.get("from", "")),
                    str(email.get("subject", "")),
                    str(email.get("body", "")),
                ]
            ).lower()
            if tokens and all(token in haystack for token in tokens):
                matches.append(email)
            elif not tokens:
                matches.append(email)
        logger.info("read_email query=%r matches=%s", query, len(matches))
        if not matches:
            return f"No emails matched query={query!r}."
        return "\n\n---\n\n".join(_format_email(email) for email in matches)

    logger.info("read_email list_all count=%s", len(emails))
    summaries = [
        f"{email.get('id')}: {email.get('subject')} (from {email.get('from')})"
        for email in emails
    ]
    return "Recent emails:\n" + "\n".join(summaries)


def send_email(to: str, subject: str, body: str) -> str:
    """Mock send: append to a local JSONL sink. No real mail is delivered."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "to": to,
        "subject": subject,
        "body": body,
    }
    EMAIL_SINK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EMAIL_SINK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    logger.info("send_email to=%s subject=%r sink=%s", to, subject, EMAIL_SINK_PATH)
    return (
        "Email accepted by mock sink "
        f"(to={to!r}, subject={subject!r}). Not delivered to a real mailbox."
    )
