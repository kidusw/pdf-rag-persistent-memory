import { FileText } from "lucide-react";
import { useState } from "react";

import type { Source } from "../types";

export default function SourceList({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState<number | null>(null);
  if (sources.length === 0) return null;

  return (
    <div className="mt-3">
      <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-zinc-500">Sources</p>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((s, i) => (
          <button
            key={`${s.filename}-${s.page}-${i}`}
            onClick={() => setOpen(open === i ? null : i)}
            aria-expanded={open === i}
            className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs transition ${
              open === i
                ? "border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300"
                : "border-zinc-200 text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800"
            }`}
          >
            <FileText size={12} />
            <span className="max-w-48 truncate">{s.filename}</span>
            <span className="text-zinc-400">· p.{s.page}</span>
          </button>
        ))}
      </div>
      {open !== null && (
        <blockquote className="mt-2 rounded-lg border-l-2 border-indigo-400 bg-zinc-50 px-3 py-2 text-sm text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">
          {sources[open].snippet}…
        </blockquote>
      )}
    </div>
  );
}
