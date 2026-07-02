import { create } from "zustand";

const useWorkspaceStore = create((set) => ({
  activeProjectId: null,
  setActiveProjectId: (id) => set({ activeProjectId: id }),

  activeFolderId: null,
  setActiveFolderId: (id) => set({ activeFolderId: id }),

  activeNoteId: null,
  setActiveNoteId: (id) => set({ activeNoteId: id }),

  activeTab: "projects",
  setActiveTab: (tab) => set({ activeTab: tab }),

  searchQuery: "",
  setSearchQuery: (q) => set({ searchQuery: q }),

  searchResults: [],
  setSearchResults: (r) => set({ searchResults: r }),

  showPinnedOnly: false,
  setShowPinnedOnly: (v) => set({ showPinnedOnly: v }),
}));

export default useWorkspaceStore;
