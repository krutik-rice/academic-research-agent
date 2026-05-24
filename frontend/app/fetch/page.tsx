"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Paper, PaperContent } from "@/lib/types";
import { Btn, Card, ErrorBanner, H2, InfoBanner, Select, Spinner } from "@/components/ui";

export default function FetchPage() {
  const [papers, setPapers]   = useState<Paper[]>([]);
  const [selected, setSelected] = useState("");
  const [content, setContent] = useState<PaperContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const [tab, setTab]         = useState("sections");

  useEffect(() => {
    api.papers.list().then(setPapers).catch(() => {});
  }, []);

  async function handleFetch() {
    if (!selected) return;
    setLoading(true);
    setError("");
    setContent(null);
    try {
      setContent(await api.papers.fetch(selected));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const sections = content ? Object.entries(content.sections) : [];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <H2>Fetch Full Text</H2>

      <Card>
        <div className="flex gap-3 items-end">
          <div className="flex-1">
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
          <Btn onClick={handleFetch} loading={loading} disabled={!selected}>
            {loading ? <Spinner /> : "Fetch"}
          </Btn>
        </div>
      </Card>

      {error && <ErrorBanner message={error} />}

      {content && (
        <div className="space-y-4">
          <div className="flex gap-2 text-sm" style={{ color: "var(--color-muted)" }}>
            <span>Method: <strong style={{ color: "var(--color-accent)" }}>{content.method}</strong></span>
            <span>·</span>
            <span>{Object.keys(content.sections).length} sections</span>
            <span>·</span>
            <span>{content.text.length.toLocaleString()} chars</span>
          </div>

          <div className="flex gap-2">
            {["sections", "full"].map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="px-3 py-1 rounded text-xs font-medium"
                style={{
                  backgroundColor: tab === t ? "rgba(138,180,248,0.15)" : "transparent",
                  color: tab === t ? "var(--color-accent)" : "var(--color-muted)",
                }}
              >
                {t === "sections" ? "Sections" : "Full Text"}
              </button>
            ))}
          </div>

          {tab === "sections" && sections.length > 0 ? (
            <div className="space-y-3">
              {sections.map(([name, text]) => (
                <Card key={name}>
                  <h3 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-accent)" }}>
                    {name}
                  </h3>
                  <p className="text-xs whitespace-pre-wrap" style={{ color: "var(--color-muted)" }}>{text}</p>
                </Card>
              ))}
            </div>
          ) : tab === "sections" ? (
            <InfoBanner message="No sections extracted — try Full Text view." />
          ) : (
            <Card>
              <pre className="text-xs whitespace-pre-wrap overflow-auto max-h-[60vh]" style={{ color: "var(--color-muted)" }}>
                {content.text}
              </pre>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
