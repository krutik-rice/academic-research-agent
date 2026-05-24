# Academic Research Agent

Python + React toolkit: searches arXiv + Google Scholar, fetches full paper text, formats citations, analyzes limitations/future directions, synthesizes research gaps, discovers connected papers via co-citation, imports from BibTeX, and runs a local Ollama ReAct agent to assess research viability. **No Anthropic API key needed** — Claude Code is the intelligence layer; these tools fetch and parse data.

## 1. Stack

**Backend**
- **Python 3.9+**
- **FastAPI + uvicorn** — REST API (`api/main.py`); all Streamlit logic replaced
- **requests** — HTTP calls to arXiv, SerpAPI, and Semantic Scholar REST APIs
- **pdfplumber** — PDF text extraction
- **beautifulsoup4 + lxml** — HTML parsing (ar5iv paper pages)
- **pytest** — test runner (all tests mock external calls; no network needed)
- Storage: plain JSON files on disk under `./data/` (no database)
- **SERPAPI_API_KEY** env var — Google Scholar + web search (free tier: 100 searches/month)

**Frontend**
- **Next.js 15 + React** — App Router, TypeScript
- **Tailwind CSS v4** — utility-first; design tokens in `frontend/app/globals.css`
- **Node.js 20+** required

## 2. Repo Map

```
start.py           Starts both servers: python start.py
                   Backend on :8000, frontend on :3000

api/
  main.py          FastAPI app — all REST endpoints
                   GET  /api/papers              list library
                   POST /api/papers/search        search + save
                   DELETE /api/papers/{id}        delete
                   POST /api/papers/{id}/fetch    fetch full text
                   GET  /api/papers/{id}/cite     format citation
                   POST /api/papers/{id}/analyze  analyze paper
                   GET  /api/analysis/status      analysis progress
                   POST /api/analysis/gaps        research gaps (SSE)
                   POST /api/papers/connected     connected papers (SSE)
                   POST /api/bib/import           BibTeX import (SSE)
                   GET  /api/graph                vis.js graph HTML
                   GET/PUT /api/summaries/{id}    paper summaries
                   GET  /api/agent/status         Ollama status + models
                   POST /api/agent/pull           pull model (SSE)
                   POST /api/agent/run            run ReAct agent (SSE)

frontend/
  app/
    layout.tsx     Root layout with Sidebar
    globals.css    Design tokens (krutikp.com palette: #202124 bg, #8ab4f8 accent)
    search/        Search arXiv + Scholar
    library/       Saved papers, BibTeX import, connected papers
    fetch/         Full text viewer (sections + raw)
    citations/     APA / MLA / BibTeX formatter
    analyze/       Per-paper analysis + research gaps finder
    graph/         vis.js similarity graph (iframe)
    agent/         Ollama ReAct agent with streaming trace
  components/
    Sidebar.tsx    Navigation sidebar
    PaperCard.tsx  Reusable paper card
    ui.tsx         Card, Btn, Input, Select, Badge, ProgressBar, Spinner, banners
  lib/
    types.ts       Shared TypeScript interfaces
    api.ts         Typed fetch wrappers + SSE streaming helpers

research.py        Unified CLI (unchanged)
                   Subcommands: search | fetch | cite | analyze | memory

tools/
  search.py        search_arxiv(), search_google_scholar(), search_papers()
  fetch.py         fetch_paper(paper_id, pdf_url) → PaperContent
  citations.py     format_citation(paper, style) → str  (apa | mla | bibtex)
  analyze.py       analyze_paper(paper_id, store) → PaperAnalysis
  synthesize.py    find_research_gaps(), get_analysis_status()
  connected.py     find_connected_papers() — co-citation via Semantic Scholar
  bib.py           parse_bib(), import_from_bib()
  graph.py         build_graph() → {nodes, edges};  render_html() → vis.js HTML string
  websearch.py     search_web() — SerpAPI engine=google
  agent.py         OllamaClient, ResearchAgent (ReAct loop), ensure_ollama_running()

memory/
  store.py         PaperStore, PaperSummary
  index.py         PaperIndex (lazy inverted-index)

tests/             pytest suite; all external APIs mocked
data/              Runtime storage (git-ignored)
ollama/            Bundled ollama.exe (git-ignored, Windows only)
```

## 3. Commands

```bash
# Install Python deps (one-time)
pip install -r requirements.txt

# Install frontend deps (one-time)
cd frontend && npm install && cd ..

# Run both servers together
python start.py
# → Backend:  http://localhost:8000
# → Frontend: http://localhost:3000

# Or run separately:
python -m uvicorn api.main:app --reload --port 8000
cd frontend && npm run dev

# CLI (unchanged)
python research.py search "retrieval augmented generation" --max 8
python research.py fetch arxiv:2005.11401
python research.py cite arxiv:2005.11401 --style bibtex
python research.py analyze arxiv:2005.11401
python research.py memory list

# Tests
pytest tests/ -v
```

## 4. Gotchas

- **No Anthropic SDK** — `anthropic` is not a dependency. Never add it.
- **SSE streaming** — agent run, model pull, gaps, connected papers, and BibTeX import all use Server-Sent Events. Frontend reads via `fetch()` + `ReadableStream`, not `EventSource` (which is GET-only). Backend uses FastAPI `StreamingResponse` with `text/event-stream`.
- **Ollama auto-start** — `ensure_ollama_running()` launches `ollama serve` silently on first agent run. Model pull happens in-app via the Agent page (no terminal needed). Model files live in `%USERPROFILE%\.ollama\models`, not the project dir.
- **`cite` requires a prior `search`** — `format_citation` reads from `./data/papers/`. Run search first.
- **`analyze` requires full text** — arXiv papers work via ar5iv HTML. Google Scholar papers often return `method="unavailable"` and are skipped.
- **`find_research_gaps` overlap threshold** — default 75%: a theme must appear in ≥75% of analyzed papers. For small libraries (≤2 papers) minimum is always 2.
- **`find_connected_papers` requires arXiv papers** — queries Semantic Scholar by arXiv ID. Scholar-only libraries return empty.
- **BibTeX import fallback** — entries without arXiv ID are title-searched on arXiv. Non-English or abbreviated titles often fail to match.
- **Graph rendered in iframe** — `render_html()` returns a self-contained vis.js HTML string; the Graph page renders it via `<iframe srcDoc={html}>` so JS executes correctly.
- **Paper ID format** — `arxiv:XXXX.XXXXX`, `scholar:<id>`, `s2:<hash>`. On disk `:` and `/` → `_`.
- **`PaperContent.to_dict()` truncates** — `text` caps at 6 000 chars, sections at 2 000.
- **Secrets** — only `SERPAPI_API_KEY` in `.env`. Never hardcode keys.
- **CORS** — FastAPI allows `http://localhost:3000`. Next.js proxies `/api/*` → `http://localhost:8000/api/*` via `next.config.ts` rewrites.
