"""Main research agent — agentic loop with Claude tool use."""

from __future__ import annotations

import json
from typing import Any, Optional

import anthropic

from agent.prompts.system import SYSTEM_PROMPT
from agent.tools import TOOL_DEFINITIONS
from memory.store import PaperStore
from memory.index import PaperIndex
from tools.search import Paper, search_papers
from tools.fetch import fetch_paper
from tools.summarize import summarize_paper
from tools.citations import format_citation


class ResearchAgent:
    """Agentic research assistant powered by Claude with tool use."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-6",
        storage_path: Optional[str] = None,
    ) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.store = PaperStore(storage_path=storage_path)
        self.index = PaperIndex(self.store)
        # In-memory paper cache for the current session
        self._session_papers: dict[str, Paper] = {}

    # ── public API ────────────────────────────────────────────────────────────

    def research(self, query: str) -> str:
        """Run a research query through the full agentic loop and return the answer."""
        messages: list[dict] = [{"role": "user", "content": query}]

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                return _extract_text(response)

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._dispatch(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result, default=str),
                            }
                        )
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason — return whatever text is there
                return _extract_text(response)

    # ── tool dispatch ─────────────────────────────────────────────────────────

    def _dispatch(self, tool_name: str, tool_input: dict) -> Any:
        try:
            handlers = {
                "search_papers": self._handle_search_papers,
                "fetch_paper": self._handle_fetch_paper,
                "summarize_paper": self._handle_summarize_paper,
                "format_citation": self._handle_format_citation,
                "search_memory": self._handle_search_memory,
            }
            handler = handlers.get(tool_name)
            if handler is None:
                return {"error": f"Unknown tool: {tool_name}"}
            return handler(**tool_input)
        except Exception as exc:
            return {"error": str(exc)}

    def _handle_search_papers(
        self,
        query: str,
        sources: Optional[list[str]] = None,
        max_results: int = 10,
    ) -> list[dict]:
        papers = search_papers(query, sources=sources, max_results=max_results)
        for paper in papers:
            self.store.save_paper(paper)
            self.index.add_paper(paper)
            self._session_papers[paper.paper_id] = paper
        return [p.to_dict() for p in papers]

    def _handle_fetch_paper(
        self,
        paper_id: str,
        pdf_url: Optional[str] = None,
        title: str = "",
    ) -> dict:
        content = fetch_paper(paper_id, pdf_url=pdf_url, title=title)
        return content.to_dict()

    def _handle_summarize_paper(self, paper_id: str) -> dict:
        paper = self._session_papers.get(paper_id) or self.store.get_paper(paper_id)
        if paper is None:
            return {"error": f"Paper '{paper_id}' not found. Search for it first."}

        # Return cached summary if available
        cached = self.store.get_summary(paper_id)
        if cached:
            return cached.to_dict()

        summary = summarize_paper(paper, model=self.model)
        self.store.save_summary(summary)
        return summary.to_dict()

    def _handle_format_citation(self, paper_id: str, style: str = "apa") -> dict:
        paper = self._session_papers.get(paper_id) or self.store.get_paper(paper_id)
        if paper is None:
            return {"error": f"Paper '{paper_id}' not found. Search for it first."}
        return {
            "paper_id": paper_id,
            "style": style,
            "citation": format_citation(paper, style=style),
        }

    def _handle_search_memory(self, query: str, top_k: int = 5) -> list[dict]:
        results = self.index.search(query, top_k=top_k)
        return [p.to_dict() for p in results]


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_text(response: anthropic.types.Message) -> str:
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""
