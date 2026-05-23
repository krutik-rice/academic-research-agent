# Academic Research Agent

An agentic AI assistant that helps with academic research tasks — finding papers, summarizing literature, synthesizing sources, and supporting the research workflow.

## Project Purpose

This agent automates and augments academic research by:
- Searching and retrieving academic papers (arXiv, Semantic Scholar, PubMed, etc.)
- Summarizing and extracting key findings from papers
- Synthesizing literature across multiple sources
- Generating structured literature reviews and annotated bibliographies
- Tracking citations and research threads
- Answering research questions grounded in retrieved sources

## Architecture

```
academic-research-agent/
├── CLAUDE.md
├── agent/
│   ├── __init__.py
│   ├── core.py          # Main agent loop and orchestration
│   ├── tools/           # Tool definitions (search, fetch, summarize)
│   └── prompts/         # System prompts and templates
├── tools/
│   ├── search.py        # Academic search APIs (arXiv, Semantic Scholar, etc.)
│   ├── fetch.py         # PDF/HTML paper retrieval and parsing
│   ├── summarize.py     # Paper summarization and extraction
│   └── citations.py     # Citation formatting and tracking
├── memory/
│   ├── store.py         # Persistent storage for papers and notes
│   └── index.py         # Vector index for semantic retrieval
├── tests/
└── requirements.txt
```

## Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent interactively
python -m agent

# Run tests
pytest tests/
```

## Model

Uses the Claude API (`claude-sonnet-4-6` by default). Set `ANTHROPIC_API_KEY` in your environment or a `.env` file.

## Development Guidelines

- Tools must return structured data (dicts/dataclasses), not raw strings
- All external API calls go through `tools/` — never directly in agent logic
- Prompts live in `agent/prompts/` — keep them versioned and readable
- Prefer cited, grounded responses over hallucinated summaries
- Tests should cover tool outputs and agent decision paths, not just unit functions

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (required) |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API key (optional, higher rate limits) |
| `ARXIV_BASE_URL` | Override arXiv API base (default: `https://export.arxiv.org/api/`) |
| `STORAGE_PATH` | Path for local paper/note storage (default: `./data/`) |
