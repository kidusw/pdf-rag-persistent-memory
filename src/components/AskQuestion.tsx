import { useState } from "react";

// -------------------- AskQuestion --------------------
function AskQuestion() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    try {
      setLoading(true);
      const res = await fetch(
        `http://localhost:8000/api/ask?q=${encodeURIComponent(question)}`
      );
      const data = await res.json();
      setAnswer(data.answer);
    } catch (error) {
      console.log(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto bg-white shadow-md rounded-2xl p-4 mb-6">
      <h2 className="text-lg font-semibold mb-2">Ask a Question</h2>
      <div className="flex items-center gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Type your question..."
          className="flex-1 rounded-xl border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          onClick={handleAsk}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl"
        >
          Ask
        </button>
      </div>
      <div className="mt-4 bg-gray-100 rounded-xl p-3 min-h-[60px]">
        {loading ? (
          <p className="text-gray-500">Loading answer...</p>
        ) : (
          <p>{answer}</p>
        )}
      </div>
    </div>
  );
}
export default AskQuestion;
