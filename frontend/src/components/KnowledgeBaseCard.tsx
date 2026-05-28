"use client";

import { useState } from "react";
import { Trash2, FileText, MessageSquare, Search, ArrowUpRight } from "lucide-react";
import type { KnowledgeBase } from "@/lib/api";
import { kbApi } from "@/lib/api";

interface Props {
  kb: KnowledgeBase;
  onDeleted: (id: string) => void;
}

export function KnowledgeBaseCard({ kb, onDeleted }: Props) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm(`Delete "${kb.name}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await kbApi.delete(kb.id);
      onDeleted(kb.id);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
      setDeleting(false);
    }
  }

  const updatedAt = new Date(kb.updated_at).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });

  return (
    <div className="glass group relative flex animate-fade-in-up flex-col overflow-hidden transition-all duration-200 hover:border-accent/40 hover:shadow-[0_0_24px_-6px_rgb(var(--accent)/0.25)]">
      {/* Top accent bar */}
      <div
        className="h-0.5 w-full opacity-0 transition-opacity duration-200 group-hover:opacity-100"
        style={{
          background: "linear-gradient(90deg, rgb(var(--accent)), rgb(var(--accent-2)))",
        }}
      />

      <div className="flex flex-1 flex-col gap-4 p-5">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="truncate font-semibold tracking-tight text-fg">{kb.name}</h3>
            {kb.description ? (
              <p className="mt-0.5 line-clamp-1 text-xs text-fg-subtle">{kb.description}</p>
            ) : (
              <p className="mt-0.5 text-xs text-fg-subtle italic">No description</p>
            )}
          </div>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="shrink-0 rounded-lg p-1.5 text-fg-subtle opacity-0 transition hover:bg-surface-2 hover:text-red-400 group-hover:opacity-100 disabled:opacity-40"
            title="Delete"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Stats */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs text-fg-muted" style={{ borderColor: "var(--line)" }}>
            <FileText className="h-3 w-3 text-accent" />
            {kb.document_count} doc{kb.document_count !== 1 ? "s" : ""}
          </span>
          <span className="rounded-md border px-2 py-1 font-mono text-xs text-fg-subtle" style={{ borderColor: "var(--line)" }}>
            {kb.llm_model.replace("claude-", "").replace("-20251001", "")}
          </span>
          <span className="rounded-md border px-2 py-1 font-mono text-xs text-fg-subtle" style={{ borderColor: "var(--line)" }}>
            {kb.chunking_strategy}
          </span>
        </div>

        {/* Updated at */}
        <p className="text-xs text-fg-subtle">Updated {updatedAt}</p>

        {/* Action buttons */}
        <div className="flex gap-2 border-t pt-3" style={{ borderColor: "var(--line)" }}>
          <a
            href={`/kb/${kb.id}/chat`}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent transition hover:bg-accent/20"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            Chat
          </a>
          <a
            href={`/kb/${kb.id}/query`}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium text-fg-muted transition hover:border-accent/40 hover:text-fg"
            style={{ borderColor: "var(--line)" }}
          >
            <Search className="h-3.5 w-3.5" />
            Query
          </a>
          <a
            href={`/kb/${kb.id}`}
            className="flex items-center justify-center rounded-lg border px-2 py-1.5 text-fg-subtle transition hover:border-accent/40 hover:text-fg"
            style={{ borderColor: "var(--line)" }}
            title="Open KB"
          >
            <ArrowUpRight className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}
