"use client";

import { useEffect, useState } from "react";
import {
  Plus, X, Upload, MessageSquare, Search, Zap, FileText,
  Scale, FlaskConical, Building2, Code2, GraduationCap, BookOpen,
  ChevronRight, Layers, Brain, Sparkles,
} from "lucide-react";
import { kbApi, type KnowledgeBase, type CreateKBPayload } from "@/lib/api";
import { KnowledgeBaseCard } from "@/components/KnowledgeBaseCard";

const EMBEDDING_MODELS = [
  "all-MiniLM-L6-v2",
  "all-mpnet-base-v2",
  "BAAI/bge-large-en-v1.5",
  "text-embedding-3-small",
  "text-embedding-3-large",
];
const LLM_MODELS = [
  "claude-haiku-4-5-20251001",
  "claude-sonnet-4-6",
  "claude-opus-4-7",
  "gpt-4o",
  "gpt-4o-mini",
  "ollama/llama3",
];
const CHUNKING_STRATEGIES = ["recursive", "fixed_size", "semantic", "page_level"];

const USE_CASES = [
  {
    icon: Scale,
    title: "Legal & Compliance",
    items: [
      "Query contracts and extract key clauses instantly",
      "Cross-reference regulatory documents",
      "Summarise case law across hundreds of PDFs",
    ],
  },
  {
    icon: FlaskConical,
    title: "Research & Science",
    items: [
      "Chat across entire research paper libraries",
      "Extract methodology and results from studies",
      "Compare findings between multiple papers",
    ],
  },
  {
    icon: Building2,
    title: "Enterprise Knowledge",
    items: [
      "Onboard employees with company policy Q&A",
      "Surface SOPs from internal documentation",
      "Reduce support tickets with instant answers",
    ],
  },
  {
    icon: Code2,
    title: "Engineering Teams",
    items: [
      "Query architecture docs and runbooks",
      "Explore API references conversationally",
      "Keep institutional knowledge searchable",
    ],
  },
  {
    icon: GraduationCap,
    title: "Education",
    items: [
      "Build interactive Q&A over course materials",
      "Let students explore textbooks through chat",
      "Generate assessments from lecture notes",
    ],
  },
  {
    icon: BookOpen,
    title: "Content & Media",
    items: [
      "Search across interview transcripts and notes",
      "Extract quotes and themes from reports",
      "Build structured summaries of long documents",
    ],
  },
];

const HOW_IT_WORKS = [
  {
    step: "01",
    icon: Upload,
    title: "Upload Documents",
    desc: "Drop in PDFs, Word docs, images, or plain text. The pipeline parses, chunks, and indexes everything automatically.",
  },
  {
    step: "02",
    icon: Brain,
    title: "Semantic Indexing",
    desc: "Hybrid retrieval combines dense vector search and BM25 keyword matching — no missed context.",
  },
  {
    step: "03",
    icon: MessageSquare,
    title: "Chat with your Data",
    desc: "Ask questions in plain language. The AI cites exact sources, maintains conversation history, and stays grounded in your documents.",
  },
];

