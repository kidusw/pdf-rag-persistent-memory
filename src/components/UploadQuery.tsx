import { useState } from "react";
import { useDropzone } from "react-dropzone";

const UploadQuery = () => {
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [downloadId, setDownloadId] = useState(null);
  const [fileFormat, setFileFormat] = useState("txt");

  const onDrop = (acceptedFiles: File[]) => {
    if (
      acceptedFiles &&
      acceptedFiles.length > 0 &&
      acceptedFiles[0].size < 10 * 1024 * 1024
    ) {
      setError(false);
      setFile(acceptedFiles[0]);
    } else {
      setError(true);
      alert("File size must be less than 10MB");
    }
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
      if (file) formData.append("file", file);
      formData.append("question", question);

      const response = await fetch(
        "http://localhost:8000/api/upload-and-query",
        {
          method: "POST",
          body: formData,
        }
      );
      const data = await response.json();

      setAnswer(data.answer);
      setDownloadId(data.download_id);
      setFile(null);
    } catch (error) {
      console.log(error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!downloadId) return;
    const url = `http://localhost:8000/api/download/${downloadId}?format=${fileFormat}`;
    window.open(url, "_blank");
  };

  return (
    <div className="max-w-2xl mx-auto bg-white shadow-md rounded-2xl p-4 mb-6">
      {/* <h2 className="text-lg font-semibold mb-2">Upload File</h2>
      <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-indigo-500 hover:bg-gray-50">
        <span className="text-gray-600">Click or drag file here</span>
        <input
          type="file"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0)
              setFile(e.target.files[0]);
          }}
          className="hidden"
        />
      </label> */}
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
          <p
            className={error ? "text-sm text-red-500" : "text-sm text-gray-700"}
          >
            {error ? "File size should be less than 10MB" : file.name}
          </p>
        ) : isDragActive ? (
          <p className="text-sm text-indigo-600">Drop your file here...</p>
        ) : (
          <p className="text-sm text-gray-500">
            Drag & drop a file, or click to select
          </p>
        )}
      </div>
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
      </div>

      {answer && (
        <div>
          {downloadId && (
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
      )}
    </div>
  );
};

export default UploadQuery;
