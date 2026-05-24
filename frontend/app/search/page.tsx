"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Paper } from "@/lib/types";
import PaperCard from "@/components/PaperCard";
import { Btn, Card, ErrorBanner, H2, Input, Select, Spinner } from "@/components/ui";

const SOURCES = ["arxiv", "google_scholar"];

export default function SearchPage() {
  const [query, setQuery]       = useState("");
  const [sources, setSources]   = useState<string[]>([]);
  const [maxRes, setMaxRes]     = useState(8);
  const [results, setResults]   = useState<Paper[]>([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const papers = await api.papers.search(query, sources.length ? sources : undefined, maxRes);
      setResults(papers);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  function toggleSource(s: string) {
    setSources(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <H2>Search Papers</H2>

      <Card>
        <form onSubmit={handleSearch} className="space-y-4">
          <Input
            placeholder="e.g. retrieval augmented generation"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex gap-3">
              {SOURCES.map(s => (
                <label key={s} className="flex items-center gap-1.5 text-xs cursor-pointer" style={{ color: "var(--color-muted)" }}>
                  <input
                    type="checkbox"
                    checked={sources.includes(s)}
                    onChange={() => toggleSource(s)}
                    className="accent-blue-400"
                  />
                  {s}
                </label>
              ))}
            </div>
            <label className="flex items-center gap-2 text-xs ml-auto" style={{ color: "var(--color-muted)" }}>
              Max results
              <Select value={maxRes} onChange={e => setMaxRes(Number(e.target.value))} className="w-16">
                {[5, 8, 10, 15, 20].map(n => <option key={n}>{n}</option>)}
              </Select>
            </label>
            <Btn type="submit" loading={loading}>
              {loading ? <Spinner /> : "Search"}
            </Btn>
          </div>
        </form>
      </Card>

      {error && <ErrorBanner message={error} />}

      {results.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs" style={{ color: "var(--color-muted)" }}>
            {results.length} result{results.length !== 1 ? "s" : ""} — saved to library
          </p>
          {results.map(p => <PaperCard key={p.paper_id} paper={p} />)}
        </div>
      )}
    </div>
  );
}
