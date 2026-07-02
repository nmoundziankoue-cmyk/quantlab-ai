import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { researchApi } from "../api/researchApi";

// Keys
const KEYS = {
  indicators: (ticker, period, interval, indicators) => [
    "indicators",
    ticker,
    period,
    interval,
    indicators,
  ],
  availableStrategies: ["availableStrategies"],
  strategies: ["strategies"],
  backtests: ["backtests"],
  backtest: (id) => ["backtest", id],
};

// ---------------------------------------------------------------------------
// Indicators
// ---------------------------------------------------------------------------

export function useIndicators(body, enabled = true) {
  return useQuery({
    queryKey: KEYS.indicators(
      body?.ticker,
      body?.period,
      body?.interval,
      JSON.stringify(body?.indicators)
    ),
    queryFn: () => researchApi.getIndicators(body),
    enabled: enabled && !!body?.ticker,
    staleTime: 60_000,
    retry: 1,
  });
}

// ---------------------------------------------------------------------------
// Strategies
// ---------------------------------------------------------------------------

export function useAvailableStrategies() {
  return useQuery({
    queryKey: KEYS.availableStrategies,
    queryFn: researchApi.getAvailableStrategies,
    staleTime: Infinity, // never changes at runtime
  });
}

export function useSavedStrategies() {
  return useQuery({
    queryKey: KEYS.strategies,
    queryFn: researchApi.listStrategies,
    staleTime: 30_000,
  });
}

export function useCreateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: researchApi.createStrategy,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.strategies }),
  });
}

export function useDeleteStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: researchApi.deleteStrategy,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.strategies }),
  });
}

// ---------------------------------------------------------------------------
// Backtests
// ---------------------------------------------------------------------------

export function useBacktestList() {
  return useQuery({
    queryKey: KEYS.backtests,
    queryFn: researchApi.listBacktests,
    staleTime: 30_000,
  });
}

export function useBacktest(id) {
  return useQuery({
    queryKey: KEYS.backtest(id),
    queryFn: () => researchApi.getBacktest(id),
    enabled: !!id,
    staleTime: Infinity, // completed backtest results never change
  });
}

export function useRunBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: researchApi.runBacktest,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.backtests }),
  });
}

export function useDeleteBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: researchApi.deleteBacktest,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.backtests }),
  });
}
