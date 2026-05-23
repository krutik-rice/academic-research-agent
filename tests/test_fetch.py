"""Tests for tools/fetch.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.fetch import PaperContent, fetch_arxiv_html, fetch_paper, fetch_pdf


# ── PaperContent ──────────────────────────────────────────────────────────────

class TestPaperContent:
    def test_to_dict_truncates_text(self):
        content = PaperContent(
            paper_id="arxiv:1",
            title="T",
            text="x" * 10_000,
            sections={"intro": "y" * 5000},
        )
        d = content.to_dict()
        assert len(d["text"]) <= 6000
        assert len(d["sections"]["intro"]) <= 2000


# ── fetch_pdf ─────────────────────────────────────────────────────────────────

class TestFetchPdf:
    def _make_mock_pdf(self, pages_text: list[str]):
        mock_page = MagicMock()
        mock_page.extract_text.side_effect = pages_text

        mock_pdf_ctx = MagicMock()
        mock_pdf_ctx.__enter__ = MagicMock(return_value=mock_pdf_ctx)
        mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdf_ctx.pages = [mock_page] * len(pages_text)
        return mock_pdf_ctx

    def test_returns_paper_content(self):
        mock_resp = MagicMock()
        mock_resp.content = b"%PDF fake"
        mock_resp.raise_for_status = MagicMock()

        mock_pdf = self._make_mock_pdf(["Abstract\nContent of the paper."])

        with (
            patch("tools.fetch.requests.get", return_value=mock_resp),
            patch("tools.fetch.pdfplumber.open", return_value=mock_pdf),
        ):
            result = fetch_pdf("https://example.com/paper.pdf", paper_id="test:1", title="T")

        assert isinstance(result, PaperContent)
        assert result.paper_id == "test:1"
        assert result.page_count == 1

    def test_http_error_propagates(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404 Not Found")

        with patch("tools.fetch.requests.get", return_value=mock_resp):
            with pytest.raises(Exception, match="404"):
                fetch_pdf("https://example.com/missing.pdf")


# ── fetch_arxiv_html ──────────────────────────────────────────────────────────

SAMPLE_HTML = """<html><body>
<article>
  <h2>Introduction</h2>
  <p>This paper presents a new approach to machine learning.</p>
  <h2>Methods</h2>
  <p>We use a transformer architecture with self-attention.</p>
  <h2>Results</h2>
  <p>Our method outperforms all baselines on benchmarks.</p>
</article>
</body></html>"""


class TestFetchArxivHtml:
    def _mock_response(self, status: int, text: str):
        resp = MagicMock()
        resp.status_code = status
        resp.text = text
        return resp

    def test_returns_paper_content(self):
        with patch("tools.fetch.requests.get", return_value=self._mock_response(200, SAMPLE_HTML)):
            result = fetch_arxiv_html("2301.00001", paper_id="arxiv:2301.00001")

        assert isinstance(result, PaperContent)
        assert len(result.text) > 0

    def test_sections_extracted(self):
        with patch("tools.fetch.requests.get", return_value=self._mock_response(200, SAMPLE_HTML)):
            result = fetch_arxiv_html("2301.00001")

        assert len(result.sections) > 0

    def test_raises_on_non_200(self):
        with patch("tools.fetch.requests.get", return_value=self._mock_response(404, "")):
            with pytest.raises(ValueError, match="ar5iv returned 404"):
                fetch_arxiv_html("9999.99999")


# ── fetch_paper ───────────────────────────────────────────────────────────────

class TestFetchPaper:
    def test_arxiv_tries_html_first(self):
        mock_content = PaperContent(paper_id="arxiv:1", title="", text="html text")

        with patch("tools.fetch.fetch_arxiv_html", return_value=mock_content) as mock_html:
            result = fetch_paper("arxiv:2301.00001")

        mock_html.assert_called_once()
        assert result.text == "html text"

    def test_arxiv_falls_back_to_pdf(self):
        pdf_content = PaperContent(paper_id="arxiv:1", title="", text="pdf text")

        with (
            patch("tools.fetch.fetch_arxiv_html", side_effect=ValueError("html failed")),
            patch("tools.fetch.fetch_pdf", return_value=pdf_content) as mock_pdf,
        ):
            result = fetch_paper("arxiv:2301.00001", pdf_url="https://arxiv.org/pdf/2301.00001")

        mock_pdf.assert_called_once()
        assert result.text == "pdf text"

    def test_no_url_raises(self):
        with patch("tools.fetch.fetch_arxiv_html", side_effect=ValueError("no html")):
            with pytest.raises(ValueError, match="No accessible URL"):
                fetch_paper("arxiv:2301.00001")

    def test_non_arxiv_uses_pdf_directly(self):
        pdf_content = PaperContent(paper_id="s2:abc", title="", text="s2 pdf")

        with patch("tools.fetch.fetch_pdf", return_value=pdf_content) as mock_pdf:
            result = fetch_paper("s2:abc123", pdf_url="https://example.com/paper.pdf")

        mock_pdf.assert_called_once()
        assert result.text == "s2 pdf"
