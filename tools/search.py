"""Academic paper search across arXiv and Google Scholar (via SerpAPI)."""

from __future__ import annotations

import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

import requests

ARXIV_BASE_URL = os.getenv("ARXIV_BASE_URL", "https://export.arxiv.org/api/")
SERPAPI_BASE_URL = "https://serpapi.com/search"
_ARXIV_NS = "http://www.w3.org/2005/Atom"


@dataclass
class Paper:
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    year: Optional[int]
    url: str
    pdf_url: Optional[str]
    source: str
    doi: Optional[str] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "year": self.year,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "source": self.source,
            "doi": self.doi,
            "venue": self.venue,
            "citation_count": self.citation_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Paper":
        return cls(
            paper_id=d["paper_id"],
            title=d["title"],
            authors=d.get("authors", []),
            abstract=d.get("abstract", ""),
            year=d.get("year"),
            url=d.get("url", ""),
            pdf_url=d.get("pdf_url"),
            source=d.get("source", ""),
            doi=d.get("doi"),
            venue=d.get("venue"),
            citation_count=d.get("citation_count"),
        )


# ── arXiv ─────────────────────────────────────────────────────────────────────

def search_arxiv(query: str, max_results: int = 10) -> list[Paper]:
    """Search arXiv for papers matching query."""
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = ARXIV_BASE_URL + "query?" + urllib.parse.urlencode(params)
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    papers: list[Paper] = []

    for entry in root.findall(f"{{{_ARXIV_NS}}}entry"):
        paper_id_url = entry.findtext(f"{{{_ARXIV_NS}}}id", "")
        arxiv_id = (
            paper_id_url.split("/abs/")[-1].split("v")[0]
            if "/abs/" in paper_id_url
            else paper_id_url
        )

        title_elem = entry.find(f"{{{_ARXIV_NS}}}title")
        title = title_elem.text.strip().replace("\n", " ") if title_elem is not None else ""

        abstract_elem = entry.find(f"{{{_ARXIV_NS}}}summary")
        abstract = abstract_elem.text.strip().replace("\n", " ") if abstract_elem is not None else ""

        authors = [
            author.findtext(f"{{{_ARXIV_NS}}}name", "")
            for author in entry.findall(f"{{{_ARXIV_NS}}}author")
        ]

        published = entry.findtext(f"{{{_ARXIV_NS}}}published", "")
        year = int(published[:4]) if published else None

        pdf_url: Optional[str] = None
        for link in entry.findall(f"{{{_ARXIV_NS}}}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "").replace("http://", "https://")
                break

        papers.append(
            Paper(
                paper_id=f"arxiv:{arxiv_id}",
                title=title,
                authors=authors,
                abstract=abstract,
                year=year,
                url=f"https://arxiv.org/abs/{arxiv_id}",
                pdf_url=pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
                source="arxiv",
            )
        )

    return papers


# ── Google Scholar via SerpAPI ────────────────────────────────────────────────

def search_google_scholar(query: str, max_results: int = 10) -> list[Paper]:
    """Search Google Scholar via SerpAPI (requires SERPAPI_API_KEY env var)."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError(
            "SERPAPI_API_KEY is not set. Get a free key at https://serpapi.com"
        )

    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": api_key,
        "num": min(max_results, 20),
    }

    response = requests.get(SERPAPI_BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    papers: list[Paper] = []
    for item in response.json().get("organic_results", []):
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        result_id = item.get("result_id", "")

        pub_info = item.get("publication_info", {})
        summary = pub_info.get("summary", "")

        # Prefer structured author list; fall back to parsing the summary string
        structured = pub_info.get("authors", [])
        if structured:
            authors = [a.get("name", "") for a in structured]
            year, venue = _year_venue_from_summary(summary)
        else:
            authors, year, venue = _parse_publication_summary(summary)

        # Citation count
        cited_by = item.get("inline_links", {}).get("cited_by", {})
        citation_count = cited_by.get("total")

        # PDF link from resources list
        pdf_url: Optional[str] = None
        for resource in item.get("resources", []):
            if resource.get("file_format", "").upper() == "PDF":
                pdf_url = resource.get("link")
                break

        paper_id = f"scholar:{result_id}" if result_id else f"scholar:{abs(hash(title))}"

        papers.append(
            Paper(
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract=snippet,
                year=year,
                url=link,
                pdf_url=pdf_url,
                source="google_scholar",
                venue=venue,
                citation_count=citation_count,
            )
        )

    return papers[:max_results]


# ── multi-source search ───────────────────────────────────────────────────────

def search_papers(
    query: str,
    sources: list[str] | None = None,
    max_results: int = 10,
) -> list[Paper]:
    """Search for papers across multiple sources, deduplicating by title.

    Sources: 'arxiv' (default, free), 'google_scholar' (requires SERPAPI_API_KEY).
    Results are round-robin interleaved so every source gets fair representation.
    """
    if sources is None:
        sources = ["arxiv", "google_scholar"]

    per_source = max(max_results, 5)
    buckets = [_fetch_source(source, query, per_source) for source in sources]
    return _interleave(buckets, max_results)


def _fetch_source(source: str, query: str, max_results: int) -> list[Paper]:
    """Fetch papers from a single source, returning [] on failure."""
    try:
        if source == "arxiv":
            return search_arxiv(query, max_results)
        if source == "google_scholar":
            return search_google_scholar(query, max_results)
        print(f"[search] Unknown source '{source}' — skipping.")
    except Exception as exc:
        print(f"[search] Warning: {source} failed — {exc}")
    return []


def _interleave(buckets: list[list[Paper]], max_results: int) -> list[Paper]:
    """Round-robin merge buckets, deduplicating by lowercased title."""
    result: list[Paper] = []
    seen: set[str] = set()

    for i in range(max((len(b) for b in buckets), default=0)):
        for bucket in buckets:
            if i >= len(bucket):
                continue
            key = bucket[i].title.lower().strip()
            if key not in seen:
                seen.add(key)
                result.append(bucket[i])
                if len(result) >= max_results:
                    return result

    return result


# ── helpers ───────────────────────────────────────────────────────────────────

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _parse_publication_summary(summary: str) -> tuple[list[str], Optional[int], Optional[str]]:
    """Parse SerpAPI summary string e.g. 'A Vaswani, N Shazeer - NeurIPS, 2017 - nips.cc'."""
    if not summary:
        return [], None, None

    parts = [p.strip() for p in summary.split(" - ")]
    authors: list[str] = []
    year: Optional[int] = None
    venue: Optional[str] = None

    if parts:
        # First segment: comma-separated author abbreviations
        raw_authors = parts[0].replace("…", "").strip()
        authors = [a.strip() for a in raw_authors.split(",") if a.strip()]

    for part in parts[1:]:
        m = _YEAR_RE.search(part)
        if m and year is None:
            year = int(m.group())
        # Venue is any segment without a dot-domain pattern and not a bare year
        if not re.search(r"\.\w{2,4}$", part) and not _YEAR_RE.fullmatch(part.strip()):
            if venue is None:
                # Strip the year from the venue segment if they share a segment
                venue = _YEAR_RE.sub("", part).strip().rstrip(",").strip() or None

    return authors, year, venue


def _year_venue_from_summary(summary: str) -> tuple[Optional[int], Optional[str]]:
    """Extract just year and venue when authors are already known."""
    _, year, venue = _parse_publication_summary(summary)
    return year, venue
