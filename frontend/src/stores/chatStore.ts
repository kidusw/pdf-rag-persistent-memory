import { create } from "zustand";

interface Message {
  role: "human" | "ai";
  content: string;
}

interface Chat {
  session_id: string;
  question: string;
  message_json: Message[];
  updated_at: string;
}

interface ChatStore {
  chats: Chat[];
  loadChats: () => Promise<void>;
  addChat: (chat: Chat) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  chats: [],

  loadChats: async () => {
    const res = await fetch("http://localhost:8000/chat/all");
    const data = await res.json();
    set({ chats: data });
  },

  addChat: (chat) =>
    set((state) => ({ chats: [chat, ...state.chats] })),
}));
