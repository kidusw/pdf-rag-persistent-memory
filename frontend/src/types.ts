// Mirrors the backend models (backend/app/storage/models.py, backend/app/api/documents.py).

export type Role = "user" | "assistant";

export interface Source {
  filename: string;
  page: number;
  snippet: string;
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  sources: Source[];
  created_at: string;
}

export interface ChatSummary {
  id: string;
  title: string;
  updated_at: string;
}

export interface Chat extends ChatSummary {
  created_at: string;
  messages: Message[];
}

export interface DocumentInfo {
  filename: string;
  chunks: number;
}

export interface IngestResponse {
  results: { filename: string; pages: number; chunks: number }[];
  errors: { filename: string; detail: string }[];
}
