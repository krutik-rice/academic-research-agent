import type {
  Paper, PaperContent, PaperSummary, PaperAnalysis,
  AnalysisStatus, AgentReport, GraphData, SummaryEntry, SseEvent,
} from "./types";

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

// ── Streaming helper ───────────────────────────────────────────────────────────

async function* stream<T>(
  path: string,
  body?: unknown,
  method = "POST",
): AsyncGenerator<SseEvent<T>> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  if (!res.body) return;

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          yield JSON.parse(line.slice(6)) as SseEvent<T>;
        } catch {
          // malformed line — skip
        }
      }
    }
  }
}

// ── Papers ─────────────────────────────────────────────────────────────────────

export const api = {
  papers: {
    list: () => get<Paper[]>("/papers"),
    search: (query: string, sources?: string[], maxResults = 8) =>
      post<Paper[]>("/papers/search", { query, sources, max_results: maxResults }),
    delete: (id: string) => del(`/papers/${encodeURIComponent(id)}`),
    fetch: (id: string) => post<PaperContent>(`/papers/${encodeURIComponent(id)}/fetch`),
    cite: (id: string, style: string) =>
      get<{ citation: string; style: string }>(
        `/papers/${encodeURIComponent(id)}/cite?style=${style}`
      ),
    analyze: (id: string) => post<PaperAnalysis>(`/papers/${encodeURIComponent(id)}/analyze`),
    connected: (maxNew = 10) =>
      stream<{ papers: Paper[]; method: string }>("/papers/connected", { max_new: maxNew }),
  },

  analysis: {
    status: () => get<AnalysisStatus[]>("/analysis/status"),
    gaps: (overlapFraction = 0.75) =>
      stream("/analysis/gaps", { overlap_fraction: overlapFraction }),
  },

  bib: {
    import: async function* (file: File) {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${BASE}/bib/import`, { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try { yield JSON.parse(line.slice(6)); } catch { /* skip */ }
          }
        }
      }
    },
  },

  graph: {
    get: () => get<GraphData>("/graph"),
  },

  summaries: {
    list: () => get<SummaryEntry[]>("/summaries"),
    get: (id: string) => get<PaperSummary | null>(`/summaries/${encodeURIComponent(id)}`),
    save: (id: string, data: Partial<PaperSummary>) =>
      put<{ ok: boolean }>(`/summaries/${encodeURIComponent(id)}`, data),
  },

  agent: {
    status: () => get<{ available: boolean; models: string[] }>("/agent/status"),
    pull: (model: string) => stream("/agent/pull", { model }),
    run: (paperId: string, model: string, maxIterations: number) =>
      stream<AgentReport>("/agent/run", {
        paper_id: paperId,
        model,
        max_iterations: maxIterations,
      }),
  },
};
