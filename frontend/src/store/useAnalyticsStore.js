/**
 * Zustand store for M4 Analytics page state.
 */
import { create } from "zustand";

const useAnalyticsStore = create((set) => ({
  // Active tab in the analytics page
  activeTab: "risk",
  setActiveTab: (tab) => set({ activeTab: tab }),

  // Risk metrics config
  lookbackDays: 252,
  setLookbackDays: (d) => set({ lookbackDays: d }),
  benchmark: "SPY",
  setBenchmark: (b) => set({ benchmark: b }),

  // Optimization config
  optimizationMethod: "max_sharpe",
  setOptimizationMethod: (m) => set({ optimizationMethod: m }),

  // Monte Carlo config
  mcModel: "gbm",
  setMcModel: (m) => set({ mcModel: m }),
  mcDays: 252,
  setMcDays: (d) => set({ mcDays: d }),
  mcSims: 10000,
  setMcSims: (n) => set({ mcSims: n }),

  // Correlation config
  corrMethod: "pearson",
  setCorrMethod: (m) => set({ corrMethod: m }),
  nClusters: 3,
  setNClusters: (n) => set({ nClusters: n }),

  // Cached results (so switching tabs doesn't re-fetch)
  riskResult: null,
  setRiskResult: (r) => set({ riskResult: r }),

  optimizationResult: null,
  setOptimizationResult: (r) => set({ optimizationResult: r }),

  frontierResult: null,
  setFrontierResult: (r) => set({ frontierResult: r }),

  stressResult: null,
  setStressResult: (r) => set({ stressResult: r }),

  monteCarloResult: null,
  setMonteCarloResult: (r) => set({ monteCarloResult: r }),

  factorResult: null,
  setFactorResult: (r) => set({ factorResult: r }),

  correlationResult: null,
  setCorrelationResult: (r) => set({ correlationResult: r }),

  mstResult: null,
  setMstResult: (r) => set({ mstResult: r }),
}));

export default useAnalyticsStore;
