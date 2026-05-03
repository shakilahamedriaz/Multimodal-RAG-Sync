"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, X, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { docApi } from "@/lib/api";

interface UploadItem {
  file: File;
  jobId?: string;
  status: "pending" | "uploading" | "polling" | "done" | "error";
  error?: string;
}

interface Props {
  kbId: string;
  onUploaded: () => void;
}

const ACCEPTED = ".pdf,.docx,.txt,.md,.jpg,.jpeg,.png,.webp,.tiff,.gif";
const MAX_MB = 50;

export function DocumentUploader({ kbId, onUploaded }: Props) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(files: FileList | File[]) {
    const arr = Array.from(files).filter((f) => f.size <= MAX_MB * 1024 * 1024);
    setItems((prev) => [...prev, ...arr.map((file) => ({ file, status: "pending" as const }))]);
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  }, []);

  async function upload() {
    const pending = items.filter((i) => i.status === "pending");
    if (!pending.length) return;

    setItems((prev) =>
      prev.map((i) => (i.status === "pending" ? { ...i, status: "uploading" } : i)),
    );

    try {
      const { job_ids } = await docApi.upload(kbId, pending.map((i) => i.file));

      setItems((prev) => {
        let jobIdx = 0;
        return prev.map((i) =>
          i.status === "uploading"
            ? { ...i, status: "polling", jobId: job_ids[jobIdx++] }
            : i,
        );
      });

      // Poll until all jobs settle
      const poll = async (item: UploadItem): Promise<void> => {
        if (!item.jobId) return;
        for (let attempt = 0; attempt < 60; attempt++) {
          await new Promise((r) => setTimeout(r, 2000));
          const res = await docApi.status(kbId, item.jobId);
          if (res.status === "INDEXED") {
            setItems((prev) =>
              prev.map((i) => (i.jobId === item.jobId ? { ...i, status: "done" } : i)),
            );
            onUploaded();
            return;
          }
          if (res.status === "FAILED") {
            setItems((prev) =>
              prev.map((i) =>
                i.jobId === item.jobId
                  ? { ...i, status: "error", error: res.error ?? "Ingestion failed" }
                  : i,
              ),
            );
            return;
          }
        }
        setItems((prev) =>
          prev.map((i) =>
            i.jobId === item.jobId ? { ...i, status: "error", error: "Timed out" } : i,
          ),
        );
      };

      await Promise.all(
        items
          .filter((i) => i.status === "polling")
          .map((i) => poll(i)),
      );
    } catch (err) {
      setItems((prev) =>
        prev.map((i) =>
          i.status === "uploading"
            ? { ...i, status: "error", error: err instanceof Error ? err.message : "Upload failed" }
            : i,
        ),
      );
    }
  }

  const statusIcon = (item: UploadItem) => {
    if (item.status === "uploading" || item.status === "polling")
      return <Loader2 className="h-4 w-4 animate-spin text-brand-500" />;
    if (item.status === "done")
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    if (item.status === "error")
      return <AlertCircle className="h-4 w-4 text-red-500" title={item.error} />;
    return null;
  };

  const hasPending = items.some((i) => i.status === "pending");

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-sm transition
          ${dragging ? "border-brand-500 bg-brand-50" : "border-gray-300 hover:border-brand-400 hover:bg-gray-50"}`}
      >
        <Upload className="h-8 w-8 text-gray-400" />
        <p className="text-gray-600">
          <span className="font-semibold text-brand-600">Click to upload</span> or drag &amp; drop
        </p>
        <p className="text-xs text-gray-400">PDF, DOCX, TXT, MD, images — max {MAX_MB} MB each</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          className="hidden"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
      </div>

      {items.length > 0 && (
        <ul className="space-y-1 text-sm">
          {items.map((item, i) => (
            <li key={i} className="flex items-center justify-between gap-2 rounded-md border border-gray-100 bg-white px-3 py-2">
              <span className="truncate text-gray-700">{item.file.name}</span>
              <div className="flex items-center gap-2 shrink-0">
                {item.status === "error" && (
                  <span className="text-xs text-red-500">{item.error}</span>
                )}
                {statusIcon(item)}
                {item.status === "pending" && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setItems((prev) => prev.filter((_, j) => j !== i)); }}
                    className="text-gray-400 hover:text-red-500"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {hasPending && (
        <button
          onClick={upload}
          className="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 active:scale-95"
        >
          Upload {items.filter((i) => i.status === "pending").length} file(s)
        </button>
      )}
    </div>
  );
}
