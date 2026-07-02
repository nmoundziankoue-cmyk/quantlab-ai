import { create } from "zustand";

const useMarketStore = create((set) => ({
  activeWatchlistId: null,
  focusedTicker: null,
  addTickerModalOpen: false,
  createWatchlistModalOpen: false,

  setActiveWatchlistId: (id) => set({ activeWatchlistId: id }),
  setFocusedTicker: (ticker) => set({ focusedTicker: ticker }),
  openAddTickerModal: () => set({ addTickerModalOpen: true }),
  closeAddTickerModal: () => set({ addTickerModalOpen: false }),
  openCreateWatchlistModal: () => set({ createWatchlistModalOpen: true }),
  closeCreateWatchlistModal: () => set({ createWatchlistModalOpen: false }),
}));

export default useMarketStore;
