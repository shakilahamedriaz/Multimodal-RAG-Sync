"use client";

import { useState } from "react";
import { Trash2, Database, FileText } from "lucide-react";
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

  return (
    <a
      href={`/kb/${kb.id}`}
      className="group relative flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition hover:border-brand-500 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 shrink-0 text-brand-600" />
          <h3 className="font-semibold text-gray-900 group-hover:text-brand-700">{kb.name}</h3>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="rounded p-1 text-gray-400 opacity-0 transition hover:text-red-500 group-hover:opacity-100 disabled:opacity-50"
          title="Delete knowledge base"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {kb.description && (
        <p className="line-clamp-2 text-sm text-gray-500">{kb.description}</p>
      )}

      <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <FileText className="h-3.5 w-3.5" />
          {kb.document_count} doc{kb.document_count !== 1 ? "s" : ""}
        </span>
        <span className="rounded bg-gray-100 px-2 py-0.5 font-mono">{kb.llm_model}</span>
        <span className="rounded bg-gray-100 px-2 py-0.5 font-mono">{kb.chunking_strategy}</span>
      </div>
    </a>
  );
}
