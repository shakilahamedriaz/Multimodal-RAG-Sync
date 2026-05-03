"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { kbApi, streamQuery, type KnowledgeBase, type SourceCitation } from "@/lib/api";
import { QueryInput } from "@/components/QueryInput";
import { AnswerPanel } from "@/components/AnswerPanel";
import { CitationsPanel } from "@/components/CitationsPanel";

export default function QueryPage() {
  const { id } = useParams<{ id: string }>();
  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<SourceCitation[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [hasAnswer, setHasAnswer] = useState<boolean | null>(null);
  const [noAnswerMsg, setNoAnswerMsg] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    kbApi.get(id).then(setKb).catch(() => {});
  }, [id]);

  const handleQuery = useCallback(
    (query: string, opts: { topK: number; rerankN: number; alpha: number }) => {
      cancelRef.current?.();
      setAnswer("");
      setSources([]);
      setHasAnswer(null);
      setNoAnswerMsg(undefined);
      setError(null);
      setStreaming(true);

      cancelRef.current = streamQuery(
        id,
        { query, top_k: opts.topK, rerank_n: opts.rerankN, alpha: opts.alpha, stream: true },
        (event) => {
          if (event.type === "token" && event.content) {
            setAnswer((prev) => prev + event.content);
          } else if (event.type === "sources" && event.data) {
            setSources(event.data);
          } else if (event.type === "no_answer") {
            setHasAnswer(false);
            setNoAnswerMsg(event.message);
            setStreaming(false);
          } else if (event.type === "done") {
            setHasAnswer(event.has_answer ?? true);
            setStreaming(false);
          } else if (event.type === "error") {
            setError(event.message ?? "Unknown error");
            setStreaming(false);
          }
        },
        () => setStreaming(false),
        (err) => { setError(err.message); setStreaming(false); },
      );
    },
    [id],
  );

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <a href={`/kb/${id}`} className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </a>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Query</h1>
          {kb && <p className="text-sm text-gray-500">{kb.name}</p>}
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <QueryInput onSubmit={handleQuery} disabled={streaming} />
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <AnswerPanel
        answer={answer}
        streaming={streaming}
        hasAnswer={hasAnswer}
        noAnswerMessage={noAnswerMsg}
      />

      <CitationsPanel sources={sources} />
    </div>
  );
}
