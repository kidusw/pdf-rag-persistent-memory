import { useEffect, useState } from "react";

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

export function useChats() {
  const [chats, setChats] = useState<Chat[]>([]);

  useEffect(() => {
    async function loadChats() {
      const res = await fetch("http://localhost:8000/chat/all");
      const data = await res.json();
      setChats(data);
    }
    loadChats();
  }, []);

  console.log("chats: ", chats);

  return chats;
}
