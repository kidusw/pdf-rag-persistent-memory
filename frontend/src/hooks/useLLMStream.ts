import { useState } from "react";

export function useLLMStream() {
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  const ask = async (question: string) => {
    setLoading(true);
    setResponse("");

    const formData = new FormData();
    formData.append("question", question);

    const res = await fetch("http://localhost:8000/api/ask-stream", {
      method: "POST",
      body: formData,
    });

    if (!res.body) {
      setLoading(false);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      if (text.includes("[DONE]")) break;

      setResponse((prev) => prev + text);
    }

    setLoading(false);
  };

  return { response, loading, ask };
}
