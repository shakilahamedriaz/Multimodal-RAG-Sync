"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Search, Trash2, Loader2 } from "lucide-react";
import { kbApi, docApi, type KnowledgeBase, type Document } from "@/lib/api";
import { DocumentUploader } from "@/components/DocumentUploader";

const STATUS_COLOR: Record<string, string> = {
  QUEUED: "bg-gray-100 text-gray-600",
  PARSING: "bg-yellow-100 text-yellow-700",
  CHUNKING: "bg-yellow-100 text-yellow-700",
  EMBEDDING: "bg-blue-100 text-blue-700",
  INDEXED: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
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

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-brand-500" /></div>;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>;
  if (!kb) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <a href="/" className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </a>
        <div>
          <h1 className="text-xl font-bold text-gray-900">{kb.name}</h1>
          {kb.description && <p className="text-sm text-gray-500">{kb.description}</p>}
        </div>
        <a
          href={`/kb/${id}/query`}
          className="ml-auto flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
        >
          <Search className="h-4 w-4" /> Query
        </a>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["LLM", kb.llm_model],
          ["Embedding", kb.embedding_model],
          ["Strategy", kb.chunking_strategy],
          ["Documents", String(kb.document_count)],
        ].map(([label, val]) => (
          <div key={label} className="rounded-xl border border-gray-200 bg-white p-3 text-center shadow-sm">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="mt-0.5 truncate text-sm font-semibold text-gray-800">{val}</p>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 font-semibold text-gray-800">Upload Documents</h2>
        <DocumentUploader kbId={id} onUploaded={refresh} />
      </div>

      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-5 py-4">
          <h2 className="font-semibold text-gray-800">Documents ({docs.length})</h2>
        </div>
        {docs.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-gray-400">No documents yet. Upload files above.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {docs.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-800">{doc.filename}</p>
                  <p className="text-xs text-gray-400">
                    {doc.chunk_count} chunks
                    {doc.page_count ? ` · ${doc.page_count} pages` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[doc.status] ?? ""}`}>
                    {doc.status}
                  </span>
                  <button onClick={() => deleteDoc(doc.id)} className="text-gray-400 hover:text-red-500">
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
