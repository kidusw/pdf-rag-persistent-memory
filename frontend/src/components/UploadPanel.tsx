import { AlertCircle, CheckCircle2, Clock, Loader2, UploadCloud } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";

import { uploadDocument } from "../api/client";
import { useDocumentStore } from "../stores/documentStore";

export const MAX_UPLOAD_MB = 10;

type Row =
  | { key: string; name: string; status: "queued" | "uploading" }
  | { key: string; name: string; status: "indexed"; chunks: number }
  | { key: string; name: string; status: "error"; detail: string };

function rejectionText(r: FileRejection): string {
  const code = r.errors[0]?.code;
  if (code === "file-too-large") return `File exceeds ${MAX_UPLOAD_MB} MB limit`;
  if (code === "file-invalid-type") return "Only PDF files are supported";
  return r.errors[0]?.message ?? "Rejected";
}

export default function UploadPanel() {
  const [rows, setRows] = useState<Row[]>([]);
  const loadDocuments = useDocumentStore((s) => s.loadDocuments);
  const seq = useRef(0);
  // Uploads run one at a time; each drop appends to the same queue.
  const queue = useRef<Promise<void>>(Promise.resolve());

  const setRow = (key: string, row: Row) =>
    setRows((rs) => rs.map((r) => (r.key === key ? row : r)));

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      const fresh: Row[] = [
        ...rejected.map((r): Row => ({
          key: `r${seq.current++}`,
          name: r.file.name,
          status: "error",
          detail: rejectionText(r),
        })),
        ...accepted.map((f): Row => ({ key: `f${seq.current++}`, name: f.name, status: "queued" })),
      ];
      setRows((rs) => [...fresh, ...rs]);

      const jobs = fresh.filter((r) => r.status === "queued");
      jobs.forEach((row, i) => {
        const file = accepted[i];
        queue.current = queue.current.then(async () => {
          setRow(row.key, { ...row, status: "uploading" });
          try {
            const res = await uploadDocument(file);
            const ok = res.results[0];
            const err = res.errors[0];
            setRow(
              row.key,
              ok
                ? { key: row.key, name: ok.filename, status: "indexed", chunks: ok.chunks }
                : { key: row.key, name: row.name, status: "error", detail: err?.detail ?? "Upload failed" },
            );
          } catch (e) {
            setRow(row.key, {
              key: row.key,
              name: row.name,
              status: "error",
              detail: e instanceof Error ? e.message : String(e),
            });
          }
          await loadDocuments();
        });
      });
    },
    [loadDocuments],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxSize: MAX_UPLOAD_MB * 1024 * 1024,
  });

  return (
    <div>
      <div
        {...getRootProps()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
          isDragActive
            ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10"
            : "border-zinc-300 hover:border-zinc-400 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
        }`}
      >
        <input {...getInputProps()} />
        <UploadCloud size={32} className="mb-3 text-indigo-500" />
        <p className="font-medium">{isDragActive ? "Drop to upload" : "Drop PDFs here or click to browse"}</p>
        <p className="mt-1 text-sm text-zinc-500">PDF only · up to {MAX_UPLOAD_MB} MB each</p>
      </div>

      {rows.length > 0 && (
        <ul className="mt-3 divide-y divide-zinc-200 rounded-xl border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {rows.map((r) => (
            <li key={r.key} className="flex items-center gap-3 px-3 py-2 text-sm">
              {r.status === "queued" && <Clock size={16} className="shrink-0 text-zinc-400" />}
              {r.status === "uploading" && (
                <Loader2 size={16} className="shrink-0 animate-spin text-indigo-500" />
              )}
              {r.status === "indexed" && <CheckCircle2 size={16} className="shrink-0 text-emerald-500" />}
              {r.status === "error" && <AlertCircle size={16} className="shrink-0 text-red-500" />}
              <span className="min-w-0 flex-1 truncate">{r.name}</span>
              <span
                className={`shrink-0 text-xs ${r.status === "error" ? "text-red-600 dark:text-red-400" : "text-zinc-500"}`}
              >
                {r.status === "queued" && "Queued"}
                {r.status === "uploading" && "Uploading…"}
                {r.status === "indexed" && `Indexed · ${r.chunks} chunks`}
                {r.status === "error" && r.detail}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
