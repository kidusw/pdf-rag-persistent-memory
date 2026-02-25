import { useState } from "react";
import { useDropzone } from "react-dropzone";

const UploadOnly = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
    setLoading(true);
    try {
      const formData = new FormData();

      files.forEach((file) => {
        formData.append("files", file);
      });

      const response = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (data) {
        console.log("file_uploaded", data);
      }
      //   setFiles([]);
    } catch (error) {
      console.log(error);
    } finally {
      setLoading(false);
    }
  };
  console.log(files);
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
        ) : loading ? (
          <p>Uploading files</p>
        ) : (
          <p className="text-sm text-gray-500">
            Drag & drop files, or click to select
          </p>
        )}
      </div>
      <button
        onClick={handleUpload}
        disabled={loading || files.length === 0}
        className="w-full mt-4 py-2 px-4 bg-indigo-600 text-white rounded-lg disabled:bg-gray-400"
      >
        {loading ? "Uploading..." : "Upload Files"}
      </button>
    </div>
  );
};

export default UploadOnly;
