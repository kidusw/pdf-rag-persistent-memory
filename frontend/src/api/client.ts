import type { Chat, ChatSummary, DocumentInfo, IngestResponse } from "../types";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Throws ApiError carrying the backend's `detail` message for non-2xx responses. */
export async function ensureOk(res: Response): Promise<Response> {
  if (res.ok) return res;
  let detail = res.statusText || `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
  } catch {
    // Non-JSON error body: keep the status text.
  }
  throw new ApiError(res.status, detail);
}

async function json<T>(input: string, init?: RequestInit): Promise<T> {
  const res = await ensureOk(await fetch(input, init));
  return res.json() as Promise<T>;
}

export const listChats = () => json<ChatSummary[]>("/api/chats");

export const getChat = (id: string) => json<Chat>(`/api/chats/${encodeURIComponent(id)}`);

export const createChat = () => json<Chat>("/api/chats", { method: "POST" });

export async function deleteChat(id: string): Promise<void> {
  await ensureOk(await fetch(`/api/chats/${encodeURIComponent(id)}`, { method: "DELETE" }));
}

export const listDocuments = () => json<DocumentInfo[]>("/api/documents");

export function uploadDocument(file: File): Promise<IngestResponse> {
  const form = new FormData();
  form.append("files", file);
  return json<IngestResponse>("/api/documents", { method: "POST", body: form });
}
