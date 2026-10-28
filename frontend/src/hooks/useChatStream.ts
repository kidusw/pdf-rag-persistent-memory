import { useCallback, useEffect, useRef, useState } from "react";

import { getChat } from "../api/client";
import { streamMessage } from "../api/sse";
import { useChatStore } from "../stores/chatStore";
import type { Message } from "../types";

interface ChatState {
  chatId: string;
  messages: Message[];
  loading: boolean;
  isStreaming: boolean;
  error: string | null;
}

const initialState = (chatId: string): ChatState => ({
  chatId,
  messages: [],
  loading: true,
  isStreaming: false,
  error: null,
});

const localMessage = (id: string, role: Message["role"], content: string): Message => ({
  id,
  role,
  content,
  sources: [],
  created_at: new Date().toISOString(),
});

const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));

/**
 * Messages and streaming state for one chat. Only the latest request may write state:
 * switching chats, unmounting, stop() or a new send() makes older streams inert.
 */
export function useChatStream(chatId: string) {
  const [state, setState] = useState<ChatState>(() => initialState(chatId));
  const controllerRef = useRef<AbortController | null>(null);
  const requestRef = useRef(0);
  const chatIdRef = useRef(chatId);
  const mountedRef = useRef(false);
  const sentForRef = useRef<string | null>(null);
  const touchChat = useChatStore((s) => s.touchChat);

  useEffect(() => {
    chatIdRef.current = chatId;
    mountedRef.current = true;
    let cancelled = false;

    getChat(chatId)
      .then((chat) => {
        if (cancelled) return;
        setState((s) =>
          // Once a send() has started for this chat it owns the message list; don't clobber it.
          // (A per-load snapshot isn't enough: StrictMode re-runs this effect after the first send.)
          s.chatId === chatId && sentForRef.current === chatId
            ? { ...s, loading: false }
            : { ...initialState(chatId), messages: chat.messages, loading: false },
        );
      })
      .catch((e) => {
        if (!cancelled) setState({ ...initialState(chatId), loading: false, error: errorText(e) });
      });

    return () => {
      cancelled = true;
      mountedRef.current = false;
      // Deferred so React StrictMode's simulated unmount/remount doesn't kill a live stream.
      setTimeout(() => {
        if (!mountedRef.current || chatIdRef.current !== chatId) {
          // Intentionally reads the latest request counter (not a snapshot): invalidates whatever is in flight.
          // eslint-disable-next-line react-hooks/exhaustive-deps
          requestRef.current++;
          controllerRef.current?.abort();
        }
      }, 0);
    };
  }, [chatId]);

  const send = useCallback(
    async (content: string, opts: { retry?: boolean } = {}) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      const req = ++requestRef.current;
      const sendChatId = chatId;
      sentForRef.current = chatId;
      const live = () => requestRef.current === req && chatIdRef.current === sendChatId;
      const assistantId = `local-assistant-${req}`;

      const update = (fn: (s: ChatState) => ChatState) =>
        setState((s) => (live() && s.chatId === sendChatId ? fn(s) : s));
      const patchAssistant = (fn: (m: Message) => Message) =>
        update((s) => ({
          ...s,
          messages: s.messages.map((m) => (m.id === assistantId ? fn(m) : m)),
        }));
      const dropEmptyAssistant = (s: ChatState) => ({
        ...s,
        messages: s.messages.filter((m) => m.id !== assistantId || m.content !== ""),
      });

      update((s) => ({
        ...s,
        error: null,
        isStreaming: true,
        messages: [
          ...(opts.retry ? s.messages : [...s.messages, localMessage(`local-user-${req}`, "user", content)]),
          localMessage(assistantId, "assistant", ""),
        ],
      }));

      let ok = false;
      try {
        for await (const ev of streamMessage(sendChatId, content, controller.signal)) {
          if (!live()) return;
          if (ev.type === "sources") patchAssistant((m) => ({ ...m, sources: ev.sources }));
          else if (ev.type === "token") patchAssistant((m) => ({ ...m, content: m.content + ev.text }));
          else if (ev.type === "done") {
            ok = true;
            patchAssistant((m) => ({ ...m, id: ev.messageId }));
          } else update((s) => ({ ...dropEmptyAssistant(s), error: ev.detail }));
        }
      } catch (e) {
        if (controller.signal.aborted) update(dropEmptyAssistant);
        else update((s) => ({ ...dropEmptyAssistant(s), error: errorText(e) }));
      } finally {
        update((s) => ({ ...s, isStreaming: false }));
        if (ok && live()) touchChat(sendChatId, content);
      }
    },
    [chatId, touchChat],
  );

  const stop = useCallback(() => {
    controllerRef.current?.abort();
  }, []);

  const retry = useCallback(() => {
    const lastUser = [...state.messages].reverse().find((m) => m.role === "user");
    if (lastUser) return send(lastUser.content, { retry: true });
    return Promise.resolve();
  }, [send, state.messages]);

  // Before the first load for a new chatId lands, never show the previous chat's messages.
  const current = state.chatId === chatId ? state : initialState(chatId);
  return {
    messages: current.messages,
    loading: current.loading,
    isStreaming: current.isStreaming,
    error: current.error,
    send,
    stop,
    retry,
  };
}
