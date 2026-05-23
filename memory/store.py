"""JSON-file-backed persistent storage for papers and summaries."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from tools.search import Paper


@dataclass
class PaperSummary:
    """Structured summary of a paper — populated by Claude after reading full text."""

    paper_id: str
    title: str
    summary: str
    key_findings: list[str] = field(default_factory=list)
    methodology: str = ""
    contributions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "methodology": self.methodology,
            "contributions": self.contributions,
            "limitations": self.limitations,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PaperSummary":
        return cls(
            paper_id=d["paper_id"],
            title=d["title"],
            summary=d.get("summary", ""),
            key_findings=d.get("key_findings", []),
            methodology=d.get("methodology", ""),
            contributions=d.get("contributions", []),
            limitations=d.get("limitations", []),
            keywords=d.get("keywords", []),
        )

_DEFAULT_STORAGE = os.getenv("STORAGE_PATH", "./data")


class PaperStore:
    """Stores Paper and PaperSummary objects as individual JSON files on disk."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        root = Path(storage_path or _DEFAULT_STORAGE)
        self._papers_dir = root / "papers"
        self._summaries_dir = root / "summaries"
        self._papers_dir.mkdir(parents=True, exist_ok=True)
        self._summaries_dir.mkdir(parents=True, exist_ok=True)

    # ── papers ────────────────────────────────────────────────────────────────

    def save_paper(self, paper: Paper) -> None:
        self._paper_path(paper.paper_id).write_text(
            json.dumps(paper.to_dict(), indent=2), encoding="utf-8"
        )

    def get_paper(self, paper_id: str) -> Optional[Paper]:
        path = self._paper_path(paper_id)
        if not path.exists():
            return None
        return Paper.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_papers(self) -> list[Paper]:
        papers: list[Paper] = []
        for path in self._papers_dir.glob("*.json"):
            try:
                papers.append(Paper.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                pass
        return papers

    def delete_paper(self, paper_id: str) -> bool:
        path = self._paper_path(paper_id)
        if path.exists():
            path.unlink()
            return True
        return False

    # ── summaries ─────────────────────────────────────────────────────────────

    def save_summary(self, summary: PaperSummary) -> None:
        self._summary_path(summary.paper_id).write_text(
            json.dumps(summary.to_dict(), indent=2), encoding="utf-8"
        )

    def get_summary(self, paper_id: str) -> Optional[PaperSummary]:
        path = self._summary_path(paper_id)
        if not path.exists():
            return None
        return PaperSummary.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_summaries(self) -> list[PaperSummary]:
        summaries: list[PaperSummary] = []
        for path in self._summaries_dir.glob("*.json"):
            try:
                summaries.append(
                    PaperSummary.from_dict(json.loads(path.read_text(encoding="utf-8")))
                )
            except Exception:
                pass
        return summaries

    # ── internals ─────────────────────────────────────────────────────────────

    def _safe_id(self, paper_id: str) -> str:
        return paper_id.replace(":", "_").replace("/", "_")

    def _paper_path(self, paper_id: str) -> Path:
        return self._papers_dir / f"{self._safe_id(paper_id)}.json"

    def _summary_path(self, paper_id: str) -> Path:
        return self._summaries_dir / f"{self._safe_id(paper_id)}.json"
