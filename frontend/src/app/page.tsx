"use client";

import { useEffect, useState } from "react";
import { Plus, X } from "lucide-react";
import { kbApi, type KnowledgeBase, type CreateKBPayload } from "@/lib/api";
import { KnowledgeBaseCard } from "@/components/KnowledgeBaseCard";

const EMBEDDING_MODELS = [
  "text-embedding-3-small",
  "text-embedding-3-large",
  "all-MiniLM-L6-v2",
  "BAAI/bge-large-en-v1.5",
];
const LLM_MODELS = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet-20241022", "ollama/llama3"];
const CHUNKING_STRATEGIES = ["recursive", "fixed_size", "semantic", "page_level"];

export default function HomePage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<CreateKBPayload>({
    name: "",
    description: "",
    embedding_model: "text-embedding-3-small",
    llm_model: "gpt-4o",
    chunking_strategy: "recursive",
    chunk_size: 512,
    chunk_overlap: 64,
    similarity_threshold: 0.3,
  });

  useEffect(() => {
    kbApi.list()
      .then(setKbs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return;
    setCreating(true);
    try {
      const kb = await kbApi.create(form);
      setKbs((prev) => [kb, ...prev]);
      setShowCreate(false);
      setForm({ ...form, name: "", description: "" });
    } catch (err) {
      alert(err instanceof Error ? err.message : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Bases</h1>
          <p className="text-sm text-gray-500">Upload documents and query them with AI</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          <Plus className="h-4 w-4" /> New KB
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-36 animate-pulse rounded-xl bg-gray-200" />
          ))}
        </div>
      ) : kbs.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-20 text-gray-400">
          <span className="text-5xl">📚</span>
          <p className="text-sm">No knowledge bases yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {kbs.map((kb) => (
            <KnowledgeBaseCard key={kb.id} kb={kb} onDeleted={(id) => setKbs((p) => p.filter((k) => k.id !== id))} />
          ))}
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <h2 className="font-semibold text-gray-900">Create Knowledge Base</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4 px-6 py-5">
              <label className="block">
                <span className="text-sm font-medium text-gray-700">Name *</span>
                <input
                  required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  placeholder="My Knowledge Base"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-gray-700">Description</span>
                <input
                  value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                  placeholder="Optional description"
                />
              </label>
              <div className="grid grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-sm font-medium text-gray-700">LLM Model</span>
                  <select value={form.llm_model} onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    {LLM_MODELS.map((m) => <option key={m}>{m}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-gray-700">Embedding Model</span>
                  <select value={form.embedding_model} onChange={(e) => setForm({ ...form, embedding_model: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    {EMBEDDING_MODELS.map((m) => <option key={m}>{m}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-gray-700">Chunking Strategy</span>
                  <select value={form.chunking_strategy} onChange={(e) => setForm({ ...form, chunking_strategy: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    {CHUNKING_STRATEGIES.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-gray-700">Similarity Threshold</span>
                  <input type="number" min={0} max={1} step={0.05}
                    value={form.similarity_threshold}
                    onChange={(e) => setForm({ ...form, similarity_threshold: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowCreate(false)}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                  Cancel
                </button>
                <button type="submit" disabled={creating}
                  className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50">
                  {creating ? "Creating…" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
