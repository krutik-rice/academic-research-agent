"""Paper retrieval and full-text extraction (PDF and HTML)."""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import pdfplumber
import requests
from bs4 import BeautifulSoup

# pdfminer emits noisy warnings for non-critical PDF quirks; silence them
logging.getLogger("pdfminer").setLevel(logging.ERROR)

_HEADERS = {"User-Agent": "AcademicResearchAgent/1.0 (open-source research tool)"}

_SECTION_RE = re.compile(
    r"^(abstract|introduction|related work|background|methodology|methods?|"
    r"experiments?|results?|evaluation|discussion|conclusion|references?|acknowledgements?)",
    re.IGNORECASE,
)


@dataclass
class PaperContent:
    paper_id: str
    title: str
    text: str
    sections: dict[str, str] = field(default_factory=dict)
    page_count: int = 0

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            # Truncate to keep API payloads reasonable
            "text": self.text[:6000],
            "sections": {k: v[:2000] for k, v in self.sections.items()},
            "page_count": self.page_count,
        }


def fetch_pdf(url: str, paper_id: str = "", title: str = "") -> PaperContent:
    """Download a PDF and extract its text."""
    response = requests.get(url, headers=_HEADERS, timeout=60)
    response.raise_for_status()

    pdf_bytes = io.BytesIO(response.content)
    pages_text: list[str] = []

    with pdfplumber.open(pdf_bytes) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)

    full_text = "\n".join(pages_text)
    return PaperContent(
        paper_id=paper_id,
        title=title,
        text=full_text,
        sections=_extract_sections(full_text),
        page_count=page_count,
    )


def fetch_arxiv_html(arxiv_id: str, paper_id: str = "", title: str = "") -> PaperContent:
    """Fetch an arXiv paper via its ar5iv HTML version (better than raw PDF parsing)."""
    clean_id = arxiv_id.replace("arxiv:", "")
    url = f"https://ar5iv.labs.arxiv.org/html/{clean_id}"

    response = requests.get(url, headers=_HEADERS, timeout=30)
    if response.status_code != 200:
        raise ValueError(f"ar5iv returned {response.status_code} for {url}")

    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
        tag.decompose()

    root = soup.find("article") or soup.find("div", class_="ltx_document") or soup

    sections: dict[str, str] = {}
    current = "main"
    buf: list[str] = []

    for elem in root.find_all(["h1", "h2", "h3", "p", "li"]):
        if elem.name in ("h1", "h2", "h3"):
            if buf:
                sections[current] = " ".join(buf)
            current = elem.get_text(strip=True).lower()
            buf = []
        else:
            t = elem.get_text(strip=True)
            if t:
                buf.append(t)

    if buf:
        sections[current] = " ".join(buf)

    return PaperContent(
        paper_id=paper_id,
        title=title,
        text=root.get_text(separator="\n", strip=True),
        sections=sections,
    )


def fetch_paper(
    paper_id: str,
    pdf_url: Optional[str] = None,
    title: str = "",
) -> PaperContent:
    """Fetch paper content, preferring HTML for arXiv then falling back to PDF."""
    if paper_id.startswith("arxiv:"):
        try:
            return fetch_arxiv_html(paper_id, paper_id=paper_id, title=title)
        except Exception:
            pass

    if pdf_url:
        return fetch_pdf(pdf_url, paper_id=paper_id, title=title)

    raise ValueError(f"No accessible URL for paper {paper_id}.")


# ── internal helpers ──────────────────────────────────────────────────────────

def _extract_sections(text: str) -> dict[str, str]:
    """Split plain text into named sections by recognising common headings."""
    sections: dict[str, str] = {}
    current = "preamble"
    buf: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped and _SECTION_RE.match(stripped) and len(stripped) < 80:
            if buf:
                sections[current] = " ".join(buf)
            current = stripped.lower()
            buf = []
        elif stripped:
            buf.append(stripped)

    if buf:
        sections[current] = " ".join(buf)

    return sections
