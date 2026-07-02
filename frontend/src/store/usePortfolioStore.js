import { create } from "zustand";

const usePortfolioStore = create((set) => ({
  selectedPortfolioId: null,
  activeTab: "holdings",
  transactionModalOpen: false,
  createPortfolioModalOpen: false,

  setSelectedPortfolioId: (id) => set({ selectedPortfolioId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  openTransactionModal: () => set({ transactionModalOpen: true }),
  closeTransactionModal: () => set({ transactionModalOpen: false }),
  openCreatePortfolioModal: () => set({ createPortfolioModalOpen: true }),
  closeCreatePortfolioModal: () => set({ createPortfolioModalOpen: false }),
}));

export default usePortfolioStore;
