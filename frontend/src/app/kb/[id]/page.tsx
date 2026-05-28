"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Search, MessageSquare, Trash2, Loader2 } from "lucide-react";
import { kbApi, docApi, type KnowledgeBase, type Document } from "@/lib/api";
import { DocumentUploader } from "@/components/DocumentUploader";

const STATUS_COLOR: Record<string, string> = {
  QUEUED: "status-queued",
  PARSING: "status-parsing",
  CHUNKING: "status-chunking",
  EMBEDDING: "status-embedding",
  INDEXED: "status-indexed",
  FAILED: "status-failed",
};

export default function KBDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const [kbData, docsData] = await Promise.all([kbApi.get(id), docApi.list(id)]);
      setKb(kbData);
      setDocs(docsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refresh(); }, [id]);

  async function deleteDoc(docId: string) {
    if (!confirm("Delete this document?")) return;
    await docApi.delete(id, docId);
    setDocs((prev) => prev.filter((d) => d.id !== docId));
  }

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-accent" /></div>;
  if (error) return <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">{error}</div>;
  if (!kb) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <a href="/" className="rounded-lg p-1.5 text-fg-muted transition hover:bg-surface-2 hover:text-fg">
          <ArrowLeft className="h-5 w-5" />
        </a>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-fg">{kb.name}</h1>
          {kb.description && <p className="text-sm text-fg-muted">{kb.description}</p>}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <a href={`/kb/${id}/chat`} className="btn-primary">
            <MessageSquare className="h-4 w-4" /> Chat
          </a>
          <a href={`/kb/${id}/query`} className="btn-secondary">
            <Search className="h-4 w-4" /> Single Query
          </a>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["LLM", kb.llm_model],
          ["Embedding", kb.embedding_model],
          ["Strategy", kb.chunking_strategy],
          ["Documents", String(kb.document_count)],
        ].map(([label, val]) => (
          <div key={label} className="glass p-3 text-center">
            <p className="text-xs text-fg-muted">{label}</p>
            <p className="mt-0.5 truncate font-mono text-sm font-semibold text-accent">{val}</p>
          </div>
        ))}
      </div>

      <div className="glass p-5">
        <h2 className="mb-4 font-semibold tracking-tight text-fg">Upload Documents</h2>
        <DocumentUploader kbId={id} onUploaded={refresh} />
      </div>

      <div className="glass">
        <div className="border-b px-5 py-4">
          <h2 className="font-semibold tracking-tight text-fg">Documents ({docs.length})</h2>
        </div>
        {docs.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-fg-subtle">No documents yet. Upload files above.</p>
        ) : (
          <ul className="divide-y" style={{ borderColor: "var(--line)" }}>
            {docs.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-fg">{doc.filename}</p>
                  <p className="text-xs text-fg-subtle">
                    {doc.chunk_count} chunks
                    {doc.page_count ? ` · ${doc.page_count} pages` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className={`badge ${STATUS_COLOR[doc.status] ?? ""}`}>
                    {doc.status}
                  </span>
                  <button onClick={() => deleteDoc(doc.id)} className="text-fg-subtle transition hover:text-red-400">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
