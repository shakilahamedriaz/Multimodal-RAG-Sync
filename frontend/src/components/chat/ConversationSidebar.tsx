"use client";

import { useState } from "react";
import { MessageSquarePlus, Trash2, Pencil, Check, X, MessageSquare } from "lucide-react";
import type { ConversationListItem } from "@/lib/api";

interface Props {
  conversations: ConversationListItem[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  loading?: boolean;
}

export function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onRename,
  loading = false,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const startEdit = (conv: ConversationListItem) => {
    setEditingId(conv.id);
    setEditValue(conv.title ?? "");
  };

  const commitEdit = (id: string) => {
    const trimmed = editValue.trim();
    if (trimmed) onRename(id, trimmed);
    setEditingId(null);
  };

  const cancelEdit = () => setEditingId(null);

  return (
    <div className="flex h-full flex-col">
      <div className="p-3">
        <button
          onClick={onNew}
          className="btn-secondary flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm"
        >
          <MessageSquarePlus className="h-4 w-4" />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {loading && (
          <div className="space-y-1.5 p-1">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-9 rounded-lg" />
            ))}
          </div>
        )}

        {!loading && conversations.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-8 text-center text-xs text-fg-subtle">
            <MessageSquare className="h-6 w-6 opacity-40" />
            <span>No conversations yet</span>
          </div>
        )}

        <ul className="space-y-0.5">
          {conversations.map((conv) => (
            <li key={conv.id}>
              {editingId === conv.id ? (
                <div className="flex items-center gap-1 rounded-lg bg-surface-2/80 px-2 py-1.5">
                  <input
                    autoFocus
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitEdit(conv.id);
                      if (e.key === "Escape") cancelEdit();
                    }}
                    className="flex-1 bg-transparent text-xs text-fg focus:outline-none"
                  />
                  <button onClick={() => commitEdit(conv.id)} className="p-0.5 text-accent hover:opacity-80">
                    <Check className="h-3.5 w-3.5" />
                  </button>
                  <button onClick={cancelEdit} className="p-0.5 text-fg-subtle hover:text-fg">
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => onSelect(conv.id)}
                  className={`group flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition ${
                    activeId === conv.id
                      ? "bg-accent/10 text-fg"
                      : "text-fg-muted hover:bg-surface-2/60 hover:text-fg"
                  }`}
                >
                  <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" />
                  <span className="flex-1 truncate">
                    {conv.title || <span className="italic opacity-60">Untitled</span>}
                  </span>
                  <span className="shrink-0 opacity-40">{conv.message_count}</span>
                  <span className="hidden shrink-0 gap-0.5 group-hover:flex">
                    <span
                      role="button"
                      onClick={(e) => { e.stopPropagation(); startEdit(conv); }}
                      className="rounded p-0.5 hover:bg-surface-2 hover:text-fg"
                    >
                      <Pencil className="h-3 w-3" />
                    </span>
                    <span
                      role="button"
                      onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}
                      className="rounded p-0.5 text-red-400/70 hover:bg-surface-2 hover:text-red-400"
                    >
                      <Trash2 className="h-3 w-3" />
                    </span>
                  </span>
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
