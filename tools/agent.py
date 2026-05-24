"""ReAct-style research viability agent powered by a local Ollama model.

How it works
------------
The agent runs a Reason + Act loop (ReAct pattern):

  1. The LLM receives the paper as context and a system prompt that defines
     four tools: search_web, search_arxiv, read_section, finish.

  2. Each iteration the LLM produces:
       Thought: <what I know and what I need to find>
       Action:  <tool name>
       Action Input: <query or JSON>

  3. The agent executes the tool and appends the Observation to the message
     history so the LLM builds up context across iterations.

  4. read_section lets the agent revisit the same paper sections multiple
     times — each re-read informed by what web/arXiv searches revealed.

  5. When the LLM calls finish with a JSON verdict the loop ends and an
     AgentReport is returned.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import requests

_OLLAMA_DEFAULT_URL = "http://localhost:11434"

from memory.store import PaperStore, PaperSummary
from tools.fetch import fetch_paper, PaperContent
from tools.search import Paper, search_arxiv
from tools.websearch import search_web


# ── Ollama client ─────────────────────────────────────────────────────────────

class OllamaClient:
    """Thin HTTP wrapper for a locally running Ollama instance."""

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = _OLLAMA_DEFAULT_URL,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []

    def pull_model(
        self,
        model: str,
        progress_cb: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        """Stream-pull a model from the Ollama registry.

        progress_cb(status, completed_bytes, total_bytes) is called for each
        progress chunk.  Raises RuntimeError on failure.
        """
        resp = requests.post(
            f"{self.base_url}/api/pull",
            json={"name": model, "stream": True},
            stream=True,
            timeout=7200,
        )
        if resp.status_code == 404:
            raise RuntimeError(f"Model '{model}' not found in Ollama registry.")
        resp.raise_for_status()
        for raw in resp.iter_lines():
            done = self._handle_pull_line(raw, progress_cb)
            if done:
                break

    @staticmethod
    def _handle_pull_line(
        raw: bytes,
        progress_cb: Optional[Callable[[str, int, int], None]],
    ) -> bool:
        """Parse one streamed pull line; return True when pull is complete."""
        if not raw:
            return False
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return False
        status    = data.get("status", "")
        total     = int(data.get("total", 0))
        completed = int(data.get("completed", 0))
        if progress_cb:
            progress_cb(status, completed, total)
        return status == "success"

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
    ) -> str:
        """Send a chat request and return the assistant's reply."""
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model":   self.model,
                "messages": messages,
                "stream":  False,
                "options": {"temperature": temperature},
            },
            timeout=300,
        )
        if resp.status_code == 404:
            raise RuntimeError(
                f"Model '{self.model}' not found. "
                f"Pull it first: ollama pull {self.model}"
            )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ── Server lifecycle ──────────────────────────────────────────────────────────

def _find_ollama_binary() -> str:
    """Return the path to the ollama executable.

    Prefers the binary bundled under <project_root>/ollama/ so the project
    is self-contained.  Falls back to whatever is on the system PATH.
    """
    # Walk up from this file's directory to find the project root
    project_root = Path(__file__).parent.parent
    for candidate in [
        project_root / "ollama" / "ollama.exe",   # Windows bundled
        project_root / "ollama" / "ollama",        # macOS/Linux bundled
    ]:
        if candidate.is_file():
            return str(candidate)
    return "ollama"  # fall back to system PATH


