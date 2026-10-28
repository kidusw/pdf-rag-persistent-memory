import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import Composer from "../components/Composer";
import MessageList from "../components/MessageList";
import { useChatStream } from "../hooks/useChatStream";

interface Props {
  chatId: string;
  onAttach?: () => void;
}

/** Location state set by HomePage when a chat is started from the first question. */
export interface ChatLocationState {
  initialMessage?: string;
}

export default function ChatPage({ chatId, onAttach }: Props) {
  const { messages, loading, isStreaming, error, send, stop, retry } = useChatStream(chatId);
  const location = useLocation();
  const navigate = useNavigate();
  const initialSent = useRef(false);

  useEffect(() => {
    const initial = (location.state as ChatLocationState | null)?.initialMessage;
    if (!initial || initialSent.current) return;
    initialSent.current = true; // StrictMode runs effects twice; send only once
    navigate(location.pathname, { replace: true, state: null });
    void send(initial);
  }, [location, navigate, send]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        <MessageList
          messages={messages}
          loading={loading}
          isStreaming={isStreaming}
          error={error}
          onRetry={() => void retry()}
        />
      </div>
      <Composer
        onSend={(c) => void send(c)}
        onStop={stop}
        onAttach={onAttach}
        isStreaming={isStreaming}
      />
    </div>
  );
}
