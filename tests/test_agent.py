"""Integration-style tests for agent/core.py."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agent.core import ResearchAgent
from tools.search import Paper


def _paper(paper_id: str = "arxiv:2301.00001") -> Paper:
    return Paper(
        paper_id=paper_id,
        title="Test Paper",
        authors=["Author One", "Author Two"],
        abstract="Abstract about machine learning.",
        year=2023,
        url=f"https://arxiv.org/abs/{paper_id.replace('arxiv:', '')}",
        pdf_url=f"https://arxiv.org/pdf/{paper_id.replace('arxiv:', '')}",
        source="arxiv",
    )


def _end_turn_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    block = MagicMock()
    block.text = text
    block.type = "text"
    resp.content = [block]
    return resp


# ── agent loop ────────────────────────────────────────────────────────────────

class TestResearchAgentLoop:
    def _agent(self, tmp_path) -> ResearchAgent:
        return ResearchAgent(api_key="fake", model="claude-sonnet-4-6", storage_path=str(tmp_path))

    def test_returns_text_on_end_turn(self, tmp_path):
        agent = self._agent(tmp_path)
        with patch.object(agent.client.messages, "create", return_value=_end_turn_response("Answer")):
            result = agent.research("What is attention?")
        assert result == "Answer"

    def test_empty_response_returns_empty_string(self, tmp_path):
        agent = self._agent(tmp_path)
        resp = MagicMock()
        resp.stop_reason = "end_turn"
        resp.content = [MagicMock(spec=[])]  # no .text attribute
        with patch.object(agent.client.messages, "create", return_value=resp):
            result = agent.research("test")
        assert result == ""


# ── tool handlers ─────────────────────────────────────────────────────────────

class TestHandleSearchPapers:
    def test_saves_to_store_and_returns_dicts(self, tmp_path):
        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        paper = _paper()

        with patch("agent.core.search_papers", return_value=[paper]):
            results = agent._handle_search_papers(query="attention")

        assert len(results) == 1
        assert results[0]["paper_id"] == paper.paper_id
        assert agent.store.get_paper(paper.paper_id) is not None

    def test_adds_to_session_cache(self, tmp_path):
        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        paper = _paper()

        with patch("agent.core.search_papers", return_value=[paper]):
            agent._handle_search_papers(query="attention")

        assert paper.paper_id in agent._session_papers


class TestHandleFormatCitation:
    def test_returns_citation_string(self, tmp_path):
        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        paper = _paper()
        agent._session_papers[paper.paper_id] = paper

        result = agent._handle_format_citation(paper.paper_id, style="apa")
        assert "citation" in result
        assert "Test Paper" in result["citation"]

    def test_missing_paper_returns_error(self, tmp_path):
        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        result = agent._handle_format_citation("arxiv:nonexistent")
        assert "error" in result

    def test_bibtex_style(self, tmp_path):
        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        paper = _paper()
        agent._session_papers[paper.paper_id] = paper

        result = agent._handle_format_citation(paper.paper_id, style="bibtex")
        assert result["citation"].startswith("@")


class TestHandleSummarizePaper:
    def test_missing_paper_returns_error(self, tmp_path):
        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        result = agent._handle_summarize_paper("arxiv:nonexistent")
        assert "error" in result

    def test_returns_cached_summary_without_api_call(self, tmp_path):
        from tools.summarize import PaperSummary

        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        paper = _paper()
        agent._session_papers[paper.paper_id] = paper

        cached = PaperSummary(
            paper_id=paper.paper_id,
            title=paper.title,
            summary="Cached summary.",
            key_findings=["F1"],
        )
        agent.store.save_summary(cached)

        with patch("agent.core.summarize_paper") as mock_summarize:
            result = agent._handle_summarize_paper(paper.paper_id)

        mock_summarize.assert_not_called()
        assert result["summary"] == "Cached summary."


class TestHandleSearchMemory:
    def test_returns_matching_papers(self, tmp_path):
        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        paper = _paper()
        agent.store.save_paper(paper)
        agent.index.add_paper(paper)

        results = agent._handle_search_memory("machine learning")
        assert any(r["paper_id"] == paper.paper_id for r in results)

    def test_returns_empty_list_on_no_match(self, tmp_path):
        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        results = agent._handle_search_memory("xyzzy nonexistent topic")
        assert results == []


class TestDispatch:
    def test_unknown_tool_returns_error(self, tmp_path):
        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        result = agent._dispatch("unknown_tool", {})
        assert "error" in result

    def test_exception_in_handler_returns_error(self, tmp_path):
        agent = ResearchAgent(api_key="fake", storage_path=str(tmp_path))
        with patch.object(agent, "_handle_search_papers", side_effect=RuntimeError("boom")):
            result = agent._dispatch("search_papers", {"query": "test"})
        assert "error" in result
        assert "boom" in result["error"]
