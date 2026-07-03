import { create } from "zustand";

export const REGIME_COLORS = {
  BULL:     "#27C784",
  BEAR:     "#E5473E",
  HIGH_VOL: "#9D7FEA",
  LOW_VOL:  "#567EFF",
  RANGING:  "#E2A52B",
};

const useRegimeStore = create((set) => ({
  regime: "BULL",
  confidence: 0.0,
  setRegime: (regime, confidence = 0.0) => set({ regime, confidence }),
}));

export default useRegimeStore;
