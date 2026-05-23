"""Academic paper search across arXiv and Semantic Scholar."""

from __future__ import annotations

import os
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

import requests

ARXIV_BASE_URL = os.getenv("ARXIV_BASE_URL", "https://export.arxiv.org/api/")
SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
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


def search_semantic_scholar(query: str, max_results: int = 10) -> list[Paper]:
    """Search Semantic Scholar for papers."""
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    headers = {"x-api-key": api_key} if api_key else {}

    fields = "paperId,title,authors,year,abstract,url,openAccessPdf,externalIds,venue,citationCount"
    params = {"query": query, "limit": max_results, "fields": fields}

    response = requests.get(
        f"{SEMANTIC_SCHOLAR_BASE_URL}/paper/search",
        params=params,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    papers: list[Paper] = []
    for item in response.json().get("data", []):
        authors = [a.get("name", "") for a in item.get("authors", [])]

        pdf_url: Optional[str] = None
        oa = item.get("openAccessPdf")
        if oa:
            pdf_url = oa.get("url")

        doi = (item.get("externalIds") or {}).get("DOI")

        papers.append(
            Paper(
                paper_id=f"s2:{item['paperId']}",
                title=item.get("title", ""),
                authors=authors,
                abstract=item.get("abstract") or "",
                year=item.get("year"),
                url=item.get("url")
                or f"https://www.semanticscholar.org/paper/{item['paperId']}",
                pdf_url=pdf_url,
                source="semantic_scholar",
                doi=doi,
                venue=item.get("venue"),
                citation_count=item.get("citationCount"),
            )
        )

    return papers


def search_papers(
    query: str,
    sources: list[str] | None = None,
    max_results: int = 10,
) -> list[Paper]:
    """Search for papers across multiple sources, deduplicating by title."""
    if sources is None:
        sources = ["arxiv", "semantic_scholar"]

    all_papers: list[Paper] = []
    seen_titles: set[str] = set()
    per_source = max(max_results // len(sources), 5)

    for source in sources:
        try:
            if source == "arxiv":
                results = search_arxiv(query, per_source)
            elif source == "semantic_scholar":
                results = search_semantic_scholar(query, per_source)
                time.sleep(0.5)
            else:
                continue

            for paper in results:
                key = paper.title.lower().strip()
                if key not in seen_titles:
                    seen_titles.add(key)
                    all_papers.append(paper)

        except Exception as exc:
            print(f"[search] Warning: {source} failed — {exc}")

    return all_papers[:max_results]
