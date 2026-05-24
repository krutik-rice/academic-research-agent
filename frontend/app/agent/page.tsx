"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentReport, AgentStep, Paper } from "@/lib/types";
import { Btn, Card, ErrorBanner, H2, InfoBanner, ProgressBar, Select, Spinner } from "@/components/ui";

const VERDICT_STYLE: Record<string, { color: string; label: string }> = {
  worth_pursuing:    { color: "var(--color-success)", label: "Worth Pursuing ✓" },
  partially_covered: { color: "var(--color-accent)",  label: "Partially Covered" },
  well_covered:      { color: "var(--color-danger)",  label: "Well Covered ✗" },
  unclear:           { color: "var(--color-warn)",    label: "Unclear" },
};

const ACTION_COLOR: Record<string, string> = {
  search_web:   "rgba(37,99,235,0.25)",
  search_arxiv: "rgba(185,28,28,0.25)",
  read_section: "rgba(67,56,202,0.25)",
  finish:       "rgba(129,201,149,0.2)",
};

export default function AgentPage() {
  const [papers, setPapers]       = useState<Paper[]>([]);
  const [models, setModels]       = useState<string[]>([]);
  const [ollamaOk, setOllamaOk]   = useState(false);
  const [selected, setSelected]   = useState("");
  const [model, setModel]         = useState("llama3.1");
  const [iters, setIters]         = useState(5);
  const [running, setRunning]     = useState(false);
  const [progress, setProgress]   = useState(0);
  const [statusMsg, setStatusMsg] = useState("");
  const [report, setReport]       = useState<AgentReport | null>(null);
  const [error, setError]         = useState("");
  const [pulling, setPulling]     = useState(false);
  const [pullMsg, setPullMsg]     = useState("");
  const [pullPct, setPullPct]     = useState(0);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [saved, setSaved]         = useState(false);

  useEffect(() => {
    Promise.all([api.papers.list(), api.agent.status()])
      .then(([p, s]) => {
        setPapers(p);
        setOllamaOk(s.available);
        setModels(s.models);
        if (s.models.length > 0) setModel(s.models[0]);
      })
      .catch(() => {});
  }, []);

  const modelReady = models.some(m => m.includes(model));

  async function handlePull() {
    setPulling(true);
    setPullMsg("Starting…");
    setPullPct(0);
    try {
      for await (const ev of api.agent.pull(model)) {
        if (ev.type === "progress") {
          const e = ev as { type: string; status?: string; completed?: number; total?: number; message?: string };
          if (e.total && e.completed) {
            const pct = e.completed / e.total;
            const mb = Math.round((e.completed ?? 0) / 1024 / 1024);
            const tot = Math.round((e.total ?? 0) / 1024 / 1024);
            setPullPct(pct);
            setPullMsg(`${e.status} — ${mb} / ${tot} MB`);
          } else {
            setPullMsg(ev.message ?? "");
          }
        }
        if (ev.type === "done") {
          setPullMsg("Model ready.");
          const s = await api.agent.status();
          setModels(s.models);
          setOllamaOk(s.available);
        }
        if (ev.type === "error") setPullMsg(`Error: ${ev.message}`);
      }
    } finally {
      setPulling(false);
    }
  }

  async function handleRun() {
    if (!selected) return;
    setRunning(true);
    setError("");
    setReport(null);
    setProgress(0);
    setSaved(false);
    try {
      for await (const ev of api.agent.run(selected, model, iters)) {
        if (ev.type === "progress") {
          const e = ev as { type: string; current?: number; total?: number; message: string };
          setStatusMsg(e.message);
          if (e.total) setProgress((e.current ?? 0) / e.total);
        }
        if (ev.type === "done" && ev.report) setReport(ev.report);
        if (ev.type === "error") setError(ev.message);
      }
    } finally {
      setRunning(false);
      setProgress(1);
    }
  }

  async function handleSave() {
    if (!report) return;
    await api.summaries.save(report.paper_id, {
      summary: report.reasoning,
      limitations: report.gaps,
      future_directions: report.directions,
    });
    setSaved(true);
  }

  const verdict = report ? (VERDICT_STYLE[report.verdict] ?? { color: "var(--color-muted)", label: report.verdict }) : null;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <H2>Research Viability Agent</H2>

      {/* How it works */}
      <details className="rounded-xl border px-4 py-3 text-xs cursor-pointer" style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}>
        <summary className="font-medium" style={{ color: "var(--color-text)" }}>How this agent works</summary>
        <div className="mt-3 space-y-1">
          <p><strong>ReAct (Reason + Act)</strong> — each iteration: Thought → Action → Observation.</p>
          <p>Tools: <code>read_section</code> · <code>search_web</code> · <code>search_arxiv</code> · <code>finish</code></p>
          <p>The agent revisits the same paper multiple times, each re-read informed by web and arXiv searches.</p>
          <p>Verdict: <code>worth_pursuing</code> · <code>partially_covered</code> · <code>well_covered</code> · <code>unclear</code></p>
        </div>
      </details>

      {/* Ollama status */}
      <div className="flex items-center gap-2 text-xs">
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: ollamaOk ? "var(--color-success)" : "var(--color-danger)" }}
        />
        <span style={{ color: "var(--color-muted)" }}>
          Ollama {ollamaOk ? "online" : "offline"}
          {models.length > 0 && ` · ${models.join(", ")}`}
        </span>
      </div>

      {/* Model pull */}
      {ollamaOk && !modelReady && (
        <Card>
          <p className="text-sm mb-3" style={{ color: "var(--color-text)" }}>
            Model <strong>{model}</strong> is not downloaded yet (~4 GB).
          </p>
          {pullMsg && (
            <div className="mb-3 space-y-1">
              <p className="text-xs" style={{ color: "var(--color-muted)" }}>{pullMsg}</p>
              {pullPct > 0 && <ProgressBar value={pullPct} />}
            </div>
          )}
          <Btn variant="ghost" loading={pulling} onClick={handlePull}>
            {pulling ? <Spinner /> : `Download ${model}`}
          </Btn>
        </Card>
      )}

      {/* Config */}
      {papers.length === 0 ? (
        <InfoBanner message="Add papers to your library first via Search." />
      ) : (
        <Card>
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="sm:col-span-2">
                <label className="text-xs mb-1 block" style={{ color: "var(--color-muted)" }}>Paper</label>
                <Select className="w-full" value={selected} onChange={e => setSelected(e.target.value)}>
                  <option value="">— select —</option>
                  {papers.map(p => <option key={p.paper_id} value={p.paper_id}>{p.paper_id} — {p.title.slice(0, 50)}</option>)}
                </Select>
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: "var(--color-muted)" }}>Model</label>
                {models.length > 0 ? (
                  <Select className="w-full" value={model} onChange={e => setModel(e.target.value)}>
                    {models.map(m => <option key={m}>{m}</option>)}
                  </Select>
                ) : (
                  <input
                    className="w-full px-3 py-2 rounded-lg text-sm border"
                    style={{ backgroundColor: "var(--color-surface2)", color: "var(--color-text)", borderColor: "var(--color-border)" }}
                    value={model}
                    onChange={e => setModel(e.target.value)}
                  />
                )}
              </div>
            </div>
            <div className="flex items-center gap-4">
              <label className="text-xs flex items-center gap-2" style={{ color: "var(--color-muted)" }}>
                Iterations: <strong style={{ color: "var(--color-text)" }}>{iters}</strong>
                <input type="range" min={3} max={8} value={iters} onChange={e => setIters(Number(e.target.value))} className="w-24 accent-blue-400" />
              </label>
              <Btn className="ml-auto" loading={running} disabled={!selected || !ollamaOk} onClick={handleRun}>
                {running ? <Spinner /> : "Run Agent"}
              </Btn>
            </div>
            {running && (
              <div>
                <ProgressBar value={progress} />
                <p className="text-xs mt-1" style={{ color: "var(--color-muted)" }}>{statusMsg}</p>
              </div>
            )}
          </div>
        </Card>
      )}

      {error && <ErrorBanner message={error} />}

      {/* Report */}
      {report && verdict && (
        <div className="space-y-4">
          <div className="h-px" style={{ backgroundColor: "var(--color-border)" }} />

          {/* Verdict card */}
          <Card>
            <div className="flex items-center gap-4 mb-3 flex-wrap">
              <span className="text-lg font-semibold" style={{ color: verdict.color }}>{verdict.label}</span>
              <span className="text-sm" style={{ color: "var(--color-muted)" }}>
                {Math.round(report.confidence * 100)}% confidence
              </span>
              <span className="text-sm" style={{ color: "var(--color-muted)" }}>
                {report.total_iterations} iterations · {report.model}
              </span>
            </div>
            <ProgressBar value={report.confidence} className="mb-4" />
            <p className="text-sm" style={{ color: "var(--color-text)" }}>{report.reasoning}</p>
          </Card>

          {/* Gaps + directions */}
          {(report.gaps.length > 0 || report.directions.length > 0) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {report.gaps.length > 0 && (
                <Card>
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-accent)" }}>Open Gaps</h4>
                  <ul className="space-y-1">
                    {report.gaps.map((g, i) => <li key={i} className="text-xs" style={{ color: "var(--color-muted)" }}>· {g}</li>)}
                  </ul>
                </Card>
              )}
              {report.directions.length > 0 && (
                <Card>
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-accent)" }}>Directions</h4>
                  <ul className="space-y-1">
                    {report.directions.map((d, i) => <li key={i} className="text-xs" style={{ color: "var(--color-muted)" }}>· {d}</li>)}
                  </ul>
                </Card>
              )}
            </div>
          )}

          {/* Competing work */}
          {report.competing_work.length > 0 && (
            <Card>
              <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-accent)" }}>Competing / Related Work</h4>
              <ul className="space-y-1">
                {report.competing_work.map((c, i) => <li key={i} className="text-xs" style={{ color: "var(--color-muted)" }}>· {c}</li>)}
              </ul>
            </Card>
          )}

          {/* Sources */}
          {report.sources.length > 0 && (
            <Card>
              <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-accent)" }}>Sources Checked</h4>
              <p className="text-xs mb-2" style={{ color: "var(--color-muted)" }}>
                Real URLs returned by search tools — click to verify any claim.
              </p>
              <ul className="space-y-1">
                {report.sources.map((url, i) => (
                  <li key={i} className="text-xs truncate">
                    <a href={url} target="_blank" rel="noreferrer" style={{ color: "var(--color-accent)" }}>
                      {url.replace(/^https?:\/\//, "")}
                    </a>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Step trace */}
          <div>
            <h4 className="text-sm font-semibold mb-3" style={{ color: "var(--color-text)" }}>Agent Trace</h4>
            <div className="space-y-2">
              {report.steps.map((step: AgentStep) => (
                <div key={step.iteration} className="rounded-xl border" style={{ borderColor: "var(--color-border)" }}>
                  <button
                    className="w-full flex items-center gap-3 px-4 py-3 text-left text-xs"
                    onClick={() => setExpandedStep(expandedStep === step.iteration ? null : step.iteration)}
                  >
                    <span className="font-mono" style={{ color: "var(--color-muted)" }}>#{step.iteration}</span>
                    <span
                      className="px-2 py-0.5 rounded text-xs"
                      style={{ backgroundColor: ACTION_COLOR[step.action] ?? "rgba(138,180,248,0.15)", color: "var(--color-text)" }}
                    >
                      {step.action}
                    </span>
                    <span className="flex-1 truncate" style={{ color: "var(--color-muted)" }}>{step.action_input.slice(0, 60)}</span>
                    <span style={{ color: "var(--color-muted)" }}>{step.elapsed_s.toFixed(1)}s</span>
                    <span style={{ color: "var(--color-muted)" }}>{expandedStep === step.iteration ? "▲" : "▼"}</span>
                  </button>
                  {expandedStep === step.iteration && (
                    <div className="px-4 pb-4 space-y-3 border-t" style={{ borderColor: "var(--color-border)" }}>
                      <div>
                        <p className="text-xs font-semibold mt-3 mb-1" style={{ color: "var(--color-accent)" }}>Thought</p>
                        <p className="text-xs" style={{ color: "var(--color-muted)" }}>{step.thought}</p>
                      </div>
                      <div>
                        <p className="text-xs font-semibold mb-1" style={{ color: "var(--color-accent)" }}>Action Input</p>
                        <pre className="text-xs whitespace-pre-wrap" style={{ color: "var(--color-muted)" }}>{step.action_input}</pre>
                      </div>
                      <div>
                        <p className="text-xs font-semibold mb-1" style={{ color: "var(--color-accent)" }}>Observation</p>
                        <pre className="text-xs whitespace-pre-wrap" style={{ color: "var(--color-muted)" }}>{step.observation.slice(0, 800)}</pre>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Save */}
          <div className="flex gap-3">
            <Btn variant="ghost" onClick={handleSave} disabled={saved}>
              {saved ? "Saved ✓" : "Save to Library"}
            </Btn>
            <Btn variant="ghost" onClick={() => setReport(null)}>Clear</Btn>
          </div>
        </div>
      )}
    </div>
  );
}
