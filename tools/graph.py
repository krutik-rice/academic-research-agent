"""Paper similarity graph — builds vis.js node/edge data and renders HTML."""

from __future__ import annotations

import json
import math
import re

from tools.search import Paper

_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "have",
    "has", "been", "not", "all", "more", "but", "however", "thus", "therefore",
    "while", "when", "where", "such", "their", "which", "also", "can", "may",
    "our", "we", "use", "used", "uses", "show", "shown", "only", "these",
    "paper", "work", "model", "method", "approach", "results", "data", "using",
    "propose", "present", "proposed", "based", "between", "both", "other",
    "does", "each", "into", "well", "its",
}

_SOURCE_COLOR = {
    "arxiv":            "#b91c1c",
    "google_scholar":   "#2563eb",
    "semantic_scholar": "#4338ca",
}


def build_graph(papers: list[Paper], threshold: float = 0.12) -> dict:
    """Return {nodes, edges} for a vis.js network.

    Edges connect papers whose combined title+abstract keyword sets have
    Jaccard similarity >= threshold.  Node size scales with citation count.
    """
    if len(papers) < 2:
        return {"nodes": [], "edges": []}

    kw = [_content_words(p.title + " " + (p.abstract or "")[:600]) for p in papers]

    nodes = []
    for i, p in enumerate(papers):
        snippet = (p.abstract or "")[:180].replace("<", "&lt;").replace(">", "&gt;")
        if len(p.abstract or "") > 180:
            snippet += "…"
        authors = ", ".join(p.authors[:2])
        if len(p.authors) > 2:
            authors += f" +{len(p.authors) - 2} more"
        tooltip = (
            f"<b>{p.title[:110]}</b><br>"
            f"{authors}<br>"
            f"{p.year or 'n/a'} &middot; {p.source.replace('_', ' ')}<br><br>"
            f"{snippet}"
        )
        label = p.title[:44] + "…" if len(p.title) > 44 else p.title
        size  = max(12, min(36, int(12 + math.log1p(p.citation_count or 0) * 3)))
        nodes.append({
            "id":      i,
            "label":   label,
            "tooltip": tooltip,
            "source":  p.source,
            "size":    size,
        })

    edges = []
    for i in range(len(papers)):
        for j in range(i + 1, len(papers)):
            sim = _jaccard(kw[i], kw[j])
            if sim >= threshold:
                edges.append({"from": i, "to": j, "width": max(1, round(sim * 8))})

    return {"nodes": nodes, "edges": edges}


# ── vis.js HTML template ──────────────────────────────────────────────────────

_VIS_HTML = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { height: 100%; background: transparent; overflow: hidden; }
  #g { width: 100%; height: 620px; }
  .vis-tooltip {
    background: #1e1e2e !important;
    color: #cdd6f4 !important;
    border: 1px solid #45475a !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    font-size: 12px !important;
    max-width: 300px !important;
    line-height: 1.5 !important;
    font-family: system-ui, sans-serif !important;
  }
</style>
</head>
<body>
<div id="g"></div>
<script src="https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js"></script>
<script>
(function () {
  var D = __DATA__;
  var C = {
    "arxiv":            "#b91c1c",
    "google_scholar":   "#2563eb",
    "semantic_scholar": "#4338ca"
  };

  var nodes = new vis.DataSet(D.nodes.map(function (n) {
    var c = C[n.source] || "#6b7280";
    return {
      id: n.id,
      label: n.label,
      title: n.tooltip,
      color: {
        background: c,
        border: c,
        highlight: { background: "#f59e0b", border: "#d97706" },
        hover:     { background: "#fbbf24", border: "#f59e0b" }
      },
      font:  { color: "#ffffff", size: 11, face: "system-ui, sans-serif" },
      size:  n.size,
      shape: "dot",
      borderWidth: 2
    };
  }));

  var edges = new vis.DataSet(D.edges.map(function (e) {
    return {
      from:  e.from,
      to:    e.to,
      width: e.width,
      color: {
        color:     "rgba(200,200,200,0.22)",
        highlight: "#f59e0b",
        hover:     "#fbbf24"
      },
      smooth: { enabled: true, type: "dynamic" }
    };
  }));

  new vis.Network(
    document.getElementById("g"),
    { nodes: nodes, edges: edges },
    {
      physics: {
        stabilization: { iterations: 200, updateInterval: 50 },
        barnesHut: {
          gravitationalConstant: -8000,
          centralGravity: 0.3,
          springLength: 160,
          springConstant: 0.04,
          damping: 0.09
        }
      },
      interaction: { hover: true, tooltipDelay: 80, zoomView: true, dragView: true },
      layout: { randomSeed: 42 }
    }
  );
})();
</script>
</body>
</html>
"""


def render_html(graph_data: dict) -> str:
    """Return a self-contained HTML string that renders graph_data as a vis.js network."""
    return _VIS_HTML.replace("__DATA__", json.dumps(graph_data))


# ── text helpers ──────────────────────────────────────────────────────────────

def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"\b[a-z]{3,}\b", text.lower()) if w not in _STOP}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
