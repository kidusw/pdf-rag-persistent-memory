import { BrowserRouter, Route, Routes, useParams } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import HomePage from "./pages/HomePage";

function ChatPlaceholder() {
  const { id } = useParams();
  return <div className="p-8 text-gray-500">Chat {id}</div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/chat/:id" element={<ChatPlaceholder />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
