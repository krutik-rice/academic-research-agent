"""BibTeX parser and importer for the Academic Research Agent."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from memory.index import PaperIndex
from memory.store import PaperStore
from tools.search import Paper, search_papers


@dataclass
class BibEntry:
    key: str
    entry_type: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None


@dataclass
class ImportResult:
    imported: list[Paper] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    total: int = 0


def parse_bib(content: str) -> list[BibEntry]:
    """Parse BibTeX content into BibEntry objects."""
    content = re.sub(r'(?m)^%.*$', '', content)  # strip line comments

    entries: list[BibEntry] = []
    entry_re = re.compile(r'@(\w+)\s*\{([^,\n]+),', re.IGNORECASE)
    pos = 0

    while pos < len(content):
        m = entry_re.search(content, pos)
        if not m:
            break

        entry_type = m.group(1).lower()
        key = m.group(2).strip()

        if entry_type in ('string', 'preamble', 'comment'):
            pos = m.end()
            continue

        # Find the opening brace and walk to its matching close
        brace_pos = m.start() + m.group(0).index('{')
        depth = 0
        i = brace_pos
        while i < len(content):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    break
            i += 1

        body = content[brace_pos + 1:i]
        pos = i + 1

        entry = BibEntry(key=key, entry_type=entry_type)
        entry.title = _field(body, "title")
        entry.authors = _split_authors(_field(body, "author"))

        year_str = _field(body, "year")
        entry.year = int(year_str) if year_str and year_str.isdigit() else None

        entry.doi = _field(body, "doi") or None
        entry.url = _field(body, "url") or _field(body, "link") or None
        entry.abstract = _field(body, "abstract") or None

        eprint = _field(body, "eprint")
        archiveprefix = _field(body, "archiveprefix")
        if eprint and "arxiv" in archiveprefix.lower():
            entry.arxiv_id = re.sub(r'v\d+$', '', eprint.strip())
        elif entry.url and "arxiv.org" in entry.url:
            m2 = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', entry.url)
            if m2:
                entry.arxiv_id = m2.group(1)

        if entry.title:
            entries.append(entry)

    return entries


def import_from_bib(
    content: str,
    store: PaperStore,
    index: PaperIndex,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> ImportResult:
    """Import papers from BibTeX content into the store.

    arXiv papers (with eprint + archiveprefix=arXiv) are saved directly from
    metadata. Others are matched by title search on arXiv (best-effort).
    Papers already in the store are skipped; unresolvable entries are reported.
    """
    entries = parse_bib(content)
    result = ImportResult(total=len(entries))

    existing_ids = {p.paper_id for p in store.list_papers()}
    existing_titles = {_norm(p.title) for p in store.list_papers()}

    for i, entry in enumerate(entries):
        if progress_cb:
            progress_cb(i, len(entries), entry.title or entry.key)

        label = entry.title or entry.key

        if _norm(entry.title) in existing_titles:
            result.skipped.append(label)
            continue

        paper: Optional[Paper] = None

        if entry.arxiv_id:
            pid = f"arxiv:{entry.arxiv_id}"
            if pid in existing_ids:
                result.skipped.append(label)
                continue
            paper = Paper(
                paper_id=pid,
                title=entry.title,
                authors=entry.authors,
                abstract=entry.abstract or "",
                year=entry.year,
                url=f"https://arxiv.org/abs/{entry.arxiv_id}",
                pdf_url=f"https://arxiv.org/pdf/{entry.arxiv_id}",
                source="arxiv",
                doi=entry.doi,
            )
        else:
            try:
                candidates = search_papers(entry.title, sources=["arxiv"], max_results=3)
            except Exception:
                candidates = []
            for candidate in candidates:
                if _norm(candidate.title) == _norm(entry.title):
                    paper = candidate
                    break

        if paper is not None:
            if paper.paper_id not in existing_ids and _norm(paper.title) not in existing_titles:
                store.save_paper(paper)
                index.add_paper(paper)
                existing_ids.add(paper.paper_id)
                existing_titles.add(_norm(paper.title))
                result.imported.append(paper)
            else:
                result.skipped.append(label)
        else:
            result.not_found.append(label)

    if progress_cb:
        progress_cb(len(entries), len(entries), "Done")

    return result


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_braced(content: str, pos: int) -> tuple[str, int]:
    """Return (inner_content, end_pos) for braces starting at pos."""
    depth = 0
    for i in range(pos, len(content)):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                return content[pos + 1:i], i + 1
    return content[pos + 1:], len(content)


def _field(body: str, name: str) -> str:
    """Extract a named field value from a BibTeX entry body."""
    pat = re.compile(rf'(?<![a-zA-Z]){re.escape(name)}\s*=\s*', re.IGNORECASE)
    m = pat.search(body)
    if not m:
        return ""

    pos = m.end()
    while pos < len(body) and body[pos] in ' \t\n\r':
        pos += 1
    if pos >= len(body):
        return ""

    if body[pos] == '{':
        val, _ = _extract_braced(body, pos)
    elif body[pos] == '"':
        end = body.find('"', pos + 1)
        val = body[pos + 1:end] if end != -1 else ""
    else:
        nm = re.match(r'[\d\w]+', body[pos:])
        val = nm.group() if nm else ""

    val = re.sub(r'\{([^{}]*)\}', r'\1', val)      # unwrap single-level braces
    val = re.sub(r'\\[a-zA-Z]+\s*', ' ', val)       # strip LaTeX commands
    return re.sub(r'\s+', ' ', val).strip()


def _split_authors(author_str: str) -> list[str]:
    """Split a BibTeX author field on ' and '."""
    if not author_str:
        return []
    authors: list[str] = []
    for part in re.split(r'\s+and\s+', author_str, flags=re.IGNORECASE):
        part = part.strip()
        if "," in part:
            last, first = part.split(",", 1)
            part = f"{first.strip()} {last.strip()}"
        if part:
            authors.append(part)
    return authors


def _norm(title: str) -> str:
    return re.sub(r'\s+', ' ', title.lower().strip())
