from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import DOCS_DIR, PROJECT_ROOT, SEARCH_TOP_K

logger = logging.getLogger(__name__)
_TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)


@dataclass(frozen=True)
class DocHit:
    path: str
    title: str
    score: float
    excerpt: str


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(text) if len(token) > 1}


def _load_documents(docs_dir: Path = DOCS_DIR) -> list[tuple[Path, str]]:
    if not docs_dir.exists():
        return []
    documents: list[tuple[Path, str]] = []
    for path in sorted(docs_dir.glob("*.md")):
        documents.append((path, path.read_text(encoding="utf-8")))
    return documents


def search_docs(query: str, top_k: int = SEARCH_TOP_K) -> list[DocHit]:
    """Keyword search over synthetic markdown docs (no embeddings)."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    hits: list[DocHit] = []
    for path, content in _load_documents():
        doc_tokens = _tokenize(content)
        overlap = query_tokens & doc_tokens
        if not overlap:
            continue

        # Prefer denser overlap; lightly boost title/filename matches.
        score = float(len(overlap))
        filename_tokens = _tokenize(path.stem.replace("_", " "))
        title_line = next(
            (line.lstrip("# ").strip() for line in content.splitlines() if line.startswith("#")),
            path.stem,
        )
        title_tokens = _tokenize(title_line)
        score += 0.5 * len(query_tokens & filename_tokens)
        score += 0.5 * len(query_tokens & title_tokens)

        hits.append(
            DocHit(
                path=str(path.relative_to(PROJECT_ROOT)),
                title=title_line,
                score=score,
                excerpt=content.strip(),
            )
        )

    hits.sort(key=lambda hit: (-hit.score, hit.path))
    selected = hits[:top_k]
    logger.info(
        "search_docs query=%r matched=%s returning=%s",
        query,
        len(hits),
        [hit.path for hit in selected],
    )
    return selected


def format_hits(hits: list[DocHit]) -> str:
    if not hits:
        return "No matching documents found."

    blocks: list[str] = []
    for index, hit in enumerate(hits, start=1):
        blocks.append(
            f"[{index}] {hit.title} ({hit.path}, score={hit.score:.1f})\n{hit.excerpt}"
        )
    return "\n\n---\n\n".join(blocks)
