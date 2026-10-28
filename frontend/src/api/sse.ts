import type { Source } from "../types";
import { ensureOk } from "./client";

export type SSEEvent = { event: string; data: unknown };

export type StreamEvent =
  | { type: "sources"; sources: Source[] }
  | { type: "token"; text: string }
  | { type: "done"; messageId: string }
  | { type: "error"; detail: string };

/** Parse a text/event-stream body. Events may arrive split across, or batched within, chunks. */
export async function* parseSSE(stream: ReadableStream<Uint8Array>): AsyncGenerator<SSEEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      // stream: true keeps a multi-byte character that straddles two chunks intact.
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const block = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const event = parseBlock(block);
        if (event) yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseBlock(block: string): SSEEvent | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (data.length === 0) return null;
  return { event, data: JSON.parse(data.join("\n")) };
}

/** POST a user message and yield the assistant's streamed response as typed events. */
export async function* streamMessage(
  chatId: string,
  content: string,
  signal: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const res = await ensureOk(
    await fetch(`/api/chats/${encodeURIComponent(chatId)}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
      signal,
    }),
  );
  if (!res.body) throw new Error("Response has no body");

  for await (const { event, data } of parseSSE(res.body)) {
    const d = data as Record<string, unknown>;
    switch (event) {
      case "sources":
        yield { type: "sources", sources: data as Source[] };
        break;
      case "token":
        yield { type: "token", text: String(d.text ?? "") };
        break;
      case "done":
        yield { type: "done", messageId: String(d.message_id ?? "") };
        break;
      case "error":
        yield { type: "error", detail: String(d.detail ?? "Unknown error") };
        break;
    }
  }
}
