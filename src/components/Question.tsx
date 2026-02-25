import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const Question = () => {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);

  const AskQuestion = async () => {
    setLoading(true);

    try {
      const formdata = new FormData();

      if (question) formdata.append("question", question);

      const response = await fetch("http://localhost:8000/api/ask", {
        method: "POST",
        body: formdata,
      });
      const res = await response.json();
      console.log(res.answer.summary);
      setAnswer(res.answer.summary);

      setQuestion("");
    } catch (error) {
      console.log(error);
      setLoading(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto bg-white shadow-md rounded-2xl p-4 mb-6">
      <div className="mt-4 bg-gray-100 rounded-xl p-3 min-h-[60px]">
        <div className="flex items-center gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Type your question..."
            className="flex-1 rounded-xl border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            disabled={loading}
          />
          <button
            onClick={AskQuestion}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl"
            disabled={loading}
          >
            {loading ? "Asking..." : "Ask"}
          </button>
        </div>
        {loading ? (
          <p className="text-gray-500">Loading answer...</p>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
        )}
      </div>
    </div>
  );
};

export default Question;
