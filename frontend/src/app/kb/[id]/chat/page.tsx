"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Bot, Loader2 } from "lucide-react";
import {
  chatApi,
  streamChatMessage,
  kbApi,
  type KnowledgeBase,
  type ConversationListItem,
  type ChatMessageOut,
  type SourceCitation,
  type SSEEvent,
} from "@/lib/api";
import { ConversationSidebar } from "@/components/chat/ConversationSidebar";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";

export default function ChatPage() {
  const { id: kbId } = useParams<{ id: string }>();

  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageOut[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<(() => void) | null>(null);
  const streamingMsgIdRef = useRef<string | null>(null);

  // Load KB metadata and conversations on mount
  useEffect(() => {
    kbApi.get(kbId).then(setKb).catch(() => {});
    loadConversations();
  }, [kbId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadConversations = async () => {
    setLoadingConvs(true);
    try {
      const convs = await chatApi.listConversations(kbId);
      setConversations(convs);
    } catch {
      // Silently fail; user can retry
    } finally {
      setLoadingConvs(false);
    }
  };

  const selectConversation = async (convId: string) => {
    cancelRef.current?.();
    setActiveConvId(convId);
    setMessages([]);
    setError(null);
    setLoadingMsgs(true);
    try {
      const conv = await chatApi.getConversation(kbId, convId);
      setMessages(conv.messages);
    } catch {
      setError("Failed to load conversation.");
    } finally {
      setLoadingMsgs(false);
    }
  };

  const newConversation = async () => {
    cancelRef.current?.();
    try {
      const conv = await chatApi.createConversation(kbId);
      setConversations((prev) => [
        { id: conv.id, title: conv.title, created_at: conv.created_at, updated_at: conv.updated_at, message_count: 0 },
        ...prev,
      ]);
      setActiveConvId(conv.id);
      setMessages([]);
      setError(null);
    } catch {
      setError("Failed to create conversation.");
    }
  };

  const deleteConversation = async (convId: string) => {
    try {
      await chatApi.deleteConversation(kbId, convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConvId === convId) {
        setActiveConvId(null);
        setMessages([]);
      }
    } catch {
      setError("Failed to delete conversation.");
    }
  };

  const renameConversation = async (convId: string, title: string) => {
    try {
      await chatApi.renameConversation(kbId, convId, title);
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title } : c))
      );
    } catch {
      setError("Failed to rename conversation.");
    }
  };

  const sendMessage = useCallback(
    (content: string) => {
      if (!activeConvId || streaming) return;
      cancelRef.current?.();
      setError(null);

      // Optimistically add user message
      const userMsg: ChatMessageOut = {
        id: `optimistic-user-${Date.now()}`,
        role: "user",
        content,
        sources: null,
        has_answer: null,
        created_at: new Date().toISOString(),
      };

      // Placeholder for streaming assistant message
      const assistantMsgId = `optimistic-assistant-${Date.now()}`;
      streamingMsgIdRef.current = assistantMsgId;
      const assistantMsg: ChatMessageOut = {
        id: assistantMsgId,
        role: "assistant",
        content: "",
        sources: null,
        has_answer: null,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setStreaming(true);

      // Update conversation message count in sidebar
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConvId ? { ...c, message_count: c.message_count + 1 } : c
        )
      );

      cancelRef.current = streamChatMessage(
        kbId,
        activeConvId,
        content,
        (event: SSEEvent) => {
          const sid = streamingMsgIdRef.current;
          if (!sid) return;

          if (event.type === "token" && event.content) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === sid ? { ...m, content: m.content + event.content! } : m
              )
            );
          } else if (event.type === "sources" && event.data) {
            setMessages((prev) =>
              prev.map((m) => (m.id === sid ? { ...m, sources: event.data! } : m))
            );
          } else if (event.type === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === sid ? { ...m, has_answer: event.has_answer ?? true } : m
              )
            );
            setStreaming(false);
            streamingMsgIdRef.current = null;
            // Refresh conversation title if it was auto-generated
            loadConversations();
          } else if (event.type === "error") {
            setError(event.message ?? "An error occurred.");
            setStreaming(false);
            streamingMsgIdRef.current = null;
          }
        },
        () => {
          setStreaming(false);
          streamingMsgIdRef.current = null;
        },
        (err) => {
          setError(err.message);
          setStreaming(false);
          streamingMsgIdRef.current = null;
        },
      );
    },
    [activeConvId, streaming, kbId],
  );

  return (
    <div className="-mx-4 -my-8 flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Sidebar */}
      <div className="flex w-60 shrink-0 flex-col border-r" style={{ borderColor: "var(--line)" }}>
        <div className="flex items-center gap-2 border-b px-3 py-3" style={{ borderColor: "var(--line)" }}>
          <a
            href={`/kb/${kbId}`}
            className="rounded-lg p-1 text-fg-muted transition hover:bg-surface-2 hover:text-fg"
          >
            <ArrowLeft className="h-4 w-4" />
          </a>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-fg">Chat</p>
            {kb && <p className="truncate text-xs text-fg-subtle">{kb.name}</p>}
          </div>
        </div>
        <div className="flex-1 overflow-hidden">
          <ConversationSidebar
            conversations={conversations}
            activeId={activeConvId}
            onSelect={selectConversation}
            onNew={newConversation}
            onDelete={deleteConversation}
            onRename={renameConversation}
            loading={loadingConvs}
          />
        </div>
      </div>

      {/* Chat area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {!activeConvId ? (
          // Empty state
          <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent/10">
              <Bot className="h-7 w-7 text-accent" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-fg">
                {kb ? `${kb.name} Assistant` : "Document Assistant"}
              </h2>
              <p className="mt-1 text-sm text-fg-muted">
                Start a new conversation to ask questions about your documents.
              </p>
            </div>
            <button onClick={newConversation} className="btn-primary px-5 py-2 text-sm">
              Start New Chat
            </button>
          </div>
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4">
              {loadingMsgs ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-fg-subtle" />
                </div>
              ) : messages.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-12 text-center text-sm text-fg-subtle">
                  <Bot className="h-8 w-8 opacity-30" />
                  <p>Send a message to start the conversation.</p>
                </div>
              ) : (
                <div className="mx-auto max-w-3xl space-y-5">
                  {messages.map((msg) => (
                    <ChatMessage
                      key={msg.id}
                      message={msg}
                      streaming={streaming && msg.id === streamingMsgIdRef.current}
                    />
                  ))}
                  <div ref={bottomRef} />
                </div>
              )}
            </div>

            {/* Error */}
            {error && (
              <div className="mx-4 mb-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-400">
                {error}
              </div>
            )}

            {/* Input */}
            <div className="border-t p-3" style={{ borderColor: "var(--line)" }}>
              <div className="mx-auto max-w-3xl">
                <ChatInput
                  onSubmit={sendMessage}
                  disabled={streaming}
                  placeholder="Ask a question about your documents… (Enter to send, Shift+Enter for new line)"
                />
                <p className="mt-1.5 text-center text-xs text-fg-subtle">
                  Answers are grounded in your uploaded documents.
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
