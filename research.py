#!/usr/bin/env python3
"""
Academic Research Toolkit — unified CLI for Claude Code.

Commands
--------
search    Search arXiv and/or Semantic Scholar for papers
fetch     Download and extract full text of a paper
cite      Format a paper citation (APA / MLA / BibTeX)
memory    Manage locally saved papers (list / show / search / delete)

All commands output JSON so Claude Code can read and reason over results.

Examples
--------
python research.py search "retrieval augmented generation" --max 8
python research.py search "diffusion models" --sources arxiv --max 5
python research.py fetch arxiv:2005.11401
python research.py fetch arxiv:2005.11401 --pdf-url https://arxiv.org/pdf/2005.11401
python research.py cite arxiv:2005.11401 --style bibtex
python research.py memory list
python research.py memory search "transformer"
python research.py memory show arxiv:2005.11401
python research.py memory delete arxiv:2005.11401
"""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv
load_dotenv()

from memory.index import PaperIndex
from memory.store import PaperStore
from tools.citations import format_citation
from tools.fetch import fetch_paper
from tools.search import search_papers

_store = PaperStore()
_index = PaperIndex(_store)


# ── search ────────────────────────────────────────────────────────────────────

def cmd_search(args: argparse.Namespace) -> None:
    sources = args.sources or None
    papers = search_papers(args.query, sources=sources, max_results=args.max)

    for paper in papers:
        _store.save_paper(paper)
        _index.add_paper(paper)

    _out([p.to_dict() for p in papers])


# ── fetch ─────────────────────────────────────────────────────────────────────

def cmd_fetch(args: argparse.Namespace) -> None:
    paper = _store.get_paper(args.paper_id)
    title = paper.title if paper else ""
    # Use stored pdf_url as fallback when --pdf-url not supplied
    pdf_url = args.pdf_url or (paper.pdf_url if paper else None)

    try:
        content = fetch_paper(args.paper_id, pdf_url=pdf_url, title=title)
    except ValueError as exc:
        _err(str(exc))
        return
    _out(content.to_dict())


# ── cite ──────────────────────────────────────────────────────────────────────

def cmd_cite(args: argparse.Namespace) -> None:
    paper = _store.get_paper(args.paper_id)
    if paper is None:
        _err(f"Paper '{args.paper_id}' not found in local memory. Run 'search' first.")
        return

    citation = format_citation(paper, style=args.style)
    _out({"paper_id": args.paper_id, "style": args.style, "citation": citation})


# ── memory ────────────────────────────────────────────────────────────────────

def cmd_memory(args: argparse.Namespace) -> None:
    sub = args.memory_cmd

    if sub == "list":
        papers = _store.list_papers()
        _out([{"paper_id": p.paper_id, "title": p.title, "year": p.year, "source": p.source}
              for p in papers])

    elif sub == "search":
        results = _index.search(args.query, top_k=args.top)
        _out([p.to_dict() for p in results])

    elif sub == "show":
        paper = _store.get_paper(args.paper_id)
        if paper is None:
            _err(f"Paper '{args.paper_id}' not found.")
            return
        data = paper.to_dict()
        summary = _store.get_summary(args.paper_id)
        if summary:
            data["summary"] = summary.to_dict()
        _out(data)

    elif sub == "delete":
        deleted = _store.delete_paper(args.paper_id)
        _out({"deleted": deleted, "paper_id": args.paper_id})


# ── helpers ───────────────────────────────────────────────────────────────────

def _out(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def _err(msg: str) -> None:
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


# ── argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research.py",
        description="Academic research toolkit for Claude Code.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="Search for academic papers")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--max", type=int, default=10, metavar="N",
                          help="Maximum results (default 10)")
    p_search.add_argument("--sources", nargs="+",
                          choices=["arxiv", "google_scholar"],
                          help="Databases to query (default: both)")

    # fetch
    p_fetch = sub.add_parser("fetch", help="Fetch full text of a paper")
    p_fetch.add_argument("paper_id", help="Paper ID (e.g. arxiv:2005.11401)")
    p_fetch.add_argument("--pdf-url", dest="pdf_url", default=None,
                         help="Direct PDF URL (optional fallback)")

    # cite
    p_cite = sub.add_parser("cite", help="Format a citation")
    p_cite.add_argument("paper_id", help="Paper ID (must be in local memory)")
    p_cite.add_argument("--style", default="apa",
                        choices=["apa", "mla", "bibtex"],
                        help="Citation style (default: apa)")

    # memory
    p_mem = sub.add_parser("memory", help="Manage locally saved papers")
    mem_sub = p_mem.add_subparsers(dest="memory_cmd", required=True)

    mem_sub.add_parser("list", help="List all saved papers")

    p_mem_search = mem_sub.add_parser("search", help="Keyword search saved papers")
    p_mem_search.add_argument("query", help="Search query")
    p_mem_search.add_argument("--top", type=int, default=5, metavar="K",
                              help="Number of results (default 5)")

    p_mem_show = mem_sub.add_parser("show", help="Show a saved paper (+ summary if cached)")
    p_mem_show.add_argument("paper_id", help="Paper ID")

    p_mem_del = mem_sub.add_parser("delete", help="Remove a paper from local memory")
    p_mem_del.add_argument("paper_id", help="Paper ID")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "search": cmd_search,
        "fetch": cmd_fetch,
        "cite": cmd_cite,
        "memory": cmd_memory,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
