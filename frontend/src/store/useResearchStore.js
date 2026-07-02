import { create } from "zustand";

const useResearchStore = create((set) => ({
  // Ticker being researched
  ticker: "",
  setTicker: (ticker) => set({ ticker: ticker.toUpperCase().trim() }),

  // Chart settings
  period: "6mo",
  interval: "1d",
  setPeriod: (period) => set({ period }),
  setInterval: (interval) => set({ interval }),

  // Selected indicators (keys from the indicator registry)
  selectedIndicators: {
    sma: [{ period: 20 }, { period: 50 }],
    rsi: [{ period: 14 }],
  },
  setIndicators: (indicators) => set({ selectedIndicators: indicators }),

  // Currently selected backtest result to display
  activeBacktestId: null,
  setActiveBacktestId: (id) => set({ activeBacktestId: id }),

  // Active tab in the research panel
  activeTab: "chart", // "chart" | "backtest" | "history"
  setActiveTab: (tab) => set({ activeTab: tab }),
}));

export default useResearchStore;
