"use client";

import { useState } from "react";
import { FileText, ChevronDown, ChevronUp, BookOpen } from "lucide-react";
import type { SourceCitation } from "@/lib/api";

interface Props {
  sources: SourceCitation[];
}

export function CitationsDrawer({ sources }: Props) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!sources.length) return null;

  return (
    <div className="mt-1 w-full max-w-full">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs text-fg-subtle transition hover:bg-surface-2/60 hover:text-fg-muted"
      >
        <BookOpen className="h-3.5 w-3.5" />
        <span>{open ? "Hide" : "Show"} sources ({sources.length})</span>
        {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {open && (
        <div className="mt-1.5 space-y-1.5 rounded-xl border bg-surface/50 p-2" style={{ borderColor: "var(--line)" }}>
          {sources.map((s) => (
            <div key={s.chunk_id} className="rounded-lg border bg-surface-2/50" style={{ borderColor: "var(--line)" }}>
              <button
                onClick={() => setExpanded(expanded === s.source_index ? null : s.source_index)}
                className="flex w-full items-start justify-between gap-3 px-3 py-2 text-left text-xs"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="shrink-0 rounded bg-accent/15 px-1.5 py-0.5 font-mono text-xs font-bold text-accent">
                    [{s.source_index}]
                  </span>
                  <FileText className="h-3 w-3 shrink-0 text-fg-subtle" />
                  <span className="truncate font-medium text-fg">{s.filename}</span>
                  {s.page_number != null && (
                    <span className="shrink-0 text-fg-subtle">p.{s.page_number}</span>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-1.5 text-fg-subtle">
                  <span className="font-mono">
                    {s.rerank_score != null
                      ? `${s.rerank_score.toFixed(3)}`
                      : `${s.similarity_score.toFixed(3)}`}
                  </span>
                  {expanded === s.source_index ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                </div>
              </button>
              {expanded === s.source_index && (
                <div className="border-t px-3 pb-2.5 pt-2" style={{ borderColor: "var(--line)" }}>
                  <p className="text-xs italic leading-relaxed text-fg-muted">{s.excerpt}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
