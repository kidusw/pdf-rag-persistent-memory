import { FileText, MessageSquare, PanelLeftClose, PanelLeftOpen, Plus, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useMatch, useNavigate } from "react-router-dom";

import { deleteChat } from "../api/client";
import { useChatStore } from "../stores/chatStore";
import { relativeTime } from "../utils/time";

interface Props {
  /** Mobile drawer visibility; on md+ screens the sidebar is always shown. */
  open: boolean;
  onClose: () => void;
}

export default function Sidebar({ open, onClose }: Props) {
  const { chats, loadChats, removeChat } = useChatStore();
  // Sidebar lives outside <Routes>, so read the active chat from the URL directly.
  const activeId = useMatch("/chat/:id")?.params.id;
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    loadChats().catch(() => setLoadError("Couldn't load chats"));
  }, [loadChats]);

  async function onDelete(id: string, title: string) {
    if (!window.confirm(`Delete "${title || "New chat"}"? This can't be undone.`)) return;
    try {
      await deleteChat(id);
    } catch (e) {
      window.alert(`Couldn't delete chat: ${e instanceof Error ? e.message : e}`);
      return;
    }
    removeChat(id);
    if (id === activeId) navigate("/");
  }

  const narrow = collapsed && !open;

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/40 md:hidden" onClick={onClose} aria-hidden />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-zinc-200 bg-zinc-50 transition-all duration-200 dark:border-zinc-800 dark:bg-zinc-900 md:static md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        } ${narrow ? "md:w-16" : "w-72"}`}
      >
        <div className="flex items-center justify-between gap-2 p-3">
          {!narrow && (
            <Link to="/" onClick={onClose} className="flex items-center gap-2 px-1 font-semibold">
              <FileText size={20} className="text-indigo-600" />
              PDF Chat
            </Link>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="hidden rounded-lg p-2 text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-800 md:block"
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
          <button
            onClick={onClose}
            title="Close menu"
            className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-800 md:hidden"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-3">
          <button
            onClick={() => {
              navigate("/");
              onClose();
            }}
            title="New chat"
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 p-2.5 text-sm font-medium text-white hover:bg-indigo-500"
          >
            <Plus size={18} />
            {!narrow && "New chat"}
          </button>
        </div>

        <nav className="mt-3 flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
          {loadError && !narrow && <p className="px-3 py-2 text-sm text-red-600">{loadError}</p>}
          {chats.length === 0 && !loadError && !narrow && (
            <p className="px-3 py-2 text-sm text-zinc-500">No chats yet.</p>
          )}
          {chats.map((chat) => {
            const active = chat.id === activeId;
            return (
              <div
                key={chat.id}
                className={`group flex items-center rounded-lg transition ${
                  active
                    ? "bg-indigo-100 text-indigo-900 dark:bg-indigo-500/15 dark:text-indigo-100"
                    : "hover:bg-zinc-200/70 dark:hover:bg-zinc-800"
                }`}
              >
                <Link
                  to={`/chat/${chat.id}`}
                  onClick={onClose}
                  title={chat.title || "New chat"}
                  className="flex min-w-0 flex-1 items-center gap-3 px-3 py-2"
                >
                  <MessageSquare size={16} className="shrink-0 opacity-60" />
                  {!narrow && (
                    <span className="min-w-0">
                      <span className="block truncate text-sm">{chat.title || "New chat"}</span>
                      <span className="block text-xs text-zinc-500">{relativeTime(chat.updated_at)}</span>
                    </span>
                  )}
                </Link>
                {!narrow && (
                  <button
                    onClick={() => void onDelete(chat.id, chat.title)}
                    title="Delete chat"
                    className="mr-1 rounded-md p-1.5 text-zinc-400 opacity-100 hover:bg-zinc-300/60 hover:text-red-600 focus:opacity-100 md:opacity-0 md:group-hover:opacity-100 dark:hover:bg-zinc-700"
                  >
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
