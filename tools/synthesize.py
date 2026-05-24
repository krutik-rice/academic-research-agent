"""Cross-paper synthesis: find related papers and identify common research gaps."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional

from memory.store import PaperStore, PaperSummary
from tools.analyze import analyze_paper
from tools.search import Paper, search_papers


# ── stopwords ─────────────────────────────────────────────────────────────────

_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "have",
    "has", "been", "not", "all", "more", "but", "however", "thus", "therefore",
    "while", "when", "where", "such", "their", "which", "also", "can", "may",
    "our", "we", "use", "used", "uses", "show", "shown", "only", "these",
    "paper", "work", "model", "method", "approach", "results", "data", "using",
    "propose", "present", "proposed", "based", "between", "both", "other",
    "does", "each", "into", "well", "its",
}


# ── dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class GapCluster:
    theme: str
    papers: list[str]
    sentences: list[str]
    frequency: int

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "papers": self.papers,
            "sentences": self.sentences,
            "frequency": self.frequency,
        }


@dataclass
class ResearchGapsReport:
    analyzed_count: int
    skipped_count: int
    common_limitations: list[GapCluster]
    common_future_directions: list[GapCluster]

    def to_dict(self) -> dict:
        return {
            "analyzed_count": self.analyzed_count,
            "skipped_count": self.skipped_count,
            "common_limitations": [c.to_dict() for c in self.common_limitations],
            "common_future_directions": [c.to_dict() for c in self.common_future_directions],
        }


# ── analysis status ──────────────────────────────────────────────────────────

def get_analysis_status(store: PaperStore) -> list[dict]:
    """Return per-paper analysis status sorted by analyzed-first, then title."""
    papers = store.list_papers()
    statuses: list[dict] = []
    for p in papers:
        summary = store.get_summary(p.paper_id)
        lim_count = len(summary.limitations) if summary else 0
        fut_count = len(summary.future_directions) if summary else 0
        statuses.append({
            "paper_id": p.paper_id,
            "title": p.title,
            "source": p.source,
            "analyzed": lim_count > 0 or fut_count > 0,
            "lim_count": lim_count,
            "fut_count": fut_count,
        })
    return sorted(statuses, key=lambda x: (not x["analyzed"], x["title"].lower()))


# ── button 1: find related papers ─────────────────────────────────────────────

def find_related_papers(
    store: PaperStore,
    sources: Optional[list[str]] = None,
    max_new: int = 10,
) -> tuple[list[Paper], str]:
    """Derive a query from library keywords and return papers not already saved.

    Returns (new_papers, query_used).
    """
    saved = store.list_papers()
    if not saved:
        return [], ""

    text = " ".join(p.title + " " + (p.abstract or "")[:300] for p in saved)
    query = _top_keywords(text, n=6)
    if not query:
        return [], ""

    existing_ids = {p.paper_id for p in saved}
    existing_titles = {_norm(p.title) for p in saved}

    candidates = search_papers(query, sources=sources, max_results=max_new * 3)
    new_papers = [
        p for p in candidates
        if p.paper_id not in existing_ids and _norm(p.title) not in existing_titles
    ]
    return new_papers[:max_new], query


# ── button 2: find research gaps ──────────────────────────────────────────────

def find_research_gaps(
    store: PaperStore,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    overlap_fraction: float = 0.75,
) -> ResearchGapsReport:
    """Analyze every saved paper and surface common limitations + future directions.

    Uses cached `PaperSummary` where available; fetches and parses otherwise.
    `progress_cb(current, total, paper_title)` is called before each paper.
    """
    saved = store.list_papers()
    if not saved:
        return ResearchGapsReport(0, 0, [], [])

    all_lims: list[tuple[str, str]] = []   # (paper_id, sentence)
    all_futs: list[tuple[str, str]] = []
    analyzed = skipped = 0

    for i, paper in enumerate(saved):
        if progress_cb:
            progress_cb(i, len(saved), paper.title)

        cached = store.get_summary(paper.paper_id)
        if cached:
            lims, futs = cached.limitations, cached.future_directions
        else:
            result = analyze_paper(paper.paper_id, store=store)
            if result.method == "unavailable":
                skipped += 1
                continue
            lims, futs = result.limitations, result.future_directions
            summary = cached or PaperSummary(
                paper_id=paper.paper_id, title=paper.title, summary=""
            )
            summary.limitations = lims
            summary.future_directions = futs
            store.save_summary(summary)

        analyzed += 1
        all_lims.extend((paper.paper_id, s) for s in lims)
        all_futs.extend((paper.paper_id, s) for s in futs)

    if progress_cb:
        progress_cb(len(saved), len(saved), "Done")

    min_papers = max(2, round(overlap_fraction * analyzed)) if analyzed >= 2 else 2
    return ResearchGapsReport(
        analyzed_count=analyzed,
        skipped_count=skipped,
        common_limitations=_cluster(all_lims, min_papers=min_papers),
        common_future_directions=_cluster(all_futs, min_papers=min_papers),
    )


# ── clustering by shared n-gram themes ───────────────────────────────────────

def _cluster(
    items: list[tuple[str, str]],
    min_papers: int = 2,
    top_clusters: int = 12,
) -> list[GapCluster]:
    """Group sentences by shared bigram/trigram themes that span multiple papers."""
    if not items:
        return []

    # Compute per-sentence content words and ngrams
    sent_data: list[tuple[str, str, list[str]]] = []
    for paper_id, sent in items:
        sent_data.append((paper_id, sent, _ngrams(sent)))

    # Count how many distinct papers each ngram appears in
    ngram_paper_ids: dict[str, set[str]] = defaultdict(set)
    for paper_id, _sent, ngrams in sent_data:
        for ng in ngrams:
            ngram_paper_ids[ng].add(paper_id)

    # Keep only ngrams that span min_papers
    cross = {ng: pids for ng, pids in ngram_paper_ids.items() if len(pids) >= min_papers}
    if not cross:
        return []

    # Assign each sentence to its single best (most cross-paper) ngram
    clusters: dict[str, dict] = {}
    for paper_id, sent, ngrams in sent_data:
        best_ng, best_count = None, min_papers - 1
        for ng in ngrams:
            if ng in cross and len(cross[ng]) > best_count:
                best_count = len(cross[ng])
                best_ng = ng
        if best_ng:
            if best_ng not in clusters:
                clusters[best_ng] = {"entries": [], "paper_ids": set()}
            clusters[best_ng]["entries"].append((paper_id, sent))
            clusters[best_ng]["paper_ids"].add(paper_id)

    result: list[GapCluster] = []
    for theme, c in clusters.items():
        if len(c["paper_ids"]) < min_papers:
            continue
        result.append(GapCluster(
            theme=theme,
            papers=list(c["paper_ids"]),
            sentences=_dedup_sentences([s for _, s in c["entries"]])[:4],
            frequency=len(c["paper_ids"]),
        ))

    return sorted(result, key=lambda x: x.frequency, reverse=True)[:top_clusters]


# ── text helpers ──────────────────────────────────────────────────────────────

def _content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", text.lower()) if w not in _STOP]


def _ngrams(text: str) -> list[str]:
    words = _content_words(text)
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words) - 2)]
    return bigrams + trigrams


def _top_keywords(text: str, n: int = 6) -> str:
    counts = Counter(_content_words(text))
    return " ".join(w for w, _ in counts.most_common(n))


def _norm(title: str) -> str:
    return re.sub(r"\s+", " ", title.lower().strip())


def _dedup_sentences(sentences: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in sentences:
        key = s.lower()[:50]
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out
