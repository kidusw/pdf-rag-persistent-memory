import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  role: "human" | "ai";
  content: string;
}

// interface ChatHistoryProps {
//   messages: Message[];
// }

export default function ChatPage() {
  const { session_id } = useParams();
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    async function loadChat() {
      const res = await fetch(`http://localhost:8000/chat/${session_id}`);
      const data = await res.json();
      setMessages(data.messages);
    }
    loadChat();
  }, [session_id]);

  return (
    <div className="p-6">
      <h1 className="text-xl font-bold mb-4">Chat {session_id}</h1>

      <div className="space-y-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${
              msg.role === "human" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] px-4 py-3 rounded-2xl shadow-sm ${
                msg.role === "human"
                  ? "bg-indigo-600 text-white rounded-br-none"
                  : "bg-white text-gray-900 rounded-bl-none border"
              }`}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
