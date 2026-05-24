"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisStatus, Paper, PaperSummary, ResearchGapsResult } from "@/lib/types";
import { Btn, Card, ErrorBanner, H2, InfoBanner, ProgressBar, Select, Spinner } from "@/components/ui";

export default function AnalyzePage() {
  const [papers, setPapers]         = useState<Paper[]>([]);
  const [statuses, setStatuses]     = useState<AnalysisStatus[]>([]);
  const [selected, setSelected]     = useState("");
  const [summary, setSummary]       = useState<PaperSummary | null>(null);
  const [analyzing, setAnalyzing]   = useState(false);
  const [gapsLoading, setGapsLoading] = useState(false);
  const [gapsResult, setGapsResult] = useState<ResearchGapsResult | null>(null);
  const [gapsMsg, setGapsMsg]       = useState("");
  const [error, setError]           = useState("");
  const [overlap, setOverlap]       = useState(0.75);

  useEffect(() => {
    Promise.all([api.papers.list(), api.analysis.status()])
      .then(([p, s]) => { setPapers(p); setStatuses(s); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.summaries.get(selected).then(s => setSummary(s)).catch(() => {});
  }, [selected]);

  async function handleAnalyze() {
    if (!selected) return;
    setAnalyzing(true);
    setError("");
    try {
      await api.papers.analyze(selected);
      const [s, status] = await Promise.all([
        api.summaries.get(selected),
        api.analysis.status(),
      ]);
      setSummary(s);
      setStatuses(status);
    } catch (e) {
      setError(String(e));
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleGaps() {
    setGapsLoading(true);
    setGapsMsg("Starting…");
    setGapsResult(null);
    try {
      for await (const ev of api.analysis.gaps(overlap)) {
        if (ev.type === "progress") setGapsMsg(ev.message);
        if (ev.type === "done" && ev.result) setGapsResult(ev.result as ResearchGapsResult);
        if (ev.type === "error") setGapsMsg(`Error: ${ev.message}`);
      }
    } finally {
      setGapsLoading(false);
    }
  }

  const analyzed = statuses.filter(s => s.analyzed).length;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <H2>Analyze Papers</H2>

      {/* Progress tracker */}
      <Card>
        <div className="flex justify-between text-xs mb-2" style={{ color: "var(--color-muted)" }}>
          <span>Analysis progress</span>
          <span>{analyzed} / {statuses.length} analyzed</span>
        </div>
        <ProgressBar value={statuses.length ? analyzed / statuses.length : 0} />
        <div className="mt-3 space-y-1">
          {statuses.map(s => (
            <div key={s.paper_id} className="flex items-center gap-2 text-xs">
              <span style={{ color: s.analyzed ? "var(--color-success)" : "var(--color-muted)" }}>
                {s.analyzed ? "✓" : "○"}
              </span>
              <span className="truncate flex-1" style={{ color: "var(--color-muted)" }}>{s.title}</span>
              {s.analyzed && (
                <span style={{ color: "var(--color-muted)" }}>
                  {s.lim_count} lim · {s.fut_count} fut
                </span>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Single paper analysis */}
      <Card>
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="text-xs mb-1 block" style={{ color: "var(--color-muted)" }}>Paper to analyze</label>
            <Select className="w-full" value={selected} onChange={e => setSelected(e.target.value)}>
              <option value="">— select —</option>
              {papers.map(p => <option key={p.paper_id} value={p.paper_id}>{p.paper_id} — {p.title.slice(0, 55)}</option>)}
            </Select>
          </div>
          <Btn onClick={handleAnalyze} loading={analyzing} disabled={!selected}>
            {analyzing ? <Spinner /> : "Analyze"}
          </Btn>
        </div>
      </Card>

      {error && <ErrorBanner message={error} />}

      {summary && (
        <Card>
          <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--color-text)" }}>{summary.title}</h3>
          {summary.limitations.length > 0 && (
            <Section title="Limitations" items={summary.limitations} />
          )}
          {summary.future_directions.length > 0 && (
            <Section title="Future Directions" items={summary.future_directions} />
          )}
          {summary.key_findings.length > 0 && (
            <Section title="Key Findings" items={summary.key_findings} />
          )}
          {summary.summary && (
            <div className="mt-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--color-accent)" }}>Summary</h4>
              <p className="text-xs" style={{ color: "var(--color-muted)" }}>{summary.summary}</p>
            </div>
          )}
        </Card>
      )}

      {/* Research gaps */}
      <div className="border-t pt-6" style={{ borderColor: "var(--color-border)" }}>
        <div className="flex items-center justify-between gap-4 mb-4 flex-wrap">
          <h3 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Find Research Gaps</h3>
          <div className="flex items-center gap-3">
            <label className="text-xs" style={{ color: "var(--color-muted)" }}>
              Overlap threshold: {Math.round(overlap * 100)}%
              <input
                type="range" min={0.25} max={1} step={0.05}
                value={overlap}
                onChange={e => setOverlap(Number(e.target.value))}
                className="ml-2 w-24 accent-blue-400"
              />
            </label>
            <Btn variant="ghost" loading={gapsLoading} onClick={handleGaps}>
              {gapsLoading ? <Spinner /> : "Find Gaps"}
            </Btn>
          </div>
        </div>
        {gapsMsg && !gapsResult && <InfoBanner message={gapsMsg} />}
        {gapsResult && (
          <div className="space-y-3">
            <p className="text-xs" style={{ color: "var(--color-muted)" }}>
              {gapsResult.analyzed_count} papers analyzed · {gapsResult.skipped_count} skipped
            </p>
            {gapsResult.themes.length === 0 ? (
              <InfoBanner message="No common themes found at this threshold — try lowering it." />
            ) : (
              gapsResult.themes.map((t, i) => (
                <Card key={i}>
                  <div className="flex justify-between items-start gap-2">
                    <span className="text-sm font-medium" style={{ color: "var(--color-text)" }}>{t.theme}</span>
                    <span className="text-xs shrink-0" style={{ color: "var(--color-muted)" }}>
                      {t.frequency} papers
                    </span>
                  </div>
                </Card>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ title, items }: Readonly<{ title: string; items: string[] }>) {
  return (
    <div className="mb-3">
      <h4 className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--color-accent)" }}>{title}</h4>
      <ul className="space-y-0.5">
        {items.map((item, i) => (
          <li key={i} className="text-xs flex gap-1.5" style={{ color: "var(--color-muted)" }}>
            <span>·</span><span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
