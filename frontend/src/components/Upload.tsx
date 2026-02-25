import type React from "react";

function FileUpload() {
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const formData = new FormData();
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      formData.append("file", file);
    }

    await fetch("http://localhost:8000/api/upload", {
      method: "POST",
      body: formData,
    });
  };

  return (
    <div className="max-w-2xl mx-auto bg-white shadow-md rounded-2xl p-4 mb-6">
      <h2 className="text-lg font-semibold mb-2">Upload File</h2>
      <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-indigo-500 hover:bg-gray-50">
        <span className="text-gray-600">Click or drag file here</span>
        <input type="file" onChange={handleUpload} className="hidden" />
      </label>
    </div>
  );
}

export default FileUpload;
