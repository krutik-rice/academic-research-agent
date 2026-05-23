# Academic Research Agent

Python toolkit for Claude Code: searches arXiv + Semantic Scholar, fetches full paper text, formats citations, caches results locally. **No Anthropic API key needed** — Claude Code (or browser Claude) does the reading and reasoning; these tools do the data fetching.

## 1. Stack

- **Python 3.9+**
- **requests** — HTTP calls to arXiv and Semantic Scholar REST APIs
- **pdfplumber** — PDF text extraction
- **beautifulsoup4 + lxml** — HTML parsing (ar5iv paper pages)
- **pytest** — test runner (all tests mock external calls; no network needed)
- Storage: plain JSON files on disk under `./data/` (no database, no API key)

## 2. Repo Map

```
research.py        Unified CLI — the main entry point for Claude Code to call
                   Subcommands: search | fetch | cite | memory

tools/
  search.py        search_arxiv(), search_semantic_scholar(), search_papers()
                   → list[Paper]  (Paper is a dataclass with to_dict/from_dict)
  fetch.py         fetch_paper(paper_id, pdf_url) → PaperContent
                   tries ar5iv HTML first, falls back to PDF
  citations.py     format_citation(paper, style) → str  (apa | mla | bibtex)

memory/
  store.py         PaperStore — save/get/list/delete Paper + PaperSummary as JSON
  index.py         PaperIndex — inverted-index keyword search over saved papers
                   lazy-loads from disk on first search; call add_paper() after saving

tests/             pytest suite; all external APIs mocked — no network calls
data/              Runtime storage (git-ignored, auto-created on first run)
```

## 3. Commands

```bash
# Install (one-time)
pip install -r requirements.txt

# Search for papers (saves results to ./data/ automatically)
python research.py search "retrieval augmented generation" --max 8
python research.py search "diffusion models image" --sources arxiv --max 5

# Fetch full text of a paper
python research.py fetch arxiv:2005.11401
python research.py fetch arxiv:2005.11401 --pdf-url https://arxiv.org/pdf/2005.11401

# Format a citation (paper must be in local memory from a prior search)
python research.py cite arxiv:2005.11401 --style bibtex
python research.py cite arxiv:2005.11401 --style apa

# Memory management
python research.py memory list
python research.py memory search "transformer attention"
python research.py memory show arxiv:2005.11401
python research.py memory delete arxiv:2005.11401

# Run tests
pytest tests/ -v
pytest tests/ --cov=. --cov-report=term-missing
```

## 4. Gotchas

- **No API key required** — `anthropic` is not a dependency. Claude Code itself is the intelligence layer; these tools only fetch and format data.
- **`cite` requires a prior `search`** — `format_citation` reads from `./data/papers/`. If the paper isn't saved yet, run `search` first.
- **`PaperContent.to_dict()` truncates** — `text` caps at 6 000 chars, each section at 2 000. Full text is in the `PaperContent` object; truncation only applies to JSON output.
- **arXiv XML namespace** — always use the `_ARXIV_NS` constant in `tools/search.py`, never hardcode `http://www.w3.org/2005/Atom`.
- **`search_papers()` deduplicates by lowercased title** — a paper on both arXiv and S2 appears once (first source wins).
- **Paper ID format** — arXiv: `arxiv:XXXX.XXXXX`, Semantic Scholar: `s2:<hash>`. On disk, `:` and `/` are replaced with `_`.
- **`PaperIndex` is lazy** — it builds from disk on the first `search()` call. Call `add_paper()` immediately after saving a new paper so it's searchable in the same session without a full rebuild.
- **`SEMANTIC_SCHOLAR_API_KEY`** — optional env var; without it you'll hit rate limits quickly on repeated searches. Set it in your shell or a `.env` file.

