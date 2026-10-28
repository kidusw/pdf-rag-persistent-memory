import { create } from "zustand";

import { listChats } from "../api/client";
import type { ChatSummary } from "../types";

interface ChatStore {
  chats: ChatSummary[];
  loadChats: () => Promise<void>;
  addChat: (chat: ChatSummary) => void;
  removeChat: (id: string) => void;
  /** Move a chat to the top after activity, filling in its title if it had none. */
  touchChat: (id: string, title?: string) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  chats: [],

  loadChats: async () => {
    set({ chats: await listChats() });
  },

  addChat: (chat) => set((s) => ({ chats: [chat, ...s.chats.filter((c) => c.id !== chat.id)] })),

  removeChat: (id) => set((s) => ({ chats: s.chats.filter((c) => c.id !== id) })),

  touchChat: (id, title) =>
    set((s) => {
      const chat = s.chats.find((c) => c.id === id);
      if (!chat) return s;
      const updated: ChatSummary = {
        ...chat,
        title: chat.title || (title ?? "").slice(0, 60),
        updated_at: new Date().toISOString(),
      };
      return { chats: [updated, ...s.chats.filter((c) => c.id !== id)] };
    }),
}));
