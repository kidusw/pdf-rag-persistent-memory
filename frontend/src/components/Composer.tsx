import { ArrowUp, Paperclip, Square } from "lucide-react";
import { useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

interface Props {
  onSend: (content: string) => void;
  onStop?: () => void;
  onAttach?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  hint?: string;
}

const MAX_HEIGHT = 200;

export default function Composer({
  onSend,
  onStop,
  onAttach,
  isStreaming = false,
  disabled = false,
  hint,
}: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  const canSend = !disabled && !isStreaming && value.trim() !== "";

  function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!canSend) return;
    onSend(value.trim());
    setValue("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto w-full max-w-3xl px-4 pb-4">
      <div
        className={`flex items-end gap-2 rounded-2xl border bg-white p-2 shadow-sm transition focus-within:border-indigo-400 dark:bg-zinc-900 ${
          disabled ? "border-zinc-200 opacity-60 dark:border-zinc-800" : "border-zinc-300 dark:border-zinc-700"
        }`}
      >
        {onAttach && (
          <button
            type="button"
            onClick={onAttach}
            title="Upload PDFs"
            className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
          >
            <Paperclip size={18} />
          </button>
        )}
        <textarea
          ref={ref}
          rows={1}
          value={value}
          disabled={disabled}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={disabled && hint ? hint : "Ask a question about your PDFs…"}
          aria-label="Message"
          className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-2 outline-none placeholder:text-zinc-400 focus-visible:outline-none disabled:cursor-not-allowed"
        />
        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            title="Stop"
            className="rounded-xl bg-zinc-800 p-2 text-white hover:bg-zinc-700 dark:bg-zinc-200 dark:text-zinc-900"
          >
            <Square size={18} fill="currentColor" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!canSend}
            title="Send"
            className="rounded-xl bg-indigo-600 p-2 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-zinc-300 dark:disabled:bg-zinc-700"
          >
            <ArrowUp size={18} />
          </button>
        )}
      </div>
      {disabled && hint && <p className="mt-2 text-center text-xs text-zinc-500">{hint}</p>}
    </form>
  );
}
