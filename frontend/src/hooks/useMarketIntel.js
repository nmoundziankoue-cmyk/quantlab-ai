import { useMutation, useQuery } from "@tanstack/react-query";
import { marketIntelApi } from "../api/marketIntelApi";

export function useSectorHeatmap(period = "1D") {
  return useQuery({
    queryKey: ["sector-heatmap", period],
    queryFn: () => marketIntelApi.getSectorHeatmap(period),
    staleTime: 60000,
  });
}

export function useMarketBreadth() {
  return useQuery({
    queryKey: ["market-breadth"],
    queryFn: marketIntelApi.getBreadth,
    staleTime: 60000,
  });
}

export function useMarketRegime() {
  return useQuery({
    queryKey: ["market-regime"],
    queryFn: marketIntelApi.getRegime,
    staleTime: 60000,
  });
}

export function useYieldCurve() {
  return useQuery({
    queryKey: ["yield-curve"],
    queryFn: marketIntelApi.getYieldCurve,
    staleTime: 300000,
  });
}

export function useGlobalMacro() {
  return useQuery({
    queryKey: ["global-macro"],
    queryFn: marketIntelApi.getMacro,
    staleTime: 300000,
  });
}

export function useMarketDashboard() {
  return useQuery({
    queryKey: ["market-intel-dashboard"],
    queryFn: marketIntelApi.getDashboard,
    staleTime: 60000,
  });
}

export function useCorrelationMatrix() {
  return useMutation({ mutationFn: (tickers) => marketIntelApi.getCorrelation(tickers) });
}
