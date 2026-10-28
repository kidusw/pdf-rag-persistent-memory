import { create } from "zustand";

import { listDocuments } from "../api/client";
import type { DocumentInfo } from "../types";

interface DocumentStore {
  documents: DocumentInfo[];
  loaded: boolean;
  error: string | null;
  loadDocuments: () => Promise<void>;
}

export const useDocumentStore = create<DocumentStore>((set) => ({
  documents: [],
  loaded: false,
  error: null,

  loadDocuments: async () => {
    try {
      set({ documents: await listDocuments(), loaded: true, error: null });
    } catch (e) {
      set({ loaded: true, error: e instanceof Error ? e.message : String(e) });
    }
  },
}));
