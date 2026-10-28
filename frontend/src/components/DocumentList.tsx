import { FileText } from "lucide-react";
import { useEffect } from "react";

import { useDocumentStore } from "../stores/documentStore";

export default function DocumentList() {
  const { documents, loaded, error, loadDocuments } = useDocumentStore();

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  return (
    <section>
      <h2 className="mb-2 text-sm font-medium text-zinc-500">
        Indexed documents{loaded && !error ? ` (${documents.length})` : ""}
      </h2>
      {!loaded && <div className="h-10 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-900" />}
      {loaded && error && <p className="text-sm text-red-600">Couldn't load documents: {error}</p>}
      {loaded && !error && documents.length === 0 && (
        <p className="rounded-xl border border-zinc-200 px-3 py-3 text-sm text-zinc-500 dark:border-zinc-800">
          No documents yet. Upload a PDF to get started.
        </p>
      )}
      {documents.length > 0 && (
        <ul className="divide-y divide-zinc-200 rounded-xl border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {documents.map((d) => (
            <li key={d.filename} className="flex items-center gap-3 px-3 py-2 text-sm">
              <FileText size={16} className="shrink-0 text-zinc-400" />
              <span className="min-w-0 flex-1 truncate">{d.filename}</span>
              <span className="shrink-0 text-xs text-zinc-500">{d.chunks} chunks</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
