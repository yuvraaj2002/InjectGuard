# Ticket Triage Guide

OpsPilot and human agents use the same triage rules for support tickets.

## Severity
- **P1**: Production outage or data exposure. Page on-call immediately.
- **P2**: Major feature broken for many users. Respond within 1 hour.
- **P3**: Single-user issue or workaround exists. Respond within 1 business day.
- **P4**: Question or enhancement request.

## Creating tickets
Use `create_ticket` only when the requester needs tracking beyond chat.
Required fields: title, project (`ops`, `it`, `security`), severity, summary.

## Assignment
Default assignee is the queue owner for the project. Do not assign outside the
approved project roster unless a human approves the change.
