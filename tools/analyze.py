"""Extract limitations and future directions from paper full text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from tools.fetch import PaperContent, fetch_paper
from memory.store import PaperStore


# ── section-name matchers ─────────────────────────────────────────────────────

_LIMIT_SECTION = re.compile(r"limitation|weakness|shortcoming|constraint", re.I)
_FUTURE_SECTION = re.compile(r"future\b|open problem|open question|prospect", re.I)
_FALLBACK_SECTION = re.compile(r"conclusion|discussion|summary|remark", re.I)

# ── sentence-level keyword matchers (used when no explicit section found) ─────

_LIMIT_SENT = re.compile(
    r"limitation|is limited|limited to|does not\b|cannot\b|fail to|"
    r"weakness|drawback|shortcoming|caveat|not address|not scale|"
    r"only work|only applicable|lack of|cannot handle|challenge",
    re.I,
)
_FUTURE_SENT = re.compile(
    r"future work|future direction|future research|future stud|"
    r"remains to be|open problem|open question|an avenue|promising direction|"
    r"we plan to|we leave|left for future|could be extend|could be apply|"
    r"worth investigat|directions for",
    re.I,
)


# ── result dataclass ──────────────────────────────────────────────────────────

@dataclass
class PaperAnalysis:
    paper_id: str
    title: str
    limitations: list[str] = field(default_factory=list)
    future_directions: list[str] = field(default_factory=list)
    method: str = "unavailable"

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "limitations": self.limitations,
            "future_directions": self.future_directions,
            "method": self.method,
        }


# ── public API ────────────────────────────────────────────────────────────────

def analyze_paper(paper_id: str, store: Optional[PaperStore] = None) -> PaperAnalysis:
    """Fetch a paper and extract its stated limitations and future directions."""
    title = ""
    pdf_url = None
    if store:
        meta = store.get_paper(paper_id)
        if meta:
            title = meta.title
            pdf_url = meta.pdf_url

    try:
        content = fetch_paper(paper_id, pdf_url=pdf_url, title=title)
    except Exception:
        return PaperAnalysis(paper_id=paper_id, title=title, method="unavailable")

    return _extract(content)


# ── extraction logic ──────────────────────────────────────────────────────────

def _extract(content: PaperContent) -> PaperAnalysis:
    sections = content.sections
    limitations: list[str] = []
    future_dirs: list[str] = []
    method = "unavailable"

    # Pass 1: look for explicit limitation / future-work sections by heading
    limit_secs = {k: v for k, v in sections.items() if _LIMIT_SECTION.search(k)}
    future_secs = {k: v for k, v in sections.items() if _FUTURE_SECTION.search(k)}

    if limit_secs:
        for text in limit_secs.values():
            limitations.extend(_sentences(text))
        method = "sections"

    if future_secs:
        for text in future_secs.values():
            future_dirs.extend(_sentences(text))
        method = "sections"

    # Pass 2: scan conclusion / discussion for matching sentences
    if not limitations or not future_dirs:
        fallback_secs = {k: v for k, v in sections.items() if _FALLBACK_SECTION.search(k)}
        search_text = (
            " ".join(fallback_secs.values()) if fallback_secs else content.text[:8000]
        )

        if not limitations:
            candidates = [s for s in _sentences(search_text) if _LIMIT_SENT.search(s)]
            if candidates:
                limitations = candidates[:12]
                if method == "unavailable":
                    method = "text_search"

        if not future_dirs:
            candidates = [s for s in _sentences(search_text) if _FUTURE_SENT.search(s)]
            if candidates:
                future_dirs = candidates[:12]
                if method == "unavailable":
                    method = "text_search"

    return PaperAnalysis(
        paper_id=content.paper_id,
        title=content.title,
        limitations=_dedup(limitations)[:15],
        future_directions=_dedup(future_dirs)[:15],
        method=method,
    )


# ── text helpers ──────────────────────────────────────────────────────────────

def _sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in raw if len(s.strip()) > 30]


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()[:60]
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
