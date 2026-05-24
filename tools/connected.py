"""Connected-paper discovery via Semantic Scholar co-citation + recommendations.

Uses only public Semantic Scholar endpoints — no API key required.
Rate limits: ~1 req/sec for Graph API (unauthenticated).
"""

from __future__ import annotations

import re
import time
from collections import Counter
from typing import Callable, Optional

import requests

from memory.store import PaperStore
from tools.search import Paper

_S2_GRAPH = "https://api.semanticscholar.org/graph/v1"
_S2_RECS = "https://api.semanticscholar.org/recommendations/v1"
_PAPER_FIELDS = "title,year,authors,abstract,externalIds,url,openAccessPdf"

# Max seeds per strategy — keeps total wall-clock time under ~15 s
_MAX_CO_CITE_SEEDS = 10
_MAX_REC_SEEDS = 5
_PAUSE = 0.6  # seconds between requests (stay under 1 req/s limit)


def find_connected_papers(
    store: PaperStore,
    max_new: int = 10,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> tuple[list[Paper], str]:
    """Find papers connected to the library via co-citation + S2 recommendations.

    Strategy:
      1. Co-citation — fetch reference lists for up to 10 saved arXiv papers;
         papers that appear in multiple reference lists are ranked highest.
      2. S2 Recommendations — call /recommendations/v1/papers/forpaper/{id}
         for up to 5 seeds; merge unique results.

    Returns (new_papers, method_description).
    """
    saved = store.list_papers()
    if not saved:
        return [], ""

    arxiv_papers = [p for p in saved if p.paper_id.startswith("arxiv:")]
    if not arxiv_papers:
        return [], "no arXiv papers in library — Semantic Scholar requires arXiv IDs"

    existing_ids = {p.paper_id for p in saved}
    existing_titles = {_norm(p.title) for p in saved}

    # Use most-recently-saved papers as seeds (tail of list)
    co_seeds = arxiv_papers[-_MAX_CO_CITE_SEEDS:]
    rec_seeds = arxiv_papers[-_MAX_REC_SEEDS:]
    total_steps = len(co_seeds) + len(rec_seeds)

    ref_freq: Counter[str] = Counter()   # s2 paper_id → how many seeds reference it
    ref_data: dict[str, dict] = {}       # s2 paper_id → raw S2 dict
    rec_freq: Counter[str] = Counter()
    rec_data: dict[str, dict] = {}

    # ── pass 1: co-citation ───────────────────────────────────────────────────
    for step, paper in enumerate(co_seeds):
        if progress_cb:
            progress_cb(step, total_steps, f"References: {paper.title[:55]}")
        arxiv_id = paper.paper_id[len("arxiv:"):]
        for ref in _get_references(f"arXiv:{arxiv_id}"):
            s2id = ref.get("paperId", "")
            if s2id and not _in_library(ref, existing_ids, existing_titles):
                ref_freq[s2id] += 1
                ref_data[s2id] = ref
        time.sleep(_PAUSE)

    # ── pass 2: S2 per-paper recommendations ─────────────────────────────────
    for step, paper in enumerate(rec_seeds):
        if progress_cb:
            progress_cb(len(co_seeds) + step, total_steps,
                        f"Recommendations: {paper.title[:55]}")
        arxiv_id = paper.paper_id[len("arxiv:"):]
        for rec in _get_recommendations(f"arXiv:{arxiv_id}"):
            s2id = rec.get("paperId", "")
            if s2id and not _in_library(rec, existing_ids, existing_titles):
                rec_freq[s2id] += 1
                rec_data[s2id] = rec
        time.sleep(_PAUSE)

    if progress_cb:
        progress_cb(total_steps, total_steps, "Done")

    # ── merge: co-cited first (most frequent), then unique recs ──────────────
    seen: set[str] = set()
    candidates: list[Paper] = []

    for s2id, _ in ref_freq.most_common(max_new * 3):
        p = _s2_to_paper(ref_data[s2id])
        if p and p.paper_id not in existing_ids and _norm(p.title) not in existing_titles:
            if p.paper_id not in seen:
                seen.add(p.paper_id)
                candidates.append(p)

    for s2id, _ in rec_freq.most_common(max_new * 3):
        p = _s2_to_paper(rec_data[s2id])
        if p and p.paper_id not in existing_ids and _norm(p.title) not in existing_titles:
            if p.paper_id not in seen:
                seen.add(p.paper_id)
                candidates.append(p)

    method = (
        f"co-citation ({len(co_seeds)} seeds) + "
        f"S2 recommendations ({len(rec_seeds)} seeds)"
    )
    return candidates[:max_new], method


# ── Semantic Scholar API calls ────────────────────────────────────────────────

def _get_references(s2_paper_id: str) -> list[dict]:
    """Fetch the reference list for a paper (papers it cites)."""
    url = f"{_S2_GRAPH}/paper/{s2_paper_id}/references"
    try:
        resp = requests.get(
            url,
            params={"fields": _PAPER_FIELDS, "limit": 100},
            timeout=15,
        )
        resp.raise_for_status()
        return [item.get("citedPaper", {}) for item in resp.json().get("data", [])]
    except Exception:
        return []


def _get_recommendations(s2_paper_id: str) -> list[dict]:
    """Fetch Semantic Scholar recommendations for a single paper."""
    url = f"{_S2_RECS}/papers/forpaper/{s2_paper_id}"
    try:
        resp = requests.get(
            url,
            params={"fields": _PAPER_FIELDS, "limit": 20},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("recommendedPapers", [])
    except Exception:
        return []


# ── converters and helpers ────────────────────────────────────────────────────

def _s2_to_paper(raw: dict) -> Optional[Paper]:
    """Convert a Semantic Scholar paper dict to a Paper dataclass."""
    if not raw or not raw.get("title"):
        return None

    ext = raw.get("externalIds") or {}
    arxiv_id = ext.get("ArXiv")
    doi = ext.get("DOI")

    if arxiv_id:
        paper_id = f"arxiv:{arxiv_id}"
        url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        source = "arxiv"
    else:
        s2id = raw.get("paperId", "")
        paper_id = f"s2:{s2id}" if s2id else f"s2:{abs(hash(raw['title']))}"
        url = raw.get("url") or f"https://www.semanticscholar.org/paper/{s2id}"
        pdf_info = raw.get("openAccessPdf") or {}
        pdf_url = pdf_info.get("url")
        source = "semantic_scholar"

    return Paper(
        paper_id=paper_id,
        title=raw["title"] or "",
        authors=[a.get("name", "") for a in (raw.get("authors") or [])],
        abstract=raw.get("abstract") or "",
        year=raw.get("year"),
        url=url,
        pdf_url=pdf_url,
        source=source,
        doi=doi,
    )


def _in_library(raw: dict, existing_ids: set[str], existing_titles: set[str]) -> bool:
    ext = raw.get("externalIds") or {}
    arxiv_id = ext.get("ArXiv")
    if arxiv_id and f"arxiv:{arxiv_id}" in existing_ids:
        return True
    return _norm(raw.get("title") or "") in existing_titles


def _norm(title: str) -> str:
    return re.sub(r'\s+', ' ', title.lower().strip())
