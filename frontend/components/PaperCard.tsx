"use client";
import type { Paper } from "@/lib/types";
import { Badge, Btn } from "./ui";

interface Props {
  paper: Paper;
  onDelete?: (id: string) => void;
  actions?: React.ReactNode;
}

export default function PaperCard({ paper, onDelete, actions }: Readonly<Props>) {
  const source = paper.source === "arxiv" ? "arxiv" : paper.source === "semantic_scholar" ? "s2" : "scholar";
  return (
    <div
      className="rounded-xl p-4 border flex flex-col gap-2"
      style={{ backgroundColor: "var(--color-surface)", borderColor: "var(--color-border)" }}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium leading-snug flex-1" style={{ color: "var(--color-text)" }}>
          {paper.title}
        </h3>
        <Badge label={paper.source} variant={source} />
      </div>

      <p className="text-xs" style={{ color: "var(--color-muted)" }}>
        {paper.authors.slice(0, 3).join(", ")}{paper.authors.length > 3 ? " et al." : ""}
        {paper.year ? ` · ${paper.year}` : ""}
        {paper.citation_count > 0 ? ` · ${paper.citation_count} citations` : ""}
      </p>

      {paper.abstract && (
        <p className="text-xs line-clamp-3" style={{ color: "var(--color-muted)" }}>
          {paper.abstract}
        </p>
      )}

      <div className="flex items-center gap-2 mt-1 flex-wrap">
        <span className="text-xs font-mono" style={{ color: "var(--color-muted)" }}>
          {paper.paper_id}
        </span>
        {paper.pdf_url && (
          <a
            href={paper.pdf_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs underline"
            style={{ color: "var(--color-accent)" }}
          >
            PDF
          </a>
        )}
        {actions}
        {onDelete && (
          <Btn variant="danger" className="ml-auto text-xs px-2 py-1" onClick={() => onDelete(paper.paper_id)}>
            Remove
          </Btn>
        )}
      </div>
    </div>
  );
}
