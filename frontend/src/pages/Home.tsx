import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import LangUpload from "../components/LangUpload";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatStore } from "../stores/chatStore";

const Home = () => {
  const navigate = useNavigate();
  const session_id = "";
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const addChat = useChatStore.getState().addChat;

  const handleAsk = async () => {
    setLoading(true);

    try {
      const formdata = new FormData();

      if (question) formdata.append("question", question);

      const response = await fetch(
        `http://localhost:8000/query/conversational?session_id=${session_id}`,
        {
          method: "POST",
          body: formdata,
        }
      );
      const res = await response.json();
      console.log(res);

      console.log("response answer: ", res.answer);
      setAnswer(res.answer);

      //   setAnswer(res.answer.summary);
      setQuestion(res.source);

      setQuestion("");
      addChat(res);
      navigate(`/chat/${res.session_id}`);
    } catch (error) {
      console.log(error);
      setLoading(false);
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="max-w-2xl mx-auto bg-white shadow-md rounded-2xl p-4 mb-6">
      <LangUpload />
      <h2 className="text-lg font-semibold mb-2">Ask a Question</h2>
      <div className="flex items-center gap-2">
        <input
          value={question}
          disabled={loading}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Type your question..."
          className="flex-1 rounded-xl border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          onClick={handleAsk}
          disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl"
        >
          {loading ? <p>Asking.....</p> : <p>Ask</p>}
        </button>
      </div>
      <div className="mt-4 bg-gray-100 rounded-xl p-3 min-h-[60px]">
        {loading ? (
          <p className="text-gray-500">Loading answer...</p>
        ) : (
          <div className="mt-4 bg-gray-100 rounded-xl p-3 min-h-[60px]">
            {/* <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown> */}
          </div>
        )}
      </div>
    </div>
  );
};

export default Home;
