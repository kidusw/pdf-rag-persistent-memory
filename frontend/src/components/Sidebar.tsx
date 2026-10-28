import { Menu, MessageSquare } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useChatStore } from "../stores/chatStore";

export default function Sidebar() {
  const { chats, loadChats } = useChatStore();
  const { id: activeId } = useParams();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    void loadChats();
  }, [loadChats]);

  return (
    <aside
      className={`flex flex-col border-r border-gray-700 bg-gray-900 text-white transition-all duration-300 ${
        collapsed ? "w-16" : "w-72"
      }`}
    >
      <div className="flex items-center justify-between border-b border-gray-700 p-4">
        {!collapsed && <h2 className="text-lg font-bold">Chats</h2>}
        <button onClick={() => setCollapsed(!collapsed)} className="rounded p-2 hover:bg-gray-700">
          <Menu size={20} />
        </button>
      </div>
      <button
        onClick={() => navigate("/")}
        className="m-2 flex items-center gap-2 rounded-lg bg-blue-600 p-3 hover:bg-blue-700"
      >
        <MessageSquare size={18} />
        {!collapsed && <span>New Chat</span>}
      </button>
      <nav className="space-y-2 overflow-y-auto p-2">
        {chats.map((chat) => (
          <Link
            key={chat.id}
            to={`/chat/${chat.id}`}
            className={`flex items-center gap-3 rounded-lg p-3 transition ${
              activeId === chat.id ? "bg-blue-600" : "bg-gray-800 hover:bg-gray-700"
            }`}
          >
            <MessageSquare size={18} />
            {!collapsed && (
              <p className="truncate text-sm font-medium">{chat.title || "New chat"}</p>
            )}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
