"use client";

import { FileText, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import type { SourceCitation } from "@/lib/api";

interface Props {
  sources: SourceCitation[];
}

export function CitationsPanel({ sources }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!sources.length) return null;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">
        Sources ({sources.length})
      </h3>
      <ul className="space-y-2">
        {sources.map((s) => (
          <li key={s.chunk_id} className="rounded-lg border border-gray-100 bg-gray-50">
            <button
              onClick={() => setExpanded(expanded === s.source_index ? null : s.source_index)}
              className="flex w-full items-start justify-between gap-3 px-3 py-2.5 text-left text-sm"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="shrink-0 rounded bg-brand-100 px-1.5 py-0.5 text-xs font-bold text-brand-700">
                  [{s.source_index}]
                </span>
                <FileText className="h-3.5 w-3.5 shrink-0 text-gray-400" />
                <span className="truncate font-medium text-gray-800">{s.filename}</span>
                {s.page_number != null && (
                  <span className="shrink-0 text-xs text-gray-400">p.{s.page_number}</span>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2 text-xs text-gray-400">
                <span title="similarity score">
                  {s.rerank_score != null
                    ? `rerank: ${s.rerank_score.toFixed(3)}`
                    : `sim: ${s.similarity_score.toFixed(3)}`}
                </span>
                {expanded === s.source_index ? (
                  <ChevronUp className="h-3.5 w-3.5" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5" />
                )}
              </div>
            </button>
            {expanded === s.source_index && (
              <div className="border-t border-gray-100 px-3 pb-3 pt-2">
                <p className="text-xs leading-relaxed text-gray-600 italic">{s.excerpt}</p>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
