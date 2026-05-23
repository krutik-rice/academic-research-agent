# Academic Research Agent

An agentic AI assistant that helps with academic research — searching papers, summarizing findings, synthesizing literature, and generating properly formatted citations.

Powered by [Claude](https://www.anthropic.com/claude) with tool use, [arXiv](https://arxiv.org), and [Semantic Scholar](https://www.semanticscholar.org).

---

## Features

- **Multi-source search** — searches arXiv and Semantic Scholar simultaneously, deduplicates results
- **Full-text retrieval** — fetches paper PDFs and HTML versions (ar5iv), extracts structured sections
- **Structured summarization** — extracts key findings, methodology, contributions, and limitations via Claude
- **Citation formatting** — APA, MLA, and BibTeX output
- **Persistent memory** — papers and summaries are cached to disk; the agent checks local memory before hitting external APIs
- **Agentic loop** — Claude autonomously decides which tools to use and iterates until the research question is answered

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/academic-research-agent.git
cd academic-research-agent
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Claude API key ([get one here](https://console.anthropic.com)) |
| `SEMANTIC_SCHOLAR_API_KEY` | No | Higher rate limits on Semantic Scholar |
| `ARXIV_BASE_URL` | No | Override arXiv API base URL |
| `STORAGE_PATH` | No | Local paper storage path (default: `./data`) |

### 3. Run

```bash
python -m agent
```

```
============================================================
  Academic Research Agent
  Powered by Claude + arXiv + Semantic Scholar
============================================================
Type a research question and press Enter.
Commands: 'quit' or Ctrl-C to exit.

Research> What are the key advances in large language model alignment?
```

---

## Usage

### Interactive CLI

```bash
python -m agent
```

### Programmatic API

```python
from agent.core import ResearchAgent

agent = ResearchAgent()  # reads ANTHROPIC_API_KEY from environment

answer = agent.research(
    "Summarise recent work on retrieval-augmented generation and format the top 3 papers as BibTeX."
)
print(answer)
```

### Use individual tools directly

```python
from tools.search import search_papers
from tools.fetch import fetch_paper
from tools.summarize import summarize_paper
from tools.citations import format_citation

# Search
papers = search_papers("transformer attention mechanism", max_results=5)

# Fetch full text
content = fetch_paper(papers[0].paper_id, pdf_url=papers[0].pdf_url)

# Summarise
summary = summarize_paper(papers[0], content=content)
print(summary.key_findings)

# Cite
print(format_citation(papers[0], style="bibtex"))
```

---

## Architecture

```
academic-research-agent/
├── agent/
│   ├── core.py              # Agentic loop (Claude + tool use)
│   ├── __main__.py          # CLI entry point  (python -m agent)
│   ├── prompts/
│   │   └── system.py        # System prompt
│   └── tools/               # Claude tool-use schema definitions
│       ├── search_tool.py
│       ├── fetch_tool.py
│       ├── summarize_tool.py
│       ├── citations_tool.py
│       └── memory_tool.py
├── tools/                   # Implementation layer (external APIs + Claude)
│   ├── search.py            # arXiv + Semantic Scholar search
│   ├── fetch.py             # PDF / HTML retrieval & parsing
│   ├── summarize.py         # Paper summarization via Claude
│   └── citations.py         # APA / MLA / BibTeX formatting
├── memory/
│   ├── store.py             # JSON file storage for papers & summaries
│   └── index.py             # Inverted-index for local keyword search
├── tests/                   # pytest test suite
├── .env.example
├── requirements.txt
└── CLAUDE.md
```

### How the agentic loop works

```
User query
    │
    ▼
ResearchAgent.research()
    │
    ├─► Claude (with tools) ──► tool_use? ──► _dispatch()
    │         ▲                                    │
    │         └────── tool_result ─────────────────┘
    │
    └─► end_turn ──► return final answer
```

Claude autonomously decides when to search, fetch, summarise, or format citations. It checks local memory first to avoid redundant API calls.

---

## Running Tests

```bash
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ --cov=. --cov-report=term-missing
```

All tests use mocks for external APIs — no real network calls or API keys required.

---

## Data Storage

Retrieved papers and summaries are stored as JSON files under `./data/` (or `$STORAGE_PATH`):

```
data/
├── papers/
│   ├── arxiv_2310.01234.json
│   └── s2_abc123def456.json
└── summaries/
    └── arxiv_2310.01234.json
```

The `data/` directory is git-ignored. Delete it to clear the local cache.

---

## Contributing

Contributions are welcome. Some good starting points:

- Add PubMed / Crossref / CORE as additional search sources
- Add semantic vector search (sentence-transformers) to `memory/index.py`
- Add a web UI or Jupyter notebook interface
- Export literature reviews to Markdown / LaTeX

Please open an issue before submitting a large PR.

---

## License

MIT — see [LICENSE](LICENSE).
