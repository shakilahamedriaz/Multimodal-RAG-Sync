"use client";

import { useState } from "react";
import { Send } from "lucide-react";

interface Props {
  onSubmit: (query: string, opts: { topK: number; rerankN: number; alpha: number }) => void;
  disabled?: boolean;
}

export function QueryInput({ onSubmit, disabled }: Props) {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(20);
  const [rerankN, setRerankN] = useState(5);
  const [alpha, setAlpha] = useState(0.5);
  const [showAdv, setShowAdv] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    onSubmit(q, { topK, rerankN, alpha });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-2">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(e as unknown as React.FormEvent); }}}
          placeholder="Ask a question about your documents…"
          rows={2}
          disabled={disabled}
          className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !query.trim()}
          className="self-end rounded-lg bg-brand-600 p-2.5 text-white transition hover:bg-brand-700 disabled:opacity-40"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>

      <button
        type="button"
        onClick={() => setShowAdv((v) => !v)}
        className="text-xs text-gray-500 hover:text-brand-600"
      >
        {showAdv ? "Hide" : "Show"} advanced options
      </button>

      {showAdv && (
        <div className="grid grid-cols-3 gap-4 rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">Retrieve top-K</span>
            <input
              type="number" min={1} max={100} value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="rounded border border-gray-300 px-2 py-1 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">Rerank N</span>
            <input
              type="number" min={1} max={20} value={rerankN}
              onChange={(e) => setRerankN(Number(e.target.value))}
              className="rounded border border-gray-300 px-2 py-1 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">Dense α ({alpha})</span>
            <input
              type="range" min={0} max={1} step={0.1} value={alpha}
              onChange={(e) => setAlpha(Number(e.target.value))}
              className="mt-1"
            />
          </label>
        </div>
      )}
    </form>
  );
}
