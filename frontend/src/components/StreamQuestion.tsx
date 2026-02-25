import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useLLMStream } from "../hooks/useLLMStream";

const StreamQuestion = () => {
  const [question, setQuestion] = useState("");
  const { response, loading, ask } = useLLMStream();

  const askQuestion = () => {
    if (question.trim().length === 0) return;
    ask(question);
    setQuestion("");
  };

  return (
    <div className="max-w-2xl mx-auto bg-white shadow-md rounded-2xl p-4 mb-6">
      <div className="flex items-center gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Type your question..."
          className="flex-1 rounded-xl border border-gray-300 px-3 py-2 focus:outline-none"
        />
        <button
          onClick={askQuestion}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl"
          disabled={loading}
        >
          {loading ? "Asking..." : "Ask"}
        </button>
      </div>

      <div className="mt-4 bg-gray-100 rounded-xl p-3 min-h-[60px]">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{response}</ReactMarkdown>
      </div>
    </div>
  );
};

export default StreamQuestion;
