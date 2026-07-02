import { create } from "zustand";

const useDocumentStore = create((set) => ({
  selectedDocumentId: null,
  setSelectedDocumentId: (id) => set({ selectedDocumentId: id }),

  searchQuery: "",
  setSearchQuery: (q) => set({ searchQuery: q }),

  searchType: "HYBRID",
  setSearchType: (t) => set({ searchType: t }),

  filterDocType: null,
  setFilterDocType: (t) => set({ filterDocType: t }),

  filterStatus: null,
  setFilterStatus: (s) => set({ filterStatus: s }),

  lastSearchResults: null,
  setLastSearchResults: (r) => set({ lastSearchResults: r }),

  lastAnswer: null,
  setLastAnswer: (a) => set({ lastAnswer: a }),
}));

export default useDocumentStore;
