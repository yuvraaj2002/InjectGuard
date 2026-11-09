"""Helpers to capture mock-sink deltas for deterministic attack oracles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import EMAIL_SINK_PATH, TICKET_SINK_PATH


@dataclass(frozen=True)
class SinkSnapshot:
    """Byte offsets (or line counts) into each JSONL sink before a case runs."""

    email_bytes: int
    ticket_bytes: int


@dataclass
class SinkDelta:
    """New sink records written during a single attack case."""

    email: list[dict[str, Any]] = field(default_factory=list)
    ticket: list[dict[str, Any]] = field(default_factory=list)


def _file_size(path: Path) -> int:
    if not path.exists():
        return 0
    return path.stat().st_size


def sink_snapshot(
    *,
    email_path: Path = EMAIL_SINK_PATH,
    ticket_path: Path = TICKET_SINK_PATH,
) -> SinkSnapshot:
    return SinkSnapshot(
        email_bytes=_file_size(email_path),
        ticket_bytes=_file_size(ticket_path),
    )


def _read_jsonl_from_offset(path: Path, offset: int) -> list[dict[str, Any]]:
    if not path.exists() or offset >= _file_size(path):
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                records.append(parsed)
    return records


def read_sink_delta(
    snapshot: SinkSnapshot,
    *,
    email_path: Path = EMAIL_SINK_PATH,
    ticket_path: Path = TICKET_SINK_PATH,
) -> SinkDelta:
    """Return sink rows appended after ``snapshot`` was taken."""
    return SinkDelta(
        email=_read_jsonl_from_offset(email_path, snapshot.email_bytes),
        ticket=_read_jsonl_from_offset(ticket_path, snapshot.ticket_bytes),
    )
