import { Menu } from "lucide-react";
import { useState } from "react";
import { BrowserRouter, Route, Routes, useParams } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import ChatPage from "./pages/ChatPage";
import HomePage from "./pages/HomePage";

function ChatRoute() {
  const { id } = useParams();
  // Keyed by id so switching chats starts from a fresh page state.
  return <ChatPage key={id} chatId={id!} />;
}

export default function App() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="flex h-full">
        <Sidebar open={drawerOpen} onClose={() => setDrawerOpen(false)} />
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center gap-2 border-b border-zinc-200 px-3 py-2 dark:border-zinc-800 md:hidden">
            <button
              onClick={() => setDrawerOpen(true)}
              title="Open menu"
              className="rounded-lg p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800"
            >
              <Menu size={20} />
            </button>
            <span className="font-semibold">PDF Chat</span>
          </header>
          <main className="min-h-0 flex-1">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/chat/:id" element={<ChatRoute />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}
