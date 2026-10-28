import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { Message } from "../types";
import SourceList from "./SourceList";

interface Props {
  message: Message;
  streaming?: boolean;
}

export default function MessageBubble({ message, streaming = false }: Props) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2.5 text-white">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      {message.content === "" && streaming ? (
        <div className="flex gap-1 py-2" aria-label="Thinking">
          {[0, 150, 300].map((d) => (
            <span
              key={d}
              className="size-2 animate-bounce rounded-full bg-zinc-400"
              style={{ animationDelay: `${d}ms` }}
            />
          ))}
        </div>
      ) : (
        <div className="prose prose-zinc max-w-none dark:prose-invert prose-pre:bg-zinc-900">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          {streaming && <span className="cursor-blink ml-0.5 inline-block h-4 w-2 bg-zinc-500 align-middle" />}
        </div>
      )}
      <SourceList sources={message.sources} />
    </div>
  );
}
