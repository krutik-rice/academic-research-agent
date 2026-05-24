"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { GraphData } from "@/lib/types";
import { Btn, ErrorBanner, H2, InfoBanner, Spinner } from "@/components/ui";

export default function GraphPage() {
  const [data, setData]     = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await api.graph.get());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  return (
    <div className="space-y-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <H2>Paper Similarity Graph</H2>
        <Btn variant="ghost" loading={loading} onClick={load}>
          {loading ? <Spinner /> : "Refresh"}
        </Btn>
      </div>

      {data && (
        <p className="text-xs" style={{ color: "var(--color-muted)" }}>
          {data.node_count} papers · {data.edge_count} connections
        </p>
      )}

      {error && <ErrorBanner message={error} />}

      {loading && !data && (
        <div className="flex justify-center py-20"><Spinner /></div>
      )}

      {data && data.node_count === 0 && (
        <InfoBanner message="No papers in library yet — add some via Search first." />
      )}

      {data && data.node_count > 0 && (
        <div className="flex-1 rounded-xl overflow-hidden border" style={{ borderColor: "var(--color-border)", minHeight: 520 }}>
          <iframe
            srcDoc={data.html}
            className="w-full h-full"
            style={{ minHeight: 520, border: "none", backgroundColor: "var(--color-surface)" }}
            title="Paper similarity graph"
          />
        </div>
      )}
    </div>
  );
}
