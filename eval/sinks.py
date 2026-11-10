"""Helpers to capture mock-sink deltas for deterministic attack oracles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import REFUND_SINK_PATH, TRANSFER_SINK_PATH


@dataclass(frozen=True)
class SinkSnapshot:
    """Byte offsets into each JSONL sink before a case runs."""

    transfer_bytes: int
    refund_bytes: int


@dataclass
class SinkDelta:
    """New sink records written during a single attack case."""

    transfer: list[dict[str, Any]] = field(default_factory=list)
    refund: list[dict[str, Any]] = field(default_factory=list)


def _file_size(path: Path) -> int:
    if not path.exists():
        return 0
    return path.stat().st_size


def sink_snapshot(
    *,
    transfer_path: Path = TRANSFER_SINK_PATH,
    refund_path: Path = REFUND_SINK_PATH,
) -> SinkSnapshot:
    return SinkSnapshot(
        transfer_bytes=_file_size(transfer_path),
        refund_bytes=_file_size(refund_path),
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
    transfer_path: Path = TRANSFER_SINK_PATH,
    refund_path: Path = REFUND_SINK_PATH,
) -> SinkDelta:
    """Return sink rows appended after ``snapshot`` was taken."""
    return SinkDelta(
        transfer=_read_jsonl_from_offset(transfer_path, snapshot.transfer_bytes),
        refund=_read_jsonl_from_offset(refund_path, snapshot.refund_bytes),
    )
