"use client";
import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import type { Paper } from "@/lib/types";
import PaperCard from "@/components/PaperCard";
import { Btn, ErrorBanner, H2, InfoBanner, Input, Spinner } from "@/components/ui";

export default function LibraryPage() {
  const [papers, setPapers]         = useState<Paper[]>([]);
  const [filter, setFilter]         = useState("");
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState("");
  const [connStatus, setConnStatus] = useState("");
  const [connLoading, setConnLoading] = useState(false);
  const [bibLog, setBibLog]         = useState("");
  const bibRef                      = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      setPapers(await api.papers.list());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function handleDelete(id: string) {
    await api.papers.delete(id);
    setPapers(prev => prev.filter(p => p.paper_id !== id));
  }

  async function handleConnected() {
    setConnLoading(true);
    setConnStatus("Searching…");
    try {
      for await (const ev of api.papers.connected()) {
        if (ev.type === "progress") setConnStatus(ev.message);
        if (ev.type === "done" && ev.result) {
          const { papers: newPapers, method } = ev.result as { papers: Paper[]; method: string };
          setConnStatus(`Found ${newPapers.length} papers via ${method}`);
          await load();
        }
        if (ev.type === "error") setConnStatus(`Error: ${ev.message}`);
      }
    } finally {
      setConnLoading(false);
    }
  }

  async function handleBib(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBibLog("Importing…");
    try {
      for await (const ev of api.bib.import(file)) {
        if (ev.type === "progress") setBibLog(ev.message);
        if (ev.type === "done" && ev.result) {
          const r = ev.result as { imported: number; skipped: number; not_found: number; total: number };
          setBibLog(`Done — ${r.imported} imported, ${r.skipped} skipped, ${r.not_found} not found`);
          await load();
        }
        if (ev.type === "error") setBibLog(`Error: ${ev.message}`);
      }
    } catch (err) {
      setBibLog(String(err));
    }
  }

  const filtered = papers.filter(p =>
    filter === "" ||
    p.title.toLowerCase().includes(filter.toLowerCase()) ||
    p.paper_id.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <H2>Library ({papers.length})</H2>
        <div className="flex gap-2 flex-wrap">
          <Btn variant="ghost" loading={connLoading} onClick={handleConnected}>
            {connLoading ? <Spinner /> : "Find Connected Papers"}
          </Btn>
          <Btn variant="ghost" onClick={() => bibRef.current?.click()}>Import BibTeX</Btn>
          <input ref={bibRef} type="file" accept=".bib" className="hidden" onChange={handleBib} />
        </div>
      </div>

      {connStatus && <InfoBanner message={connStatus} />}
      {bibLog && <InfoBanner message={bibLog} />}
      {error && <ErrorBanner message={error} />}

      {papers.length > 0 && (
        <Input placeholder="Filter by title or ID…" value={filter} onChange={e => setFilter(e.target.value)} />
      )}

      {loading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : filtered.length === 0 ? (
        <InfoBanner message={papers.length === 0 ? "No papers yet — use Search to add some." : "No papers match your filter."} />
      ) : (
        <div className="space-y-3">
          {filtered.map(p => <PaperCard key={p.paper_id} paper={p} onDelete={handleDelete} />)}
        </div>
      )}
    </div>
  );
}
