import { create } from "zustand";

const useAlternativeDataStore = create((set) => ({
  activeEventType: null,
  setActiveEventType: (t) => set({ activeEventType: t }),

  activeTicker: "",
  setActiveTicker: (ticker) => set({ activeTicker: ticker.toUpperCase().trim() }),

  minImportance: 0.0,
  setMinImportance: (v) => set({ minImportance: v }),

  sentimentFilter: null,
  setSentimentFilter: (f) => set({ sentimentFilter: f }),

  dateRange: { start: null, end: null },
  setDateRange: (range) => set({ dateRange: range }),

  selectedEventId: null,
  setSelectedEventId: (id) => set({ selectedEventId: id }),

  feedView: "importance",
  setFeedView: (v) => set({ feedView: v }),
}));

export default useAlternativeDataStore;
