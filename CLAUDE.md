# Academic Research Agent

Agentic AI research assistant: searches arXiv + Semantic Scholar, fetches full paper text, summarizes via Claude, formats citations, caches results locally.

## 1. Stack

- **Python 3.10+**
- **anthropic** ≥0.40 — Claude API client, tool-use agentic loop (`claude-sonnet-4-6` default)
- **requests** — HTTP calls to arXiv and Semantic Scholar REST APIs
- **pdfplumber** — PDF text extraction
- **beautifulsoup4 + lxml** — HTML parsing (ar5iv paper pages)
- **python-dotenv** — `.env` file loading
- **pytest** — test runner (all tests mock external calls; no real network needed)
- Storage: plain JSON files on disk (no database)

## 2. Repo Map

```
agent/
  core.py          ResearchAgent class — agentic loop, tool dispatch
  __main__.py      CLI entry point (python -m agent)
  prompts/
    system.py      System prompt string
  tools/           Claude tool-use JSON schema definitions (one file per tool)
    search_tool.py
    fetch_tool.py
    summarize_tool.py
    citations_tool.py
    memory_tool.py

tools/             Actual implementation (called by agent/core.py dispatch)
  search.py        search_arxiv(), search_semantic_scholar(), search_papers()
                   Returns list[Paper] dataclass
  fetch.py         fetch_paper() → PaperContent; tries ar5iv HTML, falls back to PDF
  summarize.py     summarize_paper() → PaperSummary; calls Claude API separately
  citations.py     format_citation(paper, style) → str  (apa | mla | bibtex)

memory/
  store.py         PaperStore — save/get/list Paper and PaperSummary as JSON files
  index.py         PaperIndex — inverted-index keyword search over saved papers

tests/             pytest suite; all external APIs mocked with unittest.mock
data/              Runtime paper/summary storage (git-ignored, created on first run)
```

## 3. Commands

```bash
# Install
pip install -r requirements.txt

# Copy and fill in API keys
cp .env.example .env

# Run interactive CLI
python -m agent

# Run all tests (no API key needed)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing
```

## 4. Gotchas

- **Two `tools/` directories** — `agent/tools/` holds only Claude JSON schema dicts; `tools/` holds the real code. Never put implementation logic in `agent/tools/`.
- **`summarize_paper()` makes a second Claude API call** — it is not part of the main agentic loop; it creates its own `anthropic.Anthropic()` client. Costs tokens on every uncached call.
- **Summary caching** — `_handle_summarize_paper` checks `store.get_summary()` before calling Claude. Don't bypass the cache.
- **`PaperContent.to_dict()` truncates text** — `text` is capped at 6 000 chars and each section at 2 000 chars before being returned as a tool result. Full text lives in the `PaperContent` object in memory.
- **arXiv XML namespace** — arXiv Atom feed uses `http://www.w3.org/2005/Atom`; always use the `_ARXIV_NS` constant, never hardcode the string.
- **`search_papers()` deduplicates by lowercased title** — papers that appear on both arXiv and S2 are collapsed to the first hit.
- **Paper IDs have source prefix** — arXiv IDs are `arxiv:XXXX.XXXXX`; Semantic Scholar IDs are `s2:<hash>`. File names on disk replace `:` and `/` with `_`.
- **Environment variables** — `ANTHROPIC_API_KEY` is required. `SEMANTIC_SCHOLAR_API_KEY` is optional but avoids rate-limit 429s on repeated searches.

