"""Tests for tools/citations.py."""

from __future__ import annotations

import pytest

from tools.citations import format_apa, format_bibtex, format_citation, format_mla
from tools.search import Paper


def _paper(**kwargs) -> Paper:
    defaults = dict(
        paper_id="arxiv:1706.03762",
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
        abstract="",
        year=2017,
        url="https://arxiv.org/abs/1706.03762",
        pdf_url=None,
        source="arxiv",
        doi=None,
        venue=None,
        citation_count=None,
    )
    defaults.update(kwargs)
    return Paper(**defaults)


# ── APA ───────────────────────────────────────────────────────────────────────

class TestFormatAPA:
    def test_contains_title(self):
        assert "Attention Is All You Need" in format_apa(_paper())

    def test_contains_year(self):
        assert "2017" in format_apa(_paper())

    def test_no_year_uses_nd(self):
        assert "n.d." in format_apa(_paper(year=None))

    def test_arxiv_url_in_citation(self):
        result = format_apa(_paper())
        assert "arxiv.org" in result

    def test_doi_used_when_present(self):
        result = format_apa(_paper(source="semantic_scholar", doi="10.1234/x"))
        assert "doi.org/10.1234/x" in result

    def test_single_author(self):
        result = format_apa(_paper(authors=["Alice Smith"]))
        assert "Smith" in result

    def test_many_authors_uses_ellipsis(self):
        authors = [f"Author {i}" for i in range(10)]
        result = format_apa(_paper(authors=authors))
        assert "..." in result


# ── MLA ───────────────────────────────────────────────────────────────────────

class TestFormatMLA:
    def test_contains_title_in_quotes(self):
        result = format_mla(_paper())
        assert '"Attention Is All You Need"' in result

    def test_contains_year(self):
        assert "2017" in format_mla(_paper())

    def test_two_authors_uses_and(self):
        result = format_mla(_paper(authors=["Alice Smith", "Bob Jones"]))
        assert "and" in result

    def test_three_plus_authors_uses_et_al(self):
        result = format_mla(_paper())
        assert "et al" in result

    def test_no_authors_fallback(self):
        result = format_mla(_paper(authors=[]))
        assert "Unknown Author" in result


# ── BibTeX ────────────────────────────────────────────────────────────────────

class TestFormatBibTeX:
    def test_starts_with_at(self):
        assert format_bibtex(_paper()).startswith("@")

    def test_required_fields_present(self):
        result = format_bibtex(_paper())
        assert "author" in result
        assert "title" in result
        assert "year" in result
        assert "url" in result

    def test_doi_included_when_set(self):
        result = format_bibtex(_paper(doi="10.99/test"))
        assert "doi" in result

    def test_venue_maps_to_journal(self):
        result = format_bibtex(_paper(venue="NeurIPS", source="semantic_scholar"))
        assert "journal" in result

    def test_key_is_alphanumeric(self):
        import re
        result = format_bibtex(_paper())
        key = re.search(r"@\w+\{(\w+),", result)
        assert key is not None


# ── format_citation dispatcher ────────────────────────────────────────────────

class TestFormatCitation:
    def test_apa_dispatch(self):
        result = format_citation(_paper(), style="apa")
        assert "Attention" in result

    def test_mla_dispatch(self):
        result = format_citation(_paper(), style="mla")
        assert '"Attention' in result

    def test_bibtex_dispatch(self):
        result = format_citation(_paper(), style="bibtex")
        assert result.startswith("@")

    def test_invalid_style_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported"):
            format_citation(_paper(), style="chicago")

    def test_case_insensitive_style(self):
        result = format_citation(_paper(), style="APA")
        assert "Attention" in result
