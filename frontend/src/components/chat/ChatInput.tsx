"use client";

import { useRef, useEffect, KeyboardEvent } from "react";
import { SendHorizonal } from "lucide-react";

interface Props {
  onSubmit: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSubmit, disabled = false, placeholder = "Ask a question about your documents…" }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled && ref.current) ref.current.focus();
  }, [disabled]);

  const submit = () => {
    const val = ref.current?.value.trim();
    if (!val || disabled) return;
    onSubmit(val);
    if (ref.current) ref.current.value = "";
    resize();
  };

  const resize = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2 rounded-xl border bg-surface-2/60 px-3 py-2.5" style={{ borderColor: "var(--line)" }}>
      <textarea
        ref={ref}
        rows={1}
        onInput={resize}
        onKeyDown={onKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        className="flex-1 resize-none bg-transparent text-sm text-fg placeholder:text-fg-subtle focus:outline-none disabled:opacity-60"
        style={{ minHeight: "24px", maxHeight: "180px" }}
      />
      <button
        onClick={submit}
        disabled={disabled}
        aria-label="Send message"
        className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg btn-primary disabled:opacity-40"
      >
        <SendHorizonal className="h-4 w-4" />
      </button>
    </div>
  );
}
