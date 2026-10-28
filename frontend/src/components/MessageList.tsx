import { AlertCircle, RotateCcw } from "lucide-react";
import { useEffect, useRef } from "react";

import type { Message } from "../types";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: Message[];
  isStreaming: boolean;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export default function MessageList({ messages, isStreaming, loading, error, onRetry }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const lastContent = messages.at(-1)?.content;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, lastContent, error]);

  if (loading) {
    return (
      <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-8">
        {[60, 90, 75].map((w, i) => (
          <div
            key={i}
            className={`h-5 animate-pulse rounded bg-zinc-200 dark:bg-zinc-800 ${i % 2 ? "" : "ml-auto"}`}
            style={{ width: `${w}%` }}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-8">
      {messages.length === 0 && !error && (
        <p className="pt-16 text-center text-zinc-500">Ask anything about your documents.</p>
      )}
      {messages.map((m, i) => (
        <MessageBubble
          key={m.id}
          message={m}
          streaming={isStreaming && i === messages.length - 1 && m.role === "assistant"}
        />
      ))}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
        >
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <p className="flex-1">{error}</p>
          {messages.some((m) => m.role === "user") && (
            <button
              onClick={onRetry}
              className="inline-flex items-center gap-1 font-medium hover:underline"
            >
              <RotateCcw size={14} /> Retry
            </button>
          )}
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
