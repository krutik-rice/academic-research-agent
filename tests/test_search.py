"""Tests for tools/search.py — arXiv and Semantic Scholar search."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.search import Paper, search_arxiv, search_google_scholar, search_papers

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

SERPAPI_JSON = {
    "organic_results": [
        {
            "position": 1,
            "title": "Attention Is All You Need",
            "result_id": "RBlwVnwclHoJ",
            "link": "https://proceedings.neurips.cc/paper/2017/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html",
            "snippet": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
            "publication_info": {
                "summary": "A Vaswani, N Shazeer, N Parmar - Advances in neural…, 2017 - proceedings.neurips.cc",
                "authors": [
                    {"name": "Ashish Vaswani", "author_id": "v1"},
                    {"name": "Noam Shazeer", "author_id": "v2"},
                    {"name": "Niki Parmar", "author_id": "v3"},
                ],
            },
            "resources": [
                {"title": "arxiv.org", "file_format": "PDF", "link": "https://arxiv.org/pdf/1706.03762"},
            ],
            "inline_links": {
                "cited_by": {"total": 100345},
            },
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


# ── Google Scholar via SerpAPI ────────────────────────────────────────────────

class TestSearchGoogleScholar:
    def _mock_get(self, data: dict):
        resp = MagicMock()
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    def test_parses_title_and_authors(self):
        with (
            patch("tools.search.requests.get", return_value=self._mock_get(SERPAPI_JSON)),
            patch.dict("os.environ", {"SERPAPI_API_KEY": "test-key"}),
        ):
            papers = search_google_scholar("attention")
        assert papers[0].title == "Attention Is All You Need"
        assert "Ashish Vaswani" in papers[0].authors

    def test_source_is_google_scholar(self):
        with (
            patch("tools.search.requests.get", return_value=self._mock_get(SERPAPI_JSON)),
            patch.dict("os.environ", {"SERPAPI_API_KEY": "test-key"}),
        ):
            papers = search_google_scholar("attention")
        assert papers[0].source == "google_scholar"
        assert papers[0].paper_id.startswith("scholar:")

    def test_citation_count_and_pdf(self):
        with (
            patch("tools.search.requests.get", return_value=self._mock_get(SERPAPI_JSON)),
            patch.dict("os.environ", {"SERPAPI_API_KEY": "test-key"}),
        ):
            papers = search_google_scholar("attention")
        assert papers[0].citation_count == 100345
        assert papers[0].pdf_url == "https://arxiv.org/pdf/1706.03762"

    def test_raises_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="SERPAPI_API_KEY"):
                search_google_scholar("test")

    def test_empty_results_returns_empty_list(self):
        with (
            patch("tools.search.requests.get", return_value=self._mock_get({"organic_results": []})),
            patch.dict("os.environ", {"SERPAPI_API_KEY": "test-key"}),
        ):
            papers = search_google_scholar("nothing obscure")
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
            patch("tools.search.search_google_scholar", return_value=[paper]),
        ):
            results = search_papers("test", sources=["arxiv", "google_scholar"])
        assert len(results) == 1

    def test_skips_failed_source_gracefully(self):
        paper = self._make_paper("arxiv:1", "Good Paper", "arxiv")
        with (
            patch("tools.search.search_arxiv", return_value=[paper]),
            patch("tools.search.search_google_scholar", side_effect=Exception("API down")),
        ):
            results = search_papers("test", sources=["arxiv", "google_scholar"])
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
