import { FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createChat } from "../api/client";
import Composer from "../components/Composer";
import DocumentList from "../components/DocumentList";
import UploadPanel from "../components/UploadPanel";
import { useChatStore } from "../stores/chatStore";
import { useDocumentStore } from "../stores/documentStore";
import type { ChatLocationState } from "./ChatPage";

export default function HomePage() {
  const navigate = useNavigate();
  const addChat = useChatStore((s) => s.addChat);
  const { documents, loaded, loadDocuments } = useDocumentStore();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  async function start(content: string) {
    setStarting(true);
    setError(null);
    try {
      const chat = await createChat();
      addChat({ id: chat.id, title: chat.title, updated_at: chat.updated_at });
      const state: ChatLocationState = { initialMessage: content };
      navigate(`/chat/${chat.id}`, { state });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStarting(false);
    }
  }

  const noDocs = loaded && documents.length === 0;

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl space-y-8 px-4 py-10">
          <header className="text-center">
            <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-2xl bg-indigo-100 dark:bg-indigo-500/15">
              <FileText className="text-indigo-600 dark:text-indigo-400" />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">Chat with your PDFs</h1>
            <p className="mt-2 text-zinc-500">
              Upload documents, then ask questions. Answers cite the pages they come from.
            </p>
          </header>
          <UploadPanel />
          <DocumentList />
          {error && (
            <p role="alert" className="text-center text-sm text-red-600">
              {error}
            </p>
          )}
        </div>
      </div>
      <Composer
        onSend={(c) => void start(c)}
        disabled={!loaded || noDocs || starting}
        hint={noDocs ? "Upload a PDF to start" : undefined}
      />
    </div>
  );
}
