import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import type { StreamEvent } from "../api/sse";
import { useChatStore } from "../stores/chatStore";
import { useChatStream } from "./useChatStream";

const h = vi.hoisted(() => ({
  signals: [] as AbortSignal[],
  release: () => {},
  script: [] as unknown[],
}));

vi.mock("../api/client", () => ({
  getChat: vi.fn(async (id: string) => ({
    id,
    title: "",
    created_at: "",
    updated_at: "",
    messages: [],
  })),
}));

vi.mock("../api/sse", () => ({
  async *streamMessage(_id: string, _content: string, signal: AbortSignal) {
    h.signals.push(signal);
    for (const step of h.script) {
      if (step === "wait") await new Promise<void>((r) => (h.release = r));
      else yield step as StreamEvent;
    }
  },
}));

beforeEach(() => {
  h.signals.length = 0;
  h.script = [];
  useChatStore.setState({
    chats: [{ id: "a", title: "", updated_at: "2020-01-01T00:00:00Z" }],
  });
});

test("send streams tokens and sources into an assistant message", async () => {
  h.script = [
    { type: "sources", sources: [{ filename: "a.pdf", page: 2, snippet: "s" }] },
    { type: "token", text: "Hel" },
    { type: "token", text: "lo" },
    { type: "done", messageId: "m1" },
  ];
  const { result } = renderHook(() => useChatStream("a"));
  await act(() => result.current.send("hi"));
  expect(result.current.messages.map((m) => [m.role, m.content])).toEqual([
    ["user", "hi"],
    ["assistant", "Hello"],
  ]);
  expect(result.current.messages[1].id).toBe("m1");
  expect(result.current.messages[1].sources[0].page).toBe(2);
  expect(result.current.isStreaming).toBe(false);
  expect(useChatStore.getState().chats[0].title).toBe("hi");
});

test("error event surfaces error and retry resends without duplicating the user message", async () => {
  h.script = [{ type: "error", detail: "rate limited" }];
  const { result } = renderHook(() => useChatStream("a"));
  await act(() => result.current.send("hi"));
  expect(result.current.error).toBe("rate limited");
  expect(result.current.messages.map((m) => m.role)).toEqual(["user"]);

  h.script = [{ type: "token", text: "ok" }, { type: "done", messageId: "m2" }];
  await act(() => result.current.retry());
  expect(result.current.error).toBeNull();
  expect(result.current.messages.map((m) => [m.role, m.content])).toEqual([
    ["user", "hi"],
    ["assistant", "ok"],
  ]);
});

test("switching chatId aborts the in-flight stream and drops its tokens", async () => {
  // Review Focus 5
  h.script = ["wait", { type: "token", text: "LATE" }];
  const { result, rerender } = renderHook(({ id }) => useChatStream(id), {
    initialProps: { id: "a" },
  });
  act(() => {
    void result.current.send("q");
  });
  rerender({ id: "b" });
  await act(async () => h.release());
  await waitFor(() => expect(h.signals[0].aborted).toBe(true));
  expect(result.current.messages.some((m) => m.content.includes("LATE"))).toBe(false);
  expect(result.current.isStreaming).toBe(false);
});
