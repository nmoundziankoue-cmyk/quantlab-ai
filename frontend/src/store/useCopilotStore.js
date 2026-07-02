import { create } from "zustand";

const useCopilotStore = create((set) => ({
  activeSessionId: null,
  setActiveSessionId: (id) => set({ activeSessionId: id }),

  activeTicker: "",
  setActiveTicker: (ticker) => set({ activeTicker: ticker.toUpperCase().trim() }),

  inputMessage: "",
  setInputMessage: (msg) => set({ inputMessage: msg }),

  selectedDocumentIds: [],
  setSelectedDocumentIds: (ids) => set({ selectedDocumentIds: ids }),
  addDocumentId: (id) => set((s) => ({ selectedDocumentIds: [...new Set([...s.selectedDocumentIds, id])] })),
  removeDocumentId: (id) => set((s) => ({ selectedDocumentIds: s.selectedDocumentIds.filter((d) => d !== id) })),

  generationMode: "chat",
  setGenerationMode: (mode) => set({ generationMode: mode }),

  isStreaming: false,
  setIsStreaming: (v) => set({ isStreaming: v }),
}));

export default useCopilotStore;