export default function HomePage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<CreateKBPayload>({
    name: "",
    description: "",
    embedding_model: "all-MiniLM-L6-v2",
    llm_model: "claude-haiku-4-5-20251001",
    chunking_strategy: "recursive",
    chunk_size: 512,
    chunk_overlap: 64,
    similarity_threshold: 0.15,
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
    <div className="space-y-24 pb-24">

      {/* ── Hero ───────────────────────────────────────────────────────────────── */}
      <section className="relative pt-6 text-center">
        {/* Background glow */}
        <div
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-72 opacity-20"
          style={{
            background:
              "radial-gradient(ellipse 70% 60% at 50% 0%, rgb(var(--accent)) 0%, transparent 70%)",
          }}
        />

        {/* Eyebrow */}
        <div className="mb-5 inline-flex items-center gap-2 rounded-full border px-3.5 py-1 text-xs font-medium text-fg-muted" style={{ borderColor: "var(--line)" }}>
          <Sparkles className="h-3.5 w-3.5 text-accent" />
          Multimodal RAG · Powered by Claude &amp; pgvector
        </div>

        <h1 className="mx-auto max-w-3xl text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                "linear-gradient(135deg, rgb(var(--fg)) 0%, rgb(var(--accent)) 50%, rgb(var(--accent-2)) 100%)",
            }}
          >
            Your Documents,
          </span>
          <br />
          <span className="text-fg">Intelligently Searchable.</span>
        </h1>

        <p className="mx-auto mt-5 max-w-xl text-base text-fg-muted">
          Upload any document — PDF, Word, image, or markdown. Ask questions in
          natural language. Get answers grounded in your content, with exact
          source citations, streamed in real time.
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <button onClick={() => setShowCreate(true)} className="btn-primary px-5 py-2.5 text-sm">
            <Plus className="h-4 w-4" /> New Knowledge Base
          </button>
          <a href="#how-it-works" className="btn-secondary px-5 py-2.5 text-sm">
            See how it works <ChevronRight className="h-4 w-4" />
          </a>
        </div>

        {/* Capability pills */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-2 text-xs text-fg-subtle">
          {[
            { icon: FileText, label: "PDF · DOCX · Images · Markdown" },
            { icon: Zap,      label: "Hybrid BM25 + Vector Retrieval" },
            { icon: Search,   label: "Cross-encoder Reranking" },
            { icon: Layers,   label: "Multi-turn Conversation Memory" },
          ].map(({ icon: Icon, label }) => (
            <span
              key={label}
              className="flex items-center gap-1.5 rounded-full border px-3 py-1"
              style={{ borderColor: "var(--line)" }}
            >
              <Icon className="h-3 w-3 text-accent" />
              {label}
            </span>
          ))}
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────────────────────── */}
      <section id="how-it-works" className="scroll-mt-20">
        <div className="mb-8 text-center">
          <p className="font-mono text-xs uppercase tracking-widest text-accent">Process</p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-fg">How it works</h2>
        </div>

        <div className="grid grid-cols-1 gap-px sm:grid-cols-3" style={{ background: "var(--line)" }}>
          {HOW_IT_WORKS.map(({ step, icon: Icon, title, desc }) => (
            <div key={step} className="flex flex-col gap-4 bg-bg p-8">
              <div className="flex items-start justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10">
                  <Icon className="h-5 w-5 text-accent" />
                </div>
                <span className="font-mono text-3xl font-black text-fg-subtle/20">{step}</span>
              </div>
              <div>
                <h3 className="font-semibold text-fg">{title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-fg-muted">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Use cases ─────────────────────────────────────────────────────────── */}
      <section>
        <div className="mb-8 text-center">
          <p className="font-mono text-xs uppercase tracking-widest text-accent">Applications</p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-fg">Built for every domain</h2>
          <p className="mt-2 text-sm text-fg-muted">
            One platform, infinite document types — from legal briefs to lab reports.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {USE_CASES.map(({ icon: Icon, title, items }) => (
            <div
              key={title}
              className="glass flex flex-col gap-4 p-5 transition-colors hover:border-accent/40"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-2/10">
                  <Icon className="h-4 w-4" style={{ color: "rgb(var(--accent-2))" }} />
                </div>
                <h3 className="text-sm font-semibold text-fg">{title}</h3>
              </div>
              <ul className="space-y-2">
                {items.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-xs text-fg-muted">
                    <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* ── Knowledge Bases ───────────────────────────────────────────────────── */}
      <section id="knowledge-bases">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-accent">Workspace</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-fg">Your Knowledge Bases</h2>
          </div>
          <button onClick={() => setShowCreate(true)} className="btn-primary text-sm">
            <Plus className="h-4 w-4" /> New KB
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => <div key={i} className="skeleton h-40 rounded-xl" />)}
          </div>
        ) : kbs.length === 0 ? (
          <div
            className="flex flex-col items-center gap-4 rounded-xl border py-16 text-center"
            style={{ borderColor: "var(--line)", borderStyle: "dashed" }}
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-2">
              <Layers className="h-6 w-6 text-fg-subtle" />
            </div>
            <div>
              <p className="text-sm font-medium text-fg">No knowledge bases yet</p>
              <p className="mt-1 text-xs text-fg-subtle">
                Create one above and upload your first document to get started.
              </p>
            </div>
            <button onClick={() => setShowCreate(true)} className="btn-primary text-xs">
              <Plus className="h-3.5 w-3.5" /> Create your first KB
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {kbs.map((kb) => (
              <KnowledgeBaseCard
                key={kb.id}
                kb={kb}
                onDeleted={(id) => setKbs((p) => p.filter((k) => k.id !== id))}
              />
            ))}
          </div>
        )}
      </section>

      {/* ── Create modal ──────────────────────────────────────────────────────── */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="glass w-full max-w-lg animate-fade-in-up shadow-2xl">
            <div className="flex items-center justify-between border-b px-6 py-4" style={{ borderColor: "var(--line)" }}>
              <div>
                <h2 className="font-semibold tracking-tight text-fg">New Knowledge Base</h2>
                <p className="mt-0.5 text-xs text-fg-subtle">Configure your document pipeline</p>
              </div>
              <button onClick={() => setShowCreate(false)} className="rounded-lg p-1.5 text-fg-subtle transition hover:bg-surface-2 hover:text-fg">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4 px-6 py-5">
              <label className="block">
                <span className="text-xs font-medium uppercase tracking-wider text-fg-subtle">Name *</span>
                <input
                  required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="input-field mt-1.5"
                  placeholder="e.g. Legal Contracts Q3"
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium uppercase tracking-wider text-fg-subtle">Description</span>
                <input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="input-field mt-1.5"
                  placeholder="Optional — what's in this KB?"
                />
              </label>

              <div className="grid grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-xs font-medium uppercase tracking-wider text-fg-subtle">LLM Model</span>
                  <select value={form.llm_model} onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
                    className="input-field mt-1.5 font-mono text-xs">
                    {LLM_MODELS.map((m) => <option key={m}>{m}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="text-xs font-medium uppercase tracking-wider text-fg-subtle">Embedding</span>
                  <select value={form.embedding_model} onChange={(e) => setForm({ ...form, embedding_model: e.target.value })}
                    className="input-field mt-1.5 font-mono text-xs">
                    {EMBEDDING_MODELS.map((m) => <option key={m}>{m}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="text-xs font-medium uppercase tracking-wider text-fg-subtle">Chunking</span>
                  <select value={form.chunking_strategy} onChange={(e) => setForm({ ...form, chunking_strategy: e.target.value })}
                    className="input-field mt-1.5 font-mono text-xs">
                    {CHUNKING_STRATEGIES.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="text-xs font-medium uppercase tracking-wider text-fg-subtle">Similarity Threshold</span>
                  <input type="number" min={0} max={1} step={0.05}
                    value={form.similarity_threshold}
                    onChange={(e) => setForm({ ...form, similarity_threshold: Number(e.target.value) })}
                    className="input-field mt-1.5"
                  />
                </label>
              </div>

              <div className="flex justify-end gap-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary text-sm">
                  Cancel
                </button>
                <button type="submit" disabled={creating} className="btn-primary text-sm">
                  {creating ? "Creating…" : "Create Knowledge Base"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
