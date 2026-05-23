"""Tests for tools/search.py — arXiv and Semantic Scholar search."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.search import Paper, search_arxiv, search_papers, search_semantic_scholar

# ── fixtures ──────────────────────────────────────────────────────────────────

ARXIV_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>Test Paper: A Study of Things</title>
    <summary>This is the abstract of the paper.</summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <published>2023-01-15T00:00:00Z</published>
    <link rel="related" title="pdf" href="https://arxiv.org/pdf/2301.00001"/>
  </entry>
</feed>"""

S2_JSON = {
    "data": [
        {
            "paperId": "abc123def456",
            "title": "Semantic Scholar Paper Title",
            "authors": [{"name": "Carol Davis"}, {"name": "Dave Evans"}],
            "year": 2022,
            "abstract": "S2 abstract text.",
            "url": "https://www.semanticscholar.org/paper/abc123def456",
            "openAccessPdf": {"url": "https://example.com/paper.pdf"},
            "externalIds": {"DOI": "10.1234/test.2022"},
            "venue": "NeurIPS",
            "citationCount": 42,
        }
    ]
}


# ── arXiv ─────────────────────────────────────────────────────────────────────

class TestSearchArxiv:
    def _mock_get(self, content: bytes):
        resp = MagicMock()
        resp.content = content
        resp.raise_for_status = MagicMock()
        return resp

    def test_parses_title_and_authors(self):
        with patch("tools.search.requests.get", return_value=self._mock_get(ARXIV_XML)):
            papers = search_arxiv("test", max_results=1)

        assert len(papers) == 1
        assert papers[0].title == "Test Paper: A Study of Things"
        assert papers[0].authors == ["Alice Smith", "Bob Jones"]

    def test_parses_year(self):
        with patch("tools.search.requests.get", return_value=self._mock_get(ARXIV_XML)):
            papers = search_arxiv("test")
        assert papers[0].year == 2023

    def test_source_is_arxiv(self):
        with patch("tools.search.requests.get", return_value=self._mock_get(ARXIV_XML)):
            papers = search_arxiv("test")
        assert papers[0].source == "arxiv"
        assert papers[0].paper_id.startswith("arxiv:")

    def test_returns_paper_objects(self):
        with patch("tools.search.requests.get", return_value=self._mock_get(ARXIV_XML)):
            papers = search_arxiv("deep learning")
        assert all(isinstance(p, Paper) for p in papers)

    def test_pdf_url_present(self):
        with patch("tools.search.requests.get", return_value=self._mock_get(ARXIV_XML)):
            papers = search_arxiv("test")
        assert papers[0].pdf_url is not None
        assert "arxiv.org" in papers[0].pdf_url


# ── Semantic Scholar ──────────────────────────────────────────────────────────

class TestSearchSemanticScholar:
    def _mock_get(self, data: dict):
        resp = MagicMock()
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    def test_parses_title_and_authors(self):
        with patch("tools.search.requests.get", return_value=self._mock_get(S2_JSON)):
            papers = search_semantic_scholar("test")
        assert papers[0].title == "Semantic Scholar Paper Title"
        assert "Carol Davis" in papers[0].authors

    def test_source_is_semantic_scholar(self):
        with patch("tools.search.requests.get", return_value=self._mock_get(S2_JSON)):
            papers = search_semantic_scholar("test")
        assert papers[0].source == "semantic_scholar"
        assert papers[0].paper_id.startswith("s2:")

    def test_citation_count_and_doi(self):
        with patch("tools.search.requests.get", return_value=self._mock_get(S2_JSON)):
            papers = search_semantic_scholar("test")
        assert papers[0].citation_count == 42
        assert papers[0].doi == "10.1234/test.2022"

    def test_empty_data_returns_empty_list(self):
        with patch("tools.search.requests.get", return_value=self._mock_get({"data": []})):
            papers = search_semantic_scholar("nothing")
        assert papers == []


# ── search_papers (multi-source) ──────────────────────────────────────────────

class TestSearchPapers:
    def _make_paper(self, paper_id: str, title: str, source: str) -> Paper:
        return Paper(
            paper_id=paper_id,
            title=title,
            authors=[],
            abstract="",
            year=2023,
            url="https://example.com",
            pdf_url=None,
            source=source,
        )

    def test_deduplicates_identical_titles(self):
        paper = self._make_paper("arxiv:1", "Duplicate Paper", "arxiv")
        with (
            patch("tools.search.search_arxiv", return_value=[paper]),
            patch("tools.search.search_semantic_scholar", return_value=[paper]),
        ):
            results = search_papers("test", sources=["arxiv", "semantic_scholar"])
        assert len(results) == 1

    def test_skips_failed_source_gracefully(self):
        paper = self._make_paper("arxiv:1", "Good Paper", "arxiv")
        with (
            patch("tools.search.search_arxiv", return_value=[paper]),
            patch("tools.search.search_semantic_scholar", side_effect=Exception("API down")),
        ):
            results = search_papers("test", sources=["arxiv", "semantic_scholar"])
        assert len(results) == 1

    def test_respects_max_results(self):
        papers = [self._make_paper(f"arxiv:{i}", f"Paper {i}", "arxiv") for i in range(15)]
        with patch("tools.search.search_arxiv", return_value=papers):
            results = search_papers("test", sources=["arxiv"], max_results=5)
        assert len(results) <= 5


# ── Paper dataclass ───────────────────────────────────────────────────────────

class TestPaperDataclass:
    def test_roundtrip_dict(self):
        paper = Paper(
            paper_id="arxiv:1234.5678",
            title="My Paper",
            authors=["A. Author"],
            abstract="Abstract text.",
            year=2024,
            url="https://arxiv.org/abs/1234.5678",
            pdf_url="https://arxiv.org/pdf/1234.5678",
            source="arxiv",
            doi="10.1234/x",
            venue="ICLR",
            citation_count=7,
        )
        assert Paper.from_dict(paper.to_dict()) == paper
