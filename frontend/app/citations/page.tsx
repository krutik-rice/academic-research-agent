"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Paper } from "@/lib/types";
import { Btn, Card, ErrorBanner, H2, Select, Spinner } from "@/components/ui";

const STYLES = ["apa", "mla", "bibtex"];

export default function CitationsPage() {
  const [papers, setPapers]     = useState<Paper[]>([]);
  const [selected, setSelected] = useState("");
  const [style, setStyle]       = useState("apa");
  const [citation, setCitation] = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [copied, setCopied]     = useState(false);

  useEffect(() => {
    api.papers.list().then(setPapers).catch(() => {});
  }, []);

  async function handleCite() {
    if (!selected) return;
    setLoading(true);
    setError("");
    setCitation("");
    try {
      const res = await api.papers.cite(selected, style);
      setCitation(res.citation);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(citation);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <H2>Format Citation</H2>

      <Card>
        <div className="space-y-4">
          <div>
            <label className="text-xs mb-1 block" style={{ color: "var(--color-muted)" }}>Paper</label>
            <Select className="w-full" value={selected} onChange={e => setSelected(e.target.value)}>
              <option value="">— select a paper —</option>
              {papers.map(p => (
                <option key={p.paper_id} value={p.paper_id}>
                  {p.paper_id} — {p.title.slice(0, 60)}
                </option>
              ))}
            </Select>
          </div>

          <div className="flex gap-3 items-end">
            <div>
              <label className="text-xs mb-1 block" style={{ color: "var(--color-muted)" }}>Style</label>
              <div className="flex gap-2">
                {STYLES.map(s => (
                  <button
                    key={s}
                    onClick={() => setStyle(s)}
                    className="px-3 py-1.5 rounded text-xs font-medium uppercase"
                    style={{
                      backgroundColor: style === s ? "rgba(138,180,248,0.15)" : "var(--color-surface2)",
                      color: style === s ? "var(--color-accent)" : "var(--color-muted)",
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <Btn onClick={handleCite} loading={loading} disabled={!selected} className="ml-auto">
              {loading ? <Spinner /> : "Format"}
            </Btn>
          </div>
        </div>
      </Card>

      {error && <ErrorBanner message={error} />}

      {citation && (
        <Card>
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--color-accent)" }}>
              {style.toUpperCase()}
            </span>
            <Btn variant="ghost" className="text-xs px-2 py-1" onClick={handleCopy}>
              {copied ? "Copied ✓" : "Copy"}
            </Btn>
          </div>
          <pre
            className="text-xs whitespace-pre-wrap font-mono leading-relaxed"
            style={{ color: "var(--color-text)" }}
          >
            {citation}
          </pre>
        </Card>
      )}
    </div>
  );
}
