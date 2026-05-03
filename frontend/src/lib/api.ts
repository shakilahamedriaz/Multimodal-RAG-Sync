const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  embedding_model: string;
  llm_model: string;
  chunking_strategy: string;
  chunk_size: number;
  chunk_overlap: number;
  similarity_threshold: number;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  kb_id: string;
  filename: string;
  mime_type: string;
  status: "QUEUED" | "PARSING" | "CHUNKING" | "EMBEDDING" | "INDEXED" | "FAILED";
  chunk_count: number;
  page_count: number | null;
  created_at: string;
}

export interface SourceCitation {
  source_index: number;
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  excerpt: string;
  similarity_score: number;
  rerank_score: number | null;
}

export interface CreateKBPayload {
  name: string;
  description?: string;
  embedding_model?: string;
  llm_model?: string;
  chunking_strategy?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  similarity_threshold?: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("rag_api_key") : null;
  const headers: Record<string, string> = {
    ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
    ...(init?.headers as Record<string, string> | undefined),
  };

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Knowledge Bases ───────────────────────────────────────────────────────────

export const kbApi = {
  list: () => apiFetch<KnowledgeBase[]>("/kb"),
  get: (id: string) => apiFetch<KnowledgeBase>(`/kb/${id}`),
  create: (payload: CreateKBPayload) =>
    apiFetch<KnowledgeBase>("/kb", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: string, payload: Partial<CreateKBPayload>) =>
    apiFetch<KnowledgeBase>(`/kb/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  delete: (id: string) => apiFetch<void>(`/kb/${id}`, { method: "DELETE" }),
};

// ── Documents ─────────────────────────────────────────────────────────────────

export const docApi = {
  list: (kbId: string) => apiFetch<Document[]>(`/kb/${kbId}/documents`),
  upload: (kbId: string, files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return apiFetch<{ job_ids: string[] }>(`/kb/${kbId}/documents`, {
      method: "POST",
      body: form,
    });
  },
  status: (kbId: string, jobId: string) =>
    apiFetch<{ status: string; doc_id?: string; error?: string }>(`/kb/${kbId}/status/${jobId}`),
  delete: (kbId: string, docId: string) =>
    apiFetch<void>(`/kb/${kbId}/documents/${docId}`, { method: "DELETE" }),
};

// ── Query (SSE streaming) ─────────────────────────────────────────────────────

export interface QueryRequest {
  query: string;
  top_k?: number;
  rerank_n?: number;
  alpha?: number;
  stream?: boolean;
}

export interface SSEEvent {
  type: "token" | "sources" | "done" | "no_answer" | "error";
  content?: string;
  data?: SourceCitation[];
  has_answer?: boolean;
  message?: string;
}

export function streamQuery(
  kbId: string,
  payload: QueryRequest,
  onEvent: (event: SSEEvent) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): () => void {
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("rag_api_key") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
    ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
  };

  const controller = new AbortController();

  fetch(`${BASE}/kb/${kbId}/query`, {
    method: "POST",
    headers,
    body: JSON.stringify({ ...payload, stream: true }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) throw new Error(`${res.status}: query failed`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";
        for (const part of parts) {
          const line = part.replace(/^data:\s*/, "").trim();
          if (!line) continue;
          try {
            const event: SSEEvent = JSON.parse(line);
            onEvent(event);
            if (event.type === "done") onDone();
          } catch {
            // malformed SSE line
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError(err instanceof Error ? err : new Error(String(err)));
    });

  return () => controller.abort();
}
