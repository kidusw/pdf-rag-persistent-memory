import React, { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  role: "human" | "ai";
  content: string;
}

interface ChatHistoryProps {
  messages: Message[];
}

const ChatHistory: React.FC<ChatHistoryProps> = ({ messages }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom whenever messages update
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div
      ref={containerRef}
      className="p-4 bg-gray-100 rounded-xl h-[500px] overflow-y-auto space-y-4"
    >
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
  );
};

export default ChatHistory;
