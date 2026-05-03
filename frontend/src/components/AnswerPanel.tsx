"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Loader2 } from "lucide-react";

interface Props {
  answer: string;
  streaming: boolean;
  hasAnswer: boolean | null;
  noAnswerMessage?: string;
}

export function AnswerPanel({ answer, streaming, hasAnswer, noAnswerMessage }: Props) {
  if (hasAnswer === null && !streaming) return null;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-700">
        {streaming && <Loader2 className="h-4 w-4 animate-spin text-brand-500" />}
        <span>Answer</span>
      </div>

      {hasAnswer === false ? (
        <p className="text-sm text-gray-500 italic">
          {noAnswerMessage ?? "No relevant answer found in the documents."}
        </p>
      ) : (
        <div className="prose prose-sm max-w-none text-gray-800">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
          {streaming && (
            <span className="inline-block h-4 w-0.5 animate-pulse bg-brand-500 align-text-bottom" />
          )}
        </div>
      )}
    </div>
  );
}
