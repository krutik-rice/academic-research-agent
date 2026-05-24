"""FastAPI backend for the Academic Research Agent."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from typing import Annotated, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from memory.store import PaperStore, PaperSummary
from memory.index import PaperIndex
from tools.search import search_papers
from tools.fetch import fetch_paper
from tools.citations import format_citation
from tools.analyze import analyze_paper
from tools.synthesize import find_research_gaps, get_analysis_status
from tools.connected import find_connected_papers
from tools.bib import import_from_bib
from tools.graph import build_graph, render_html
from tools.agent import ResearchAgent, OllamaClient, ensure_ollama_running

app = FastAPI(title="Academic Research Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = PaperStore()
index = PaperIndex(store)

_NOT_FOUND = "Paper not found"
_SSE_MEDIA = "text/event-stream"
_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


# ── SSE helper ─────────────────────────────────────────────────────────────────

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _require_paper(paper_id: str):
    paper = store.get_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return paper


# ── Pydantic models ────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    sources: Optional[list[str]] = None
    max_results: int = 8

class GapsRequest(BaseModel):
    overlap_fraction: float = 0.75

class ConnectedRequest(BaseModel):
    max_new: int = 10

class AgentRunRequest(BaseModel):
    paper_id: str
    model: str = "llama3.1"
    max_iterations: int = 5

class AgentPullRequest(BaseModel):
    model: str

class SummaryUpdateRequest(BaseModel):
    summary: str = ""
    limitations: list[str] = []
    future_directions: list[str] = []
    key_findings: list[str] = []
    methodology: str = ""
    contributions: list[str] = []
    keywords: list[str] = []


# ── Papers ─────────────────────────────────────────────────────────────────────

@app.get("/api/papers")
def list_papers():
    return [p.to_dict() for p in store.list_papers()]


@app.post("/api/papers/search")
def search(req: SearchRequest):
    try:
        papers = search_papers(req.query, sources=req.sources, max_results=req.max_results)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    for p in papers:
        store.save_paper(p)
        index.add_paper(p)
    return [p.to_dict() for p in papers]


@app.delete("/api/papers/{paper_id:path}")
def delete_paper(paper_id: str):
    store.delete_paper(paper_id)
    return {"ok": True}


@app.post("/api/papers/{paper_id:path}/fetch")
def fetch_full_text(paper_id: str):
    paper = _require_paper(paper_id)
    try:
        content = fetch_paper(paper_id, pdf_url=paper.pdf_url, title=paper.title)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return content.to_dict()


@app.get("/api/papers/{paper_id:path}/cite")
def cite_paper(paper_id: str, style: Annotated[str, Query()] = "apa"):
    paper = _require_paper(paper_id)
    try:
        citation = format_citation(paper, style=style)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"citation": citation, "style": style}


@app.post("/api/papers/{paper_id:path}/analyze")
def analyze(paper_id: str):
    _require_paper(paper_id)
    try:
        result = analyze_paper(paper_id, store)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result.to_dict()


# ── Analysis ───────────────────────────────────────────────────────────────────

@app.get("/api/analysis/status")
def analysis_status():
    return get_analysis_status(store)


@app.post("/api/analysis/gaps")
def research_gaps(req: GapsRequest):
    async def stream():
        loop = asyncio.get_event_loop()
        yield _sse({"type": "progress", "message": "Analyzing papers…"})
        try:
            report = await loop.run_in_executor(
                None,
                lambda: find_research_gaps(store, progress_cb=None,
                                           overlap_fraction=req.overlap_fraction),
            )
            yield _sse({"type": "done", "result": {
                "themes": report.themes,
                "analyzed_count": report.analyzed_count,
                "skipped_count": report.skipped_count,
            }})
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(stream(), media_type=_SSE_MEDIA, headers=_SSE_HEADERS)


# ── Connected papers ───────────────────────────────────────────────────────────

@app.post("/api/papers/connected")
def connected_papers(req: ConnectedRequest):
    async def stream():
        loop = asyncio.get_event_loop()
        yield _sse({"type": "progress", "message": "Searching for connected papers…"})
        try:
            papers, method = await loop.run_in_executor(
                None,
                lambda: find_connected_papers(store, max_new=req.max_new, progress_cb=None),
            )
            for p in papers:
                store.save_paper(p)
                index.add_paper(p)
            yield _sse({"type": "done", "result": {
                "papers": [p.to_dict() for p in papers],
                "method": method,
            }})
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(stream(), media_type=_SSE_MEDIA, headers=_SSE_HEADERS)


# ── BibTeX ─────────────────────────────────────────────────────────────────────

@app.post("/api/bib/import")
async def bib_import(file: Annotated[UploadFile, File()]):
    bib_text = (await file.read()).decode("utf-8", errors="replace")

    async def stream():
        loop = asyncio.get_event_loop()
        yield _sse({"type": "progress", "message": "Parsing BibTeX…"})
        try:
            result = await loop.run_in_executor(
                None,
                lambda: import_from_bib(bib_text, store, index, progress_cb=None),
            )
            yield _sse({"type": "done", "result": {
                "imported": result.imported,
                "skipped": result.skipped,
                "not_found": result.not_found,
                "total": result.total,
            }})
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(stream(), media_type=_SSE_MEDIA, headers=_SSE_HEADERS)


# ── Graph ──────────────────────────────────────────────────────────────────────

@app.get("/api/graph")
def graph():
    papers = store.list_papers()
    if not papers:
        return {"html": "<p style='color:#9aa0a6;padding:2rem'>No papers in library yet.</p>",
                "node_count": 0, "edge_count": 0}
    data = build_graph(papers)
    return {"html": render_html(data),
            "node_count": len(data["nodes"]),
            "edge_count": len(data["edges"])}


# ── Summaries ──────────────────────────────────────────────────────────────────

@app.get("/api/summaries")
def list_summaries():
    return [
        {"paper": p.to_dict(),
         "summary": store.get_summary(p.paper_id).__dict__ if store.get_summary(p.paper_id) else None}
        for p in store.list_papers()
    ]


@app.get("/api/summaries/{paper_id:path}")
def get_summary(paper_id: str):
    s = store.get_summary(paper_id)
    return s.__dict__ if s else None


@app.put("/api/summaries/{paper_id:path}")
def save_summary(paper_id: str, req: SummaryUpdateRequest):
    paper = _require_paper(paper_id)
    summary = store.get_summary(paper_id) or PaperSummary(paper_id=paper_id, title=paper.title)
    summary.summary = req.summary
    summary.limitations = req.limitations
    summary.future_directions = req.future_directions
    summary.key_findings = req.key_findings
    summary.methodology = req.methodology
    summary.contributions = req.contributions
    summary.keywords = req.keywords
    store.save_summary(summary)
    return {"ok": True}


# ── Agent ──────────────────────────────────────────────────────────────────────

@app.get("/api/agent/status")
def agent_status():
    client = OllamaClient()
    available = client.is_available()
    return {"available": available, "models": client.list_models() if available else []}


@app.post("/api/agent/pull")
def agent_pull(req: AgentPullRequest):
    async def stream():
        loop = asyncio.get_event_loop()
        client = OllamaClient()

        if not client.is_available():
            yield _sse({"type": "progress", "message": "Starting Ollama server…"})
            ok = await loop.run_in_executor(None, ensure_ollama_running)
            if not ok:
                yield _sse({"type": "error", "message": "Could not start Ollama server."})
                return

        queue: asyncio.Queue = asyncio.Queue()

        def _progress(status: str, completed: int, total: int) -> None:
            asyncio.run_coroutine_threadsafe(
                queue.put({"status": status, "completed": completed, "total": total}),
                loop,
            )

        def _pull() -> None:
            try:
                client.pull_model(req.model, progress_cb=_progress)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        threading.Thread(target=_pull, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                yield _sse({"type": "done", "message": f"Model {req.model} ready."})
                break
            yield _sse({"type": "progress", **item})

    return StreamingResponse(stream(), media_type=_SSE_MEDIA, headers=_SSE_HEADERS)


@app.post("/api/agent/run")
def agent_run(req: AgentRunRequest):
    async def stream():
        loop = asyncio.get_event_loop()

        if not OllamaClient(model=req.model).is_available():
            yield _sse({"type": "progress", "message": "Starting Ollama…"})
            ok = await loop.run_in_executor(None, ensure_ollama_running)
            if not ok:
                yield _sse({"type": "error", "message": "Could not start Ollama."})
                return

        queue: asyncio.Queue = asyncio.Queue()

        def _progress(current: int, total: int, msg: str) -> None:
            asyncio.run_coroutine_threadsafe(
                queue.put({"type": "progress", "current": current,
                           "total": total, "message": msg}),
                loop,
            )

        def _run() -> None:
            try:
                agent = ResearchAgent(model=req.model, max_iterations=req.max_iterations)
                report = agent.run(req.paper_id, store=store, progress_cb=_progress)
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "__report__", "report": report}), loop
                )
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "error", "message": str(exc)}), loop
                )

        threading.Thread(target=_run, daemon=True).start()

        while True:
            item = await queue.get()
            item_type = item["type"]
            if item_type == "__report__":
                yield _sse({"type": "done", "report": item["report"].to_dict()})
                break
            yield _sse(item)
            if item_type == "error":
                break

    return StreamingResponse(stream(), media_type=_SSE_MEDIA, headers=_SSE_HEADERS)
