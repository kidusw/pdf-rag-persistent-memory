import { useState } from "react";
import { useDropzone } from "react-dropzone";

const UploadQuestion = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadId, setDownloadId] = useState<string | null>(null);
  const [fileFormat, setFileFormat] = useState("txt");
  const [sources, setSources] = useState([]);

  const onDrop = (acceptedFiles: File[]) => {
    const validFiles = acceptedFiles.filter((f) => f.size < 10 * 1024 * 1024);
    if (validFiles.length !== acceptedFiles.length) {
      setError("Some files were too large (>10MB) and were skipped.");
    } else {
      setError(null);
    }
    setFiles((prev) => [...prev, ...validFiles]); // allow adding more
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
  });

  const handleUpload = async () => {
    if (!question) return;
    setLoading(true);
    try {
      setAnswer("");
      const formData = new FormData();

      files.forEach((file) => {
        formData.append("files", file);
      });
      formData.append("question", question);

      const response = await fetch(
        "http://localhost:8000/api/upload-question",
        {
          method: "POST",
          body: formData,
        }
      );
      const data = await response.json();

      setAnswer(data.answer);
      setDownloadId(data.download_id);
      setSources(data.sources);
      setFiles([]); // clear files after upload
    } catch (error) {
      console.log(error);
    } finally {
      setLoading(false);
    }
  };

  console.log(sources);

  const handleDownload = () => {
    if (!downloadId) return;
    const url = `http://localhost:8000/api/download/${downloadId}?format=${fileFormat}`;
    window.open(url, "_blank");
  };

  return (
    <div className="max-w-2xl mx-auto bg-white shadow-md rounded-2xl p-4 mb-6">
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
        {files.length > 0 ? (
          <ul className="text-sm text-gray-700">
            {files.map((f, idx) => (
              <li key={idx}>{f.name}</li>
            ))}
          </ul>
        ) : isDragActive ? (
          <p className="text-sm text-indigo-600">Drop your files here...</p>
        ) : (
          <p className="text-sm text-gray-500">
            Drag & drop files, or click to select
          </p>
        )}
      </div>
      {error && <p className="text-red-600">{error}</p>}

      <h2 className="text-lg font-semibold mb-2">Ask a Question</h2>
      <div className="flex items-center gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Type your question..."
          className="flex-1 rounded-xl border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          onClick={handleUpload}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl"
          disabled={loading}
        >
          {loading ? "Asking..." : "Ask"}
        </button>
      </div>

      <div className="mt-4 bg-gray-100 rounded-xl p-3 min-h-[60px]">
        {loading ? (
          <p className="text-gray-500">Loading answer...</p>
        ) : (
          <p>{answer}</p>
        )}
        <div className="mt-4">
          <h4 className="font-semibold">Sources</h4>
          <ul className="list-disc ml-5">
            {sources.map((s, idx) => (
              <li key={idx} className="text-indigo-600">
                {s}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {answer && downloadId && (
        <div className="p-5">
          <select
            onChange={(e) => setFileFormat(e.target.value)}
            className="m-3 rounded-b-sm"
          >
            <option value="txt">Text</option>
            <option value="json">Json</option>
            <option value="csv">CSV</option>
          </select>

          <button
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl"
            onClick={handleDownload}
          >
            Download Answer
          </button>
        </div>
      )}
    </div>
  );
};

export default UploadQuestion;
