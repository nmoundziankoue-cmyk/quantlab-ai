import { create } from "zustand";

const usePortfolioOptimizationStore = create((set) => ({
  // --- Input form state ---
  tickersRaw: "AAPL,MSFT,GOOGL,AMZN,NVDA",
  method: "max_sharpe",
  riskFreeRate: 0.05,
  nFrontierPoints: 50,
  mcSimulations: 2000,
  mcDays: 252,
  mcModel: "gbm",

  setTickersRaw: (v) => set({ tickersRaw: v }),
  setMethod: (v) => set({ method: v }),
  setRiskFreeRate: (v) => set({ riskFreeRate: v }),
  setNFrontierPoints: (v) => set({ nFrontierPoints: v }),
  setMcSimulations: (v) => set({ mcSimulations: v }),
  setMcDays: (v) => set({ mcDays: v }),
  setMcModel: (v) => set({ mcModel: v }),

  // --- Active tab ---
  activeTab: "optimize",
  setActiveTab: (v) => set({ activeTab: v }),

  // --- Results ---
  availableMethods: [],
  setAvailableMethods: (v) => set({ availableMethods: v }),

  optimization: null,
  setOptimization: (v) => set({ optimization: v }),

  comparison: null,
  setComparison: (v) => set({ comparison: v }),

  frontier: null,
  setFrontier: (v) => set({ frontier: v }),

  stressResults: null,
  setStressResults: (v) => set({ stressResults: v }),

  monteCarloResult: null,
  setMonteCarloResult: (v) => set({ monteCarloResult: v }),

  // --- Error / loading ---
  error: null,
  setError: (v) => set({ error: v }),
  clearError: () => set({ error: null }),
}));

export default usePortfolioOptimizationStore;