def ensure_ollama_running(
    ollama_url: str = _OLLAMA_DEFAULT_URL,
    timeout: float = 20.0,
) -> bool:
    """Start `ollama serve` in the background if not already running.

    Tries the binary bundled at <project>/ollama/ollama[.exe] first,
    then falls back to the system PATH.
    Returns True once the server is reachable, False if it could not start.
    """
    client = OllamaClient(base_url=ollama_url)
    if client.is_available():
        return True

    binary = _find_ollama_binary()
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(
            [binary, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    except FileNotFoundError:
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1.0)
        if client.is_available():
            return True
    return False


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class AgentStep:
    """One Thought → Action → Observation cycle."""
    iteration:    int
    thought:      str
    action:       str   # search_web | search_arxiv | read_section | finish
    action_input: str
    observation:  str
    elapsed_s:    float = 0.0

    def to_dict(self) -> dict:
        return {
            "iteration":    self.iteration,
            "thought":      self.thought,
            "action":       self.action,
            "action_input": self.action_input,
            "observation":  self.observation[:600],
            "elapsed_s":    round(self.elapsed_s, 1),
        }


@dataclass
class AgentReport:
    """Final output of a ResearchAgent run."""
    paper_id:         str
    title:            str
    model:            str
    total_iterations: int
    steps:            list[AgentStep]

    # Verdict fields (populated from the finish JSON)
    verdict:          str         # worth_pursuing | well_covered | partially_covered | unclear
    confidence:       float       # 0.0 – 1.0
    reasoning:        str
    gaps:             list[str]   # open problems the paper leaves unresolved
    directions:       list[str]   # suggested follow-up research directions
    competing_work:   list[str]   # papers found that address the same problem
    sources:          list[str] = field(default_factory=list)  # real URLs from tool observations

    def to_dict(self) -> dict:
        return {
            "paper_id":         self.paper_id,
            "title":            self.title,
            "model":            self.model,
            "total_iterations": self.total_iterations,
            "verdict":          self.verdict,
            "confidence":       self.confidence,
            "reasoning":        self.reasoning,
            "gaps":             self.gaps,
            "directions":       self.directions,
            "competing_work":   self.competing_work,
            "sources":          self.sources,
            "steps":            [s.to_dict() for s in self.steps],
        }


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a rigorous research analysis agent. Your goal is to deeply analyze an
academic paper and assess whether its core research problem is still worth pursuing.

You work iteratively — each iteration you learn something new, either by re-reading
the paper with fresh context or by searching for related work. Take your time.

AVAILABLE TOOLS
---------------
search_web(query)       Search the general web for recent news, blog posts, and
                        commentary about this research problem or competing solutions.

search_arxiv(query)     Search arXiv for recent academic papers on the topic.
                        Use this to find papers that might solve the same problem.

read_section(section)   Re-read a specific section of the paper being analyzed.
                        Valid section names: abstract, introduction, methodology,
                        results, conclusion, limitations, related_work, discussion.
                        Use this multiple times — re-reading with new context each
                        time is how you deepen your understanding.

finish(json)            End the analysis with your verdict. The JSON must contain:
                          verdict: "worth_pursuing" | "well_covered" |
                                   "partially_covered" | "unclear"
                          confidence: float 0.0-1.0
                          reasoning: string (detailed explanation)
                          gaps: list of open sub-problems still unsolved
                          directions: list of specific follow-up research directions
                          competing_work: list of "Title (Year) — brief note" strings

RESPONSE FORMAT
---------------
You MUST respond in EXACTLY this format on every turn. No extra text before Thought.

Thought: <your reasoning — what you know, what you need to find out, what it means>
Action: <one of: search_web | search_arxiv | read_section | finish>
Action Input: <the query string, section name, or JSON for finish>

STRATEGY
--------
1. Start with read_section: introduction — understand the core problem claim.
2. Then read_section: conclusion — see what was achieved and what was left open.
3. search_web with a focused query about the problem space and recent developments.
4. search_arxiv to find papers that might have already solved the same problem.
5. read_section: limitations — re-read this with the knowledge of what you found.
6. Optionally do one more targeted search based on what the limitations revealed.
7. finish with your verdict when you have enough evidence.

Be specific in searches. Think like a skeptic: what would invalidate this paper?
What has the field done in the past 1-2 years? Is the core gap still open?
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class ResearchAgent:
    """ReAct agent that iteratively analyzes a paper for research viability."""

    def __init__(
        self,
        model: str = "llama3.1",
        max_iterations: int = 5,
        ollama_url: str = _OLLAMA_DEFAULT_URL,
    ) -> None:
        self.llm = OllamaClient(model=model, base_url=ollama_url)
        self.model = model
        self.max_iterations = max_iterations

    # ── Public ────────────────────────────────────────────────────────────────

    def run(
        self,
        paper_id: str,
        store: PaperStore,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ) -> AgentReport:
        """Run the ReAct loop for a single paper."""
        if not self.llm.is_available():
            raise RuntimeError(
                "Ollama is not running. Start it with: ollama serve"
            )

        paper = store.get_paper(paper_id)
        if paper is None:
            raise ValueError(f"Paper '{paper_id}' not found in library.")

        # Fetch full text (may be slow — show progress)
        if progress_cb:
            progress_cb(0, self.max_iterations, "Fetching full paper text…")
        try:
            content = fetch_paper(
                paper_id, pdf_url=paper.pdf_url, title=paper.title
            )
        except Exception:
            content = None

        paper_context = self._build_paper_context(paper, content)

        # Seed message history
        messages: list[dict] = [
            {"role": "system",  "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Analyze the following paper and assess whether its research "
                    "problem is worth pursuing further.\n\n"
                    f"{paper_context}\n\n"
                    "Begin your analysis now."
                ),
            },
        ]

        steps: list[AgentStep] = []
        seen_urls: list[str] = []
        url_set: set[str] = set()

        for iteration in range(1, self.max_iterations + 1):
            if progress_cb:
                progress_cb(iteration - 1, self.max_iterations,
                            f"Iteration {iteration}: asking {self.model}…")

            t0 = time.time()
            response = self._chat(messages)
            thought, action, action_input = self._parse_response(response)
            elapsed = time.time() - t0

            if action == "finish":
                verdict_data = self._parse_finish(action_input)
                steps.append(AgentStep(iteration=iteration, thought=thought,
                                       action="finish", action_input=action_input,
                                       observation="Analysis complete.", elapsed_s=elapsed))
                if progress_cb:
                    progress_cb(self.max_iterations, self.max_iterations, "Done")
                return AgentReport(paper_id=paper_id, title=paper.title,
                                   model=self.model, total_iterations=iteration,
                                   steps=steps, sources=seen_urls, **verdict_data)

            if progress_cb:
                progress_cb(iteration - 1, self.max_iterations,
                            f"Iteration {iteration}: {action}({action_input[:55]}…)")
            observation = self._execute_tool(action, action_input, paper, content)
            self._collect_urls(observation, seen_urls, url_set)

            steps.append(AgentStep(iteration=iteration, thought=thought,
                                   action=action, action_input=action_input,
                                   observation=observation, elapsed_s=time.time() - t0))
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": (
                f"Observation:\n{observation[:1800]}\n\n"
                "Continue your analysis. You may re-read sections, search "
                "for more information, or call finish if you have enough evidence."
            )})

        return self._forced_finish(messages, steps, paper_id, paper.title, seen_urls,
                                   progress_cb)

    # ── Private: helpers ──────────────────────────────────────────────────────

    def _chat(self, messages: list[dict]) -> str:
        try:
            return self.llm.chat(messages)
        except Exception as exc:
            raise RuntimeError(f"Ollama call failed: {exc}") from exc

    @staticmethod
    def _collect_urls(text: str, seen: list[str], seen_set: set[str]) -> None:
        for u in re.findall(r"https?://\S+", text):
            u = u.rstrip(".,)")
            if u not in seen_set:
                seen_set.add(u)
                seen.append(u)

    def _forced_finish(
        self,
        messages: list[dict],
        steps: list[AgentStep],
        paper_id: str,
        title: str,
        seen_urls: list[str],
        progress_cb: Optional[Callable[[int, int, str], None]],
    ) -> AgentReport:
        if progress_cb:
            progress_cb(self.max_iterations, self.max_iterations,
                        "Max iterations reached — synthesizing verdict…")
        messages.append({"role": "user", "content": (
            "You have reached the maximum number of iterations. "
            "Please provide your final verdict now using the finish action."
        )})
        t0 = time.time()
        response = self._chat(messages)
        thought, action, action_input = self._parse_response(response)
        verdict_data = self._parse_finish(action_input if action == "finish" else response)
        steps.append(AgentStep(
            iteration=self.max_iterations + 1,
            thought=thought,
            action="finish",
            action_input=action_input,
            observation="Forced finish after max iterations.",
            elapsed_s=time.time() - t0,
        ))
        return AgentReport(paper_id=paper_id, title=title, model=self.model,
                           total_iterations=len(steps), steps=steps,
                           sources=seen_urls, **verdict_data)

    # ── Private: context builder ───────────────────────────────────────────────

    def _build_paper_context(
        self,
        paper: Paper,
        content: Optional[PaperContent],
    ) -> str:
        """Format the paper into a concise context block for the LLM.

        Caps are deliberate: keeps total prompt under ~3k tokens so there
        is plenty of room for search results in the message history.
        """
        lines = [
            f"TITLE: {paper.title}",
            f"AUTHORS: {', '.join(paper.authors[:4])}",
            f"YEAR: {paper.year or 'unknown'}",
            f"SOURCE: {paper.source}",
            "",
            "ABSTRACT:",
            (paper.abstract or "Not available.")[:600],
        ]

        if content and content.sections:
            SECTION_CAP = 800
            priority = [
                "introduction", "abstract", "conclusion",
                "limitations", "future work", "related work",
                "methodology", "method", "discussion",
            ]
            added: set[str] = set()
            for key in priority:
                for sec_name, sec_text in content.sections.items():
                    if key in sec_name.lower() and sec_name not in added:
                        lines.append(f"\n{sec_name.upper()}:")
                        lines.append(sec_text[:SECTION_CAP])
                        added.add(sec_name)
                        break
        elif content and content.text:
            lines.append("\nFULL TEXT (first 1500 chars):")
            lines.append(content.text[:1500])

        return "\n".join(lines)

    # ── Private: ReAct parser ──────────────────────────────────────────────────

    def _parse_response(self, text: str) -> tuple[str, str, str]:
        """Extract Thought / Action / Action Input from LLM response.

        Finds each keyword boundary then slices between them — avoids lookahead
        quantifier patterns that trip static analysis tools.
        """
        t_m  = re.search(r"Thought\s*:\s*",      text, re.IGNORECASE)
        a_m  = re.search(r"\nAction\s*:\s*",      text, re.IGNORECASE)
        ai_m = re.search(r"\nAction\s*Input\s*:\s*", text, re.IGNORECASE)

        if t_m and a_m and t_m.end() <= a_m.start():
            thought = text[t_m.end():a_m.start()].strip()
        elif t_m:
            thought = text[t_m.end():].strip()[:300]
        else:
            thought = text[:300]

        if a_m and ai_m and a_m.end() <= ai_m.start():
            raw_action = text[a_m.end():ai_m.start()].strip()
        elif a_m:
            raw_action = text[a_m.end():].split("\n")[0].strip()
        else:
            raw_action = "finish"

        action_input = text[ai_m.end():].strip() if ai_m else ""

        # Normalise action name
        action_map = {
            "search_web":   "search_web",
            "search web":   "search_web",
            "search_arxiv": "search_arxiv",
            "search arxiv": "search_arxiv",
            "read_section": "read_section",
            "read section": "read_section",
            "finish":       "finish",
            "done":         "finish",
        }
        action = action_map.get(raw_action.lower().replace("-", "_"), "finish")

        return thought, action, action_input

    def _parse_finish(self, text: str) -> dict:
        """Extract the verdict JSON from a finish action input.

        Falls back gracefully if the LLM produced malformed JSON.
        """
        defaults: dict = {
            "verdict":        "unclear",
            "confidence":     0.5,
            "reasoning":      text.strip(),
            "gaps":           [],
            "directions":     [],
            "competing_work": [],
        }

        # Find the outermost {...} block
        json_m = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_m:
            return defaults

        try:
            data = json.loads(json_m.group())
        except json.JSONDecodeError:
            return defaults

        return {
            "verdict":        str(data.get("verdict", "unclear")),
            "confidence":     max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
            "reasoning":      str(data.get("reasoning", text)),
            "gaps":           [str(g) for g in data.get("gaps", [])],
            "directions":     [str(d) for d in data.get("directions", [])],
            "competing_work": [str(c) for c in data.get("competing_work", [])],
        }

    # ── Private: tool dispatcher ───────────────────────────────────────────────

    def _execute_tool(
        self,
        action: str,
        action_input: str,
        paper: Paper,
        content: Optional[PaperContent],
    ) -> str:
        if action == "search_web":
            return self._tool_search_web(action_input)
        if action == "search_arxiv":
            return self._tool_search_arxiv(action_input)
        if action == "read_section":
            return self._tool_read_section(action_input, paper, content)
        return f"[Unknown tool '{action}' — skipped]"

    def _tool_search_web(self, query: str) -> str:
        try:
            results = search_web(query, max_results=5)
        except Exception as exc:
            return f"[Web search failed: {exc}]"
        if not results:
            return "[No web results found.]"
        parts = []
        for r in results:
            parts.append(
                f"• {r['title']}\n  {r['snippet'][:300]}\n  {r['link']}"
            )
        return "\n\n".join(parts)

    def _tool_search_arxiv(self, query: str) -> str:
        try:
            papers = search_arxiv(query, max_results=8)
        except Exception as exc:
            return f"[arXiv search failed: {exc}]"
        if not papers:
            return "[No arXiv papers found for this query.]"
        parts = []
        for p in papers[:6]:
            authors = ", ".join(p.authors[:2])
            abstract = (p.abstract or "")[:250]
            url = ""
            if p.paper_id and p.paper_id.startswith("arxiv:"):
                url = f"\n  URL: https://arxiv.org/abs/{p.paper_id[6:]}"
            parts.append(
                f"• {p.title} ({p.year})\n  {authors}{url}\n  {abstract}"
            )
        return "\n\n".join(parts)

    def _tool_read_section(
        self,
        section_name: str,
        paper: Paper,
        content: Optional[PaperContent],
    ) -> str:
        target = section_name.lower().strip()

        # Try exact or partial match in parsed sections
        if content and content.sections:
            for name, text in content.sections.items():
                if target in name.lower() or name.lower() in target:
                    return f"[{name}]\n{text[:2000]}"

        # Fall back to full text window
        if content and content.text:
            return f"[full text excerpt]\n{content.text[:2000]}"

        # Last resort: paper abstract from metadata
        return f"[abstract (no full text available)]\n{paper.abstract or 'No abstract.'}"
