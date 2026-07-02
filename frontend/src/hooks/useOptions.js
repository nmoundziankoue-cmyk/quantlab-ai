import { useMutation, useQuery } from "@tanstack/react-query";
import { optionsApi } from "../api/optionsApi";

export function useTickerOptionsSummary(ticker, underlyingPrice, atmIv, enabled = true) {
  return useQuery({
    queryKey: ["options-summary", ticker, underlyingPrice, atmIv],
    queryFn: () => optionsApi.getTickerSummary(ticker, underlyingPrice, atmIv),
    enabled: !!ticker && enabled,
  });
}

export function usePriceOption() {
  return useMutation({ mutationFn: optionsApi.priceOption });
}

export function useOptionsChain() {
  return useMutation({ mutationFn: optionsApi.getChain });
}

export function useIVSurface() {
  return useMutation({ mutationFn: optionsApi.getIVSurface });
}

export function useExpectedMove() {
  return useMutation({ mutationFn: optionsApi.getExpectedMove });
}

export function useVolatilitySkew() {
  return useMutation({ mutationFn: optionsApi.getSkew });
}
