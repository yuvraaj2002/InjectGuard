from __future__ import annotations

import logging
import re
from typing import Any

from app.config import DOCS_DIR, PROJECT_ROOT, SEARCH_TOP_K

logger = logging.getLogger(__name__)

SEARCH_POLICIES_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_policies",
        "description": (
            "Keyword search over internal banking policy markdown (refunds, disputes, "
            "KYC, transfers, payees, holds, fraud, privacy, chargebacks). "
            "Use for BankOps policy questions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords or operator question to match against policies.",
                }
            },
            "required": ["query"],
        },
    },
}


def search_policies(query: str, top_k: int = SEARCH_TOP_K) -> str:
    """Keyword-overlap search over policy markdown. Returns ranked top_k as text."""
    token_re = re.compile(r"[a-z0-9_]+", re.IGNORECASE)

    def tokens(text: str) -> set[str]:
        return {t.lower() for t in token_re.findall(text) if len(t) > 1}

    query_tokens = tokens(query)
    if not query_tokens or not DOCS_DIR.exists():
        return "No matching policy documents found."

    # Each hit: (score, relative_path, title, full_content)
    hits: list[tuple[float, str, str, str]] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        overlap = query_tokens & tokens(content)
        if not overlap:
            continue

        title = next(
            (line.lstrip("# ").strip() for line in content.splitlines() if line.startswith("#")),
            path.stem,
        )
        score = float(len(overlap))
        score += 0.5 * len(query_tokens & tokens(path.stem.replace("_", " ")))
        score += 0.5 * len(query_tokens & tokens(title))
        hits.append((score, str(path.relative_to(PROJECT_ROOT)), title, content.strip()))

    hits.sort(key=lambda h: (-h[0], h[1]))
    selected = hits[:top_k]
    logger.info(
        "search_policies query=%r matched=%s returning=%s",
        query,
        len(hits),
        [path for _, path, _, _ in selected],
    )
    if not selected:
        return "No matching policy documents found."

    blocks = [
        f"[{i}] {title} ({path}, score={score:.1f})\n{content}"
        for i, (score, path, title, content) in enumerate(selected, start=1)
    ]
    return "\n\n---\n\n".join(blocks)
