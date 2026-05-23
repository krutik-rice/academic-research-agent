"""Inverted-index for keyword search over the local paper store.

Uses token-overlap scoring (no heavy ML dependencies) so the agent can quickly
find previously retrieved papers without hitting external APIs again.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING

from tools.search import Paper

if TYPE_CHECKING:
    from memory.store import PaperStore


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class PaperIndex:
    """Lightweight inverted index over a PaperStore."""

    def __init__(self, store: "PaperStore") -> None:
        self._store = store
        self._index: dict[str, set[str]] = defaultdict(set)  # token -> {paper_id}
        self._cache: dict[str, Paper] = {}
        self._loaded = False

    # ── public API ────────────────────────────────────────────────────────────

    def add_paper(self, paper: Paper) -> None:
        """Index a single paper (call after saving it to the store)."""
        self._ensure_loaded()
        self._index_paper(paper)

    def search(self, query: str, top_k: int = 5) -> list[Paper]:
        """Return up to top_k papers ranked by token overlap with query."""
        self._ensure_loaded()

        query_tokens = _tokenize(query)
        scores: dict[str, int] = defaultdict(int)

        for token in query_tokens:
            for pid in self._index.get(token, set()):
                scores[pid] += 1

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results: list[Paper] = []
        for pid, _ in ranked[:top_k]:
            paper = self._cache.get(pid) or self._store.get_paper(pid)
            if paper:
                results.append(paper)

        return results

    def rebuild(self) -> None:
        """Reload all papers from disk and rebuild the index."""
        self._index.clear()
        self._cache.clear()
        for paper in self._store.list_papers():
            self._index_paper(paper)
        self._loaded = True

    # ── internals ─────────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.rebuild()

    def _index_paper(self, paper: Paper) -> None:
        tokens = _tokenize(paper.title) | _tokenize(paper.abstract)
        for token in tokens:
            self._index[token].add(paper.paper_id)
        self._cache[paper.paper_id] = paper
