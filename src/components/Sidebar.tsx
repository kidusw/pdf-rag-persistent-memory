import { useChats } from "../hooks/useChats";
import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Menu, MessageSquare } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useChatStore } from "../stores/chatStore";
import { Trash2 } from "lucide-react";

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

function Sidebar() {
  // const chats = useChats();
  const { chats, loadChats } = useChatStore();

  const { session_id } = useParams();
  const navigate = useNavigate();

  const [collapsed, setCollapsed] = useState(false);

  console.log("session_id from sidebar", session_id);

  useEffect(() => {
    loadChats();
  }, []);

  return (
    <div
      className={`
        bg-gray-900 text-white flex flex-col border-r border-gray-700
        transition-all duration-300
        ${collapsed ? "w-16" : "w-72"}
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        {!collapsed && <h2 className="text-lg font-bold">Chats</h2>}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-2 rounded hover:bg-gray-700"
        >
          <Menu size={20} />
        </button>
      </div>
      <button
        onClick={() => navigate("/")}
        className="flex items-center gap-2 p-3 bg-blue-600 rounded-lg hover:bg-blue-700 mb-4"
      >
        <MessageSquare size={18} />
        <span>New Chat</span>
      </button>
      {/* Chat list */}
      <div className="space-y-2 overflow-y-auto p-2">
        {chats.map((chat: Chat) => (
          <Link
            key={chat.session_id}
            to={`/chat/${chat.session_id}`}
            className={`
              flex items-center gap-3 p-3 rounded-lg cursor-pointer transition
              ${
                session_id === chat.session_id
                  ? "bg-blue-600 hover:bg-amber-500"
                  : "bg-gray-800 hover:bg-gray-700"
              }
            `}
          >
            {/* Icon when collapsed */}
            <MessageSquare size={18} />

            {/* Title (hidden when collapsed) */}
            {!collapsed && (
              <p className="text-sm font-medium truncate">
                {chat.question ? chat.question.slice(0, 40) : ""}
              </p>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}

export default Sidebar;
