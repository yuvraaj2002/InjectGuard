from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.config import DEFAULT_USER_ID, DOCS_DIR, POLICY_ACCESS_PATH, PROJECT_ROOT, SEARCH_TOP_K

logger = logging.getLogger(__name__)

SEARCH_POLICIES_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_policies",
        "description": (
            "Keyword search over banking policy markdown the current operator is allowed to read "
            "(refunds, disputes, KYC, transfers, payees, holds, fraud, privacy, chargebacks)."
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


def search_policies(query: str, user_id: str = DEFAULT_USER_ID, top_k: int = SEARCH_TOP_K) -> str:
    """Keyword-overlap search over policies allowed for user_id. Returns ranked top_k text."""
    token_re = re.compile(r"[a-z0-9_]+", re.IGNORECASE)

    def tokens(text: str) -> set[str]:
        return {t.lower() for t in token_re.findall(text) if len(t) > 1}

    query_tokens = tokens(query)
    if not query_tokens or not DOCS_DIR.exists():
        return "No matching policy documents found."

    allowed: set[str] = set()
    if POLICY_ACCESS_PATH.exists():
        access = json.loads(POLICY_ACCESS_PATH.read_text(encoding="utf-8"))
        allowed = {str(pid) for pid in access.get(user_id, [])}
    if not allowed:
        logger.info("search_policies user_id=%s has no policy access", user_id)
        return f"No policies are accessible for user_id={user_id!r}."

    hits: list[tuple[float, str, str, str, str]] = []  # score, policy_id, path, title, content
    for path in sorted(DOCS_DIR.glob("*.md")):
        policy_id = path.stem
        if policy_id not in allowed:
            continue

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
        hits.append((score, policy_id, str(path.relative_to(PROJECT_ROOT)), title, content.strip()))

    hits.sort(key=lambda h: (-h[0], h[1]))
    selected = hits[:top_k]
    logger.info(
        "search_policies user_id=%s query=%r matched=%s returning=%s",
        user_id,
        query,
        len(hits),
        [policy_id for _, policy_id, _, _, _ in selected],
    )
    if not selected:
        return "No matching policy documents found."

    blocks = [
        f"[{i}] {title} (id={policy_id}, {path}, score={score:.1f})\n{content}"
        for i, (score, policy_id, path, title, content) in enumerate(selected, start=1)
    ]
    return "\n\n---\n\n".join(blocks)
