"""Citation formatting — APA, MLA, and BibTeX."""

from __future__ import annotations

import re

from tools.search import Paper


def format_apa(paper: Paper) -> str:
    """Return an APA-style citation string."""
    authors = _apa_authors(paper.authors)
    year = f"({paper.year})" if paper.year else "(n.d.)"
    title = paper.title

    if paper.source == "arxiv":
        arxiv_id = paper.paper_id.replace("arxiv:", "")
        return f"{authors} {year}. {title}. *arXiv*. https://arxiv.org/abs/{arxiv_id}"

    if paper.doi:
        return f"{authors} {year}. {title}. https://doi.org/{paper.doi}"

    venue = f"*{paper.venue}*. " if paper.venue else ""
    return f"{authors} {year}. {title}. {venue}{paper.url}"


def format_mla(paper: Paper) -> str:
    """Return an MLA-style citation string."""
    if not paper.authors:
        authors_str = "Unknown Author"
    elif len(paper.authors) == 1:
        authors_str = paper.authors[0]
    elif len(paper.authors) == 2:
        authors_str = f"{paper.authors[0]}, and {paper.authors[1]}"
    else:
        authors_str = f"{paper.authors[0]}, et al"

    year = str(paper.year) if paper.year else "n.d."
    venue = f"{paper.venue}, " if paper.venue else ""
    return f'{authors_str}. "{paper.title}." {venue}{year}. {paper.url}.'


def format_bibtex(paper: Paper) -> str:
    """Return a BibTeX entry."""
    key = _bibtex_key(paper)
    authors_str = " and ".join(paper.authors) if paper.authors else "Unknown"
    year = str(paper.year) if paper.year else ""
    entry_type = "article" if paper.venue else "misc"

    lines = [
        f"  author = {{{authors_str}}}",
        f"  title  = {{{paper.title}}}",
        f"  year   = {{{year}}}",
        f"  url    = {{{paper.url}}}",
    ]
    if paper.doi:
        lines.append(f"  doi    = {{{paper.doi}}}")
    if paper.venue:
        lines.append(f"  journal = {{{paper.venue}}}")

    body = ",\n".join(lines)
    return f"@{entry_type}{{{key},\n{body}\n}}"


def format_citation(paper: Paper, style: str = "apa") -> str:
    """Format a citation in the requested style ('apa', 'mla', or 'bibtex')."""
    style = style.lower()
    if style == "apa":
        return format_apa(paper)
    if style == "mla":
        return format_mla(paper)
    if style == "bibtex":
        return format_bibtex(paper)
    raise ValueError(f"Unsupported citation style '{style}'. Choose 'apa', 'mla', or 'bibtex'.")


# ── helpers ───────────────────────────────────────────────────────────────────

def _last_first(name: str) -> str:
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0]
    last = parts[-1]
    initials = " ".join(p[0] + "." for p in parts[:-1])
    return f"{last}, {initials}"


def _apa_authors(authors: list[str]) -> str:
    if not authors:
        return "Unknown Author"
    if len(authors) == 1:
        return _last_first(authors[0])
    if len(authors) <= 7:
        formatted = [_last_first(a) for a in authors]
        return ", ".join(formatted[:-1]) + ", & " + formatted[-1]
    # 8+ authors: first six, ellipsis, last author
    formatted = [_last_first(a) for a in authors[:6]]
    return ", ".join(formatted) + ", ... " + _last_first(authors[-1])


def _bibtex_key(paper: Paper) -> str:
    first_author = paper.authors[0].split()[-1].lower() if paper.authors else "unknown"
    year = str(paper.year) if paper.year else "nd"
    first_word = paper.title.split()[0].lower() if paper.title else "paper"
    clean = lambda s: re.sub(r"[^a-z0-9]", "", s)
    return f"{clean(first_author)}{year}{clean(first_word)}"
