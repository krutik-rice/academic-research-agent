# Academic Research Agent

Python toolkit for Claude Code: searches arXiv + Google Scholar, fetches full paper text, formats citations, analyzes limitations/future directions, synthesizes research gaps, discovers connected papers via co-citation, and imports from BibTeX. **No Anthropic API key needed** — Claude Code does the reading and reasoning; these tools fetch and parse data.

## 1. Stack

- **Python 3.9+**
- **requests** — HTTP calls to arXiv, SerpAPI, and Semantic Scholar REST APIs
- **pdfplumber** — PDF text extraction
- **beautifulsoup4 + lxml** — HTML parsing (ar5iv paper pages)
- **streamlit 1.12** — web UI (`app.py`); note: use only APIs available in 1.12 (no `cache_resource`, no `link_button`, no `label_visibility`, no `horizontal=` on radio, no `st.rerun()` — use `st.experimental_rerun()`, no `st.tabs()` — added in 1.14, use sidebar `st.radio()` navigation instead)
- **pytest** — test runner (all tests mock external calls; no network needed)
- Storage: plain JSON files on disk under `./data/` (no database)
- **SERPAPI_API_KEY** env var — Google Scholar search (free tier: 100 searches/month at serpapi.com)

## 2. Repo Map

```
app.py             Streamlit web UI — run with: streamlit run app.py
                   Tabs: Search | Library | Fetch Full Text | Citations | Analyze
                   Library tab: "Find Connected Papers" button + BibTeX import
                   Analyze tab: per-paper analysis + progress tracker + "Find Research Gaps" button

research.py        Unified CLI — the main entry point for Claude Code to call
                   Subcommands: search | fetch | cite | analyze | memory

tools/
  search.py        search_arxiv(), search_google_scholar(), search_papers()
                   → list[Paper]  (Paper is a dataclass with to_dict/from_dict)
                   google_scholar uses SerpAPI (engine=google_scholar)
  fetch.py         fetch_paper(paper_id, pdf_url) → PaperContent
                   tries ar5iv HTML first, falls back to PDF
  citations.py     format_citation(paper, style) → str  (apa | mla | bibtex)
  analyze.py       analyze_paper(paper_id, store) → PaperAnalysis
                   extracts limitations + future_directions from section headings;
                   falls back to keyword sentence search in Conclusion/Discussion
  synthesize.py    get_analysis_status(store) → list[dict]
                     per-paper analyzed/pending status (lim_count, fut_count)
                   find_research_gaps(store, progress_cb, overlap_fraction=0.75)
                     → ResearchGapsReport
                     analyzes all papers; clusters by bigram/trigram themes;
                     min_papers = max(2, round(overlap_fraction * analyzed_count))
  connected.py     find_connected_papers(store, max_new, progress_cb)
                     → (list[Paper], method_str)
                     pass 1: co-citation — fetches /references for up to 10 arXiv seeds
                       via Semantic Scholar Graph API; ranks by cross-library frequency
                     pass 2: S2 recommendations — /recommendations/v1/papers/forpaper/{id}
                       for up to 5 seeds; fills remaining slots
                     no API key required; 0.6 s pause per call (~15 calls total)
  bib.py           parse_bib(content) → list[BibEntry]
                     regex BibTeX parser; detects arXiv ID from eprint/archiveprefix or URL
                   import_from_bib(content, store, index, progress_cb)
                     → ImportResult(imported, skipped, not_found, total)
                     arXiv entries saved from metadata; others searched by title on arXiv

memory/
  store.py         PaperStore — save/get/list/delete Paper + PaperSummary as JSON
                   PaperSummary has: limitations, future_directions, key_findings,
                   methodology, contributions, keywords
  index.py         PaperIndex — inverted-index keyword search over saved papers
                   lazy-loads from disk on first search; call add_paper() after saving

tests/             pytest suite; all external APIs mocked — no network calls
data/              Runtime storage (git-ignored, auto-created on first run)
```

## 3. Commands

```bash
# Install (one-time)
pip install -r requirements.txt

# Run the web UI
streamlit run app.py

# Search for papers (saves results to ./data/ automatically)
python research.py search "retrieval augmented generation" --max 8
python research.py search "diffusion models image" --sources arxiv --max 5
python research.py search "diffusion models" --sources google_scholar --max 5

# Fetch full text of a paper
python research.py fetch arxiv:2005.11401
python research.py fetch arxiv:2005.11401 --pdf-url https://arxiv.org/pdf/2005.11401

# Format a citation (paper must be in local memory from a prior search)
python research.py cite arxiv:2005.11401 --style bibtex
python research.py cite arxiv:2005.11401 --style apa

# Extract limitations and future directions from a paper's full text
python research.py analyze arxiv:2005.11401

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
- **`analyze` requires a prior `search` or known `pdf_url`** — needs metadata from store to resolve pdf_url. arXiv papers always work via ar5iv HTML. Google Scholar papers often fail (no clean HTML), so `method="unavailable"` is returned and the paper is skipped.
- **`find_research_gaps` overlap threshold** — default 75%: a theme must appear in ≥75% of analyzed papers to surface. For small libraries (≤2 papers analyzed) the minimum is always 2. Adjust via the UI slider or `overlap_fraction` parameter.
- **`find_research_gaps` skips papers it can't fetch** — check `report.skipped_count`. A library of mostly Google Scholar papers will produce fewer results.
- **`find_connected_papers` requires arXiv papers** — Semantic Scholar is queried using arXiv IDs. Google Scholar–only libraries return an empty result. Non-arXiv papers returned by S2 get `paper_id = s2:{hash}` and `source = "semantic_scholar"`.
- **BibTeX import fallback** — entries without an arXiv ID or URL are matched by title search on arXiv. If the title doesn't match exactly, the entry appears in `not_found`. Non-English or highly abbreviated titles often fail to match.
- **`PaperContent.to_dict()` truncates** — `text` caps at 6 000 chars, each section at 2 000. Full text is in the `PaperContent` object; truncation only applies to JSON output.
- **arXiv XML namespace** — always use the `_ARXIV_NS` constant in `tools/search.py`, never hardcode `http://www.w3.org/2005/Atom`.
- **Paper ID format** — arXiv: `arxiv:XXXX.XXXXX`, Google Scholar: `scholar:<result_id>`, Semantic Scholar: `s2:<hash>`. On disk, `:` and `/` are replaced with `_`.
- **`PaperIndex` is lazy** — it builds from disk on the first `search()` call. Call `add_paper()` immediately after saving a new paper so it's searchable in the same session without a full rebuild.
- **`SERPAPI_API_KEY`** — required for `google_scholar` source; without it that source raises `ValueError` and `search_papers()` prints a warning and continues with arXiv only. Get a free key at serpapi.com (100 free searches/month). `arxiv` source is always free with no key needed.
- **Streamlit 1.12 compatibility** — `app.py` deliberately avoids APIs added after 1.12: no `st.cache_resource` (use module-level init), no `st.link_button` (use `st.markdown("[text](url)"`), no `label_visibility=`, no `horizontal=True` on radio, no `st.rerun()` (use `st.experimental_rerun()`), no `type="primary"` on `st.form_submit_button`.
