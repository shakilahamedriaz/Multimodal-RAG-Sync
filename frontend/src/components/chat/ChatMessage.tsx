"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User } from "lucide-react";
import type { ChatMessageOut } from "@/lib/api";
import { CitationsDrawer } from "./CitationsDrawer";

interface Props {
  message: ChatMessageOut;
  streaming?: boolean;
}

export function ChatMessage({ message, streaming = false }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser
            ? "bg-accent/20 text-accent"
            : "bg-accent-2/20 text-accent-2"
        }`}
        style={isUser ? undefined : { color: "rgb(var(--accent-2))", background: "rgb(var(--accent-2) / 0.15)" }}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Bubble */}
      <div className={`flex max-w-[80%] flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "rounded-tr-sm bg-accent/15 text-fg"
              : "rounded-tl-sm bg-surface-2/80 text-fg-muted"
          }`}
          style={{ borderColor: "var(--line)" }}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none text-fg-muted prose-headings:text-fg prose-strong:text-fg prose-a:text-accent prose-code:text-accent">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              {streaming && (
                <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse-glow bg-accent align-text-bottom" />
              )}
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser && message.sources && message.sources.length > 0 && !streaming && (
          <CitationsDrawer sources={message.sources} />
        )}
      </div>
    </div>
  );
}
