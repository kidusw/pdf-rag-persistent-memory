import { useState } from "react";
import { useDropzone } from "react-dropzone";

function UploadAndQueryStream() {
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  // Handle file drop
  const onDrop = (acceptedFiles: File[]) => {
    if (acceptedFiles && acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true, // only allow 1 file
  });

  const handleUploadAndQuery = async () => {
    if (!question) return;

    try {
      setAnswer(""); // reset answer
      setLoading(true);

      const formData = new FormData();
      if (file) formData.append("file", file);
      formData.append("question", question);

      const response = await fetch(
        "http://localhost:8000/api/upload-and-query-stream",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.body) {
        console.error("ReadableStream not supported");
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        setAnswer((prev) => prev + chunk);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto bg-white shadow-md rounded-2xl p-4">
      <h2 className="text-lg font-semibold mb-3">Upload & Ask</h2>

      {/* Drag & Drop Zone */}
      <div
        {...getRootProps()}
        className={`w-full h-28 flex items-center justify-center border-2 border-dashed rounded-xl cursor-pointer transition  hover:border-indigo-500 hover:bg-gray-50
          ${
            isDragActive
              ? "border-indigo-500 bg-indigo-50"
              : "border-gray-300 bg-gray-50"
          }`}
      >
        <input {...getInputProps()} />
        {file ? (
          <p className="text-sm text-gray-700">{file.name}</p>
        ) : isDragActive ? (
          <p className="text-sm text-indigo-600">Drop your file here...</p>
        ) : (
          <p className="text-sm text-gray-500">
            Drag & drop a file, or click to select
          </p>
        )}
      </div>

      {/* Chat Input */}
      <div className="mt-4 flex items-center gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask your question..."
          className="flex-1 rounded-xl border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 "
        />
        <button
          onClick={handleUploadAndQuery}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl disabled:opacity-50"
          disabled={loading}
        >
          {loading ? "Asking..." : "Ask"}
        </button>
      </div>

      {/* Answer Box */}
      <div className="mt-4 bg-gray-100 rounded-xl p-3 min-h-[100px]">
        {loading ? (
          <p className="text-gray-500">Loading...</p>
        ) : (
          <pre className="whitespace-pre-wrap">{answer}</pre>
        )}
      </div>
    </div>
  );
}

export default UploadAndQueryStream;
