"""Structured paper summarization via the Claude API."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

import anthropic

from tools.search import Paper
from tools.fetch import PaperContent

_PROMPT = """\
You are an expert academic researcher. Analyse the paper below and return a structured JSON \
summary with exactly these fields:
- "summary": a concise 3–5 sentence overview of the paper
- "key_findings": list of 3–7 key results or takeaways
- "methodology": one-paragraph description of the methods used
- "contributions": list of the main contributions to the field
- "limitations": list of limitations or future work mentioned by the authors
- "keywords": list of 5–10 relevant topic keywords

Return only valid JSON — no markdown fences, no prose outside the JSON object.

Paper title: {title}
Paper ID: {paper_id}

Content:
{content}
"""

_FENCE_RE = re.compile(r"```(?:json)?\s*|\s*```", re.IGNORECASE)


@dataclass
class PaperSummary:
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


def summarize_paper(
    paper: Paper,
    content: Optional[PaperContent] = None,
    model: str = "claude-sonnet-4-6",
) -> PaperSummary:
    """Generate a structured summary of a paper using Claude."""
    client = anthropic.Anthropic()

    # Use full text if available, otherwise fall back to the abstract
    text = content.text[:8000] if content is not None else paper.abstract

    prompt = _PROMPT.format(
        title=paper.title,
        paper_id=paper.paper_id,
        content=text,
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    raw = _FENCE_RE.sub("", raw).strip()

    data = json.loads(raw)

    return PaperSummary(
        paper_id=paper.paper_id,
        title=paper.title,
        summary=data.get("summary", ""),
        key_findings=data.get("key_findings", []),
        methodology=data.get("methodology", ""),
        contributions=data.get("contributions", []),
        limitations=data.get("limitations", []),
        keywords=data.get("keywords", []),
    )
