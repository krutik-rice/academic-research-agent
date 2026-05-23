"""Tests for memory/store.py and memory/index.py."""

from __future__ import annotations

import pytest

from memory.index import PaperIndex
from memory.store import PaperStore, PaperSummary
from tools.search import Paper


def _paper(paper_id: str = "arxiv:0001.0001", title: str = "Sample Paper") -> Paper:
    return Paper(
        paper_id=paper_id,
        title=title,
        authors=["Alice", "Bob"],
        abstract="A paper about transformers and attention mechanisms.",
        year=2023,
        url=f"https://arxiv.org/abs/{paper_id}",
        pdf_url=None,
        source="arxiv",
    )


def _summary(paper_id: str = "arxiv:0001.0001") -> PaperSummary:
    return PaperSummary(
        paper_id=paper_id,
        title="Sample Paper",
        summary="A concise overview.",
        key_findings=["Finding A"],
        methodology="Experiments",
        contributions=["Contribution X"],
        limitations=["Small dataset"],
        keywords=["transformer", "attention"],
    )


# ── PaperStore ────────────────────────────────────────────────────────────────

class TestPaperStore:
    def test_save_and_get_paper(self, tmp_path):
        store = PaperStore(str(tmp_path))
        paper = _paper()
        store.save_paper(paper)
        loaded = store.get_paper(paper.paper_id)
        assert loaded == paper

    def test_get_missing_paper_returns_none(self, tmp_path):
        store = PaperStore(str(tmp_path))
        assert store.get_paper("arxiv:nonexistent") is None

    def test_list_papers(self, tmp_path):
        store = PaperStore(str(tmp_path))
        p1 = _paper("arxiv:0001.0001", "Paper One")
        p2 = _paper("arxiv:0001.0002", "Paper Two")
        store.save_paper(p1)
        store.save_paper(p2)
        listed = store.list_papers()
        ids = {p.paper_id for p in listed}
        assert "arxiv:0001.0001" in ids
        assert "arxiv:0001.0002" in ids

    def test_delete_paper(self, tmp_path):
        store = PaperStore(str(tmp_path))
        paper = _paper()
        store.save_paper(paper)
        assert store.delete_paper(paper.paper_id) is True
        assert store.get_paper(paper.paper_id) is None

    def test_delete_missing_returns_false(self, tmp_path):
        store = PaperStore(str(tmp_path))
        assert store.delete_paper("arxiv:missing") is False

    def test_save_and_get_summary(self, tmp_path):
        store = PaperStore(str(tmp_path))
        s = _summary()
        store.save_summary(s)
        loaded = store.get_summary(s.paper_id)
        assert loaded == s

    def test_get_missing_summary_returns_none(self, tmp_path):
        store = PaperStore(str(tmp_path))
        assert store.get_summary("arxiv:no-summary") is None

    def test_paper_id_with_colon_stored_safely(self, tmp_path):
        store = PaperStore(str(tmp_path))
        paper = _paper("s2:abc/def:ghi")
        store.save_paper(paper)
        assert store.get_paper("s2:abc/def:ghi") is not None


# ── PaperIndex ────────────────────────────────────────────────────────────────

class TestPaperIndex:
    def test_search_finds_matching_paper(self, tmp_path):
        store = PaperStore(str(tmp_path))
        paper = _paper()
        store.save_paper(paper)
        index = PaperIndex(store)
        results = index.search("transformers attention")
        assert any(r.paper_id == paper.paper_id for r in results)

    def test_add_paper_then_search(self, tmp_path):
        store = PaperStore(str(tmp_path))
        index = PaperIndex(store)
        paper = _paper()
        index.add_paper(paper)
        results = index.search("attention mechanisms")
        assert len(results) > 0

    def test_no_results_for_unknown_query(self, tmp_path):
        store = PaperStore(str(tmp_path))
        index = PaperIndex(store)
        index.add_paper(_paper())
        results = index.search("xyzzy frobnicator")
        assert results == []

    def test_top_k_limits_results(self, tmp_path):
        store = PaperStore(str(tmp_path))
        index = PaperIndex(store)
        for i in range(10):
            p = _paper(f"arxiv:000{i}.0000", f"Attention Paper {i}")
            store.save_paper(p)
            index.add_paper(p)
        results = index.search("attention", top_k=3)
        assert len(results) <= 3

    def test_rebuild_loads_all_papers(self, tmp_path):
        store = PaperStore(str(tmp_path))
        for i in range(5):
            store.save_paper(_paper(f"arxiv:000{i}.rebuild", f"Rebuild Paper {i}"))
        index = PaperIndex(store)
        index.rebuild()
        results = index.search("rebuild paper")
        assert len(results) > 0
