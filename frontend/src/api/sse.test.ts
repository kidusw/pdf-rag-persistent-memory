import { afterEach, expect, test, vi } from "vitest";

import { parseSSE, streamMessage, type SSEEvent, type StreamEvent } from "./sse";

const streamOf = (...chunks: string[]) =>
  new ReadableStream<Uint8Array>({
    start(c) {
      chunks.forEach((s) => c.enqueue(new TextEncoder().encode(s)));
      c.close();
    },
  });

async function collect(s: ReadableStream<Uint8Array>): Promise<SSEEvent[]> {
  const out: SSEEvent[] = [];
  for await (const e of parseSSE(s)) out.push(e);
  return out;
}

afterEach(() => vi.unstubAllGlobals());

test("event split across chunks", async () => {
  expect(await collect(streamOf("event: tok", 'en\ndata: {"text":"Hi"}', "\n\n"))).toEqual([
    { event: "token", data: { text: "Hi" } },
  ]);
});

test("multiple events in one chunk", async () => {
  const s = streamOf('event: token\ndata: {"text":"a"}\n\nevent: done\ndata: {"message_id":"m1"}\n\n');
  expect((await collect(s)).map((e) => e.event)).toEqual(["token", "done"]);
});

test("multi-byte characters split across chunks are decoded intact", async () => {
  const bytes = new TextEncoder().encode('event: token\ndata: {"text":"ü"}\n\n');
  const cut = bytes.indexOf(0xc3) + 1; // split inside the two-byte "ü"
  const s = new ReadableStream<Uint8Array>({
    start(c) {
      c.enqueue(bytes.slice(0, cut));
      c.enqueue(bytes.slice(cut));
      c.close();
    },
  });
  expect(await collect(s)).toEqual([{ event: "token", data: { text: "ü" } }]);
});

test("streamMessage maps events and throws ApiError on 409", async () => {
  const sse =
    'event: sources\ndata: [{"filename":"a.pdf","page":1,"snippet":"s"}]\n\n' +
    'event: token\ndata: {"text":"Hi"}\n\n' +
    'event: done\ndata: {"message_id":"m1"}\n\n' +
    'event: error\ndata: {"detail":"boom"}\n\n';
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(new Response(streamOf(sse), { status: 200 }))
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Upload a PDF first." }), { status: 409 }),
    );
  vi.stubGlobal("fetch", fetchMock);

  const evs: StreamEvent[] = [];
  for await (const e of streamMessage("c1", "q", new AbortController().signal)) evs.push(e);
  expect(evs).toEqual([
    { type: "sources", sources: [{ filename: "a.pdf", page: 1, snippet: "s" }] },
    { type: "token", text: "Hi" },
    { type: "done", messageId: "m1" },
    { type: "error", detail: "boom" },
  ]);
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/chats/c1/messages");
  expect(JSON.parse(init.body)).toEqual({ content: "q" });

  await expect(streamMessage("c1", "q", new AbortController().signal).next()).rejects.toMatchObject(
    { status: 409, message: "Upload a PDF first." },
  );
});
