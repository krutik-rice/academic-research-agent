"""Tests for tools/summarize.py."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from tools.fetch import PaperContent
from tools.search import Paper
from tools.summarize import PaperSummary, summarize_paper


def _paper() -> Paper:
    return Paper(
        paper_id="arxiv:2301.00001",
        title="Test Paper on Machine Learning",
        authors=["Alice Smith", "Bob Jones"],
        abstract="We propose a new method for solving hard problems.",
        year=2023,
        url="https://arxiv.org/abs/2301.00001",
        pdf_url=None,
        source="arxiv",
    )


VALID_JSON = {
    "summary": "This paper proposes a new machine learning method.",
    "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
    "methodology": "Experiments on benchmark datasets.",
    "contributions": ["Novel architecture", "State-of-the-art results"],
    "limitations": ["Limited to English text", "High compute cost"],
    "keywords": ["machine learning", "deep learning", "NLP"],
}


def _mock_client(response_text: str) -> MagicMock:
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


class TestSummarizePaper:
    def test_returns_paper_summary(self):
        client = _mock_client(json.dumps(VALID_JSON))
        with patch("tools.summarize.anthropic.Anthropic", return_value=client):
            result = summarize_paper(_paper())

        assert isinstance(result, PaperSummary)
        assert result.paper_id == "arxiv:2301.00001"
        assert result.summary == VALID_JSON["summary"]

    def test_key_findings_populated(self):
        client = _mock_client(json.dumps(VALID_JSON))
        with patch("tools.summarize.anthropic.Anthropic", return_value=client):
            result = summarize_paper(_paper())
        assert len(result.key_findings) == 3

    def test_strips_markdown_fences(self):
        fenced = f"```json\n{json.dumps(VALID_JSON)}\n```"
        client = _mock_client(fenced)
        with patch("tools.summarize.anthropic.Anthropic", return_value=client):
            result = summarize_paper(_paper())
        assert result.summary == VALID_JSON["summary"]

    def test_strips_plain_code_fence(self):
        fenced = f"```\n{json.dumps(VALID_JSON)}\n```"
        client = _mock_client(fenced)
        with patch("tools.summarize.anthropic.Anthropic", return_value=client):
            result = summarize_paper(_paper())
        assert result.methodology == VALID_JSON["methodology"]

    def test_uses_abstract_when_no_content(self):
        client = _mock_client(json.dumps(VALID_JSON))
        with patch("tools.summarize.anthropic.Anthropic", return_value=client):
            summarize_paper(_paper(), content=None)

        call_kwargs = client.messages.create.call_args
        prompt_text = call_kwargs[1]["messages"][0]["content"]
        assert "We propose a new method" in prompt_text

    def test_uses_full_text_when_content_provided(self):
        content = PaperContent(
            paper_id="arxiv:2301.00001",
            title="Test Paper",
            text="Full paper body text. " * 100,
        )
        client = _mock_client(json.dumps(VALID_JSON))
        with patch("tools.summarize.anthropic.Anthropic", return_value=client):
            summarize_paper(_paper(), content=content)

        call_kwargs = client.messages.create.call_args
        prompt_text = call_kwargs[1]["messages"][0]["content"]
        assert "Full paper body text" in prompt_text

    def test_invalid_json_raises(self):
        client = _mock_client("not valid json at all")
        with patch("tools.summarize.anthropic.Anthropic", return_value=client):
            with pytest.raises(Exception):
                summarize_paper(_paper())


class TestPaperSummaryRoundtrip:
    def test_from_dict_to_dict(self):
        summary = PaperSummary(
            paper_id="arxiv:1",
            title="T",
            summary="S",
            key_findings=["F1"],
            methodology="M",
            contributions=["C1"],
            limitations=["L1"],
            keywords=["k1", "k2"],
        )
        assert PaperSummary.from_dict(summary.to_dict()) == summary
