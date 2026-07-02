import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addWatchlistItem,
  createWatchlist,
  deleteWatchlist,
  deleteWatchlistItem,
  getBatchQuotes,
  getCalendar,
  getNews,
  getOHLCV,
  getQuote,
  getSentiment,
  listWatchlists,
} from "../api/marketApi";

// ---------------------------------------------------------------------------
// Query key factories
// ---------------------------------------------------------------------------

export const marketKeys = {
  quote: (ticker) => ["market", "quote", ticker],
  batchQuotes: (tickers) => ["market", "quotes", tickers.sort().join(",")],
  ohlcv: (ticker, interval, period) => ["market", "ohlcv", ticker, interval, period],
  news: (ticker) => ["market", "news", ticker],
  sentiment: (ticker) => ["market", "sentiment", ticker],
  calendar: (days) => ["market", "calendar", days],
  watchlists: () => ["watchlists"],
  watchlist: (id) => ["watchlists", id],
};

// ---------------------------------------------------------------------------
// Market queries
// ---------------------------------------------------------------------------

export const useQuote = (ticker) =>
  useQuery({
    queryKey: marketKeys.quote(ticker),
    queryFn: () => getQuote(ticker),
    enabled: !!ticker,
    refetchInterval: 30_000,
    staleTime: 20_000,
  });

export const useBatchQuotes = (tickers) =>
  useQuery({
    queryKey: marketKeys.batchQuotes(tickers),
    queryFn: () => getBatchQuotes(tickers),
    enabled: tickers.length > 0,
    refetchInterval: 30_000,
    staleTime: 20_000,
  });

export const useOHLCV = (ticker, { interval = "1d", period = "6mo" } = {}) =>
  useQuery({
    queryKey: marketKeys.ohlcv(ticker, interval, period),
    queryFn: () => getOHLCV(ticker, { interval, period }),
    enabled: !!ticker,
    staleTime: 5 * 60_000,
  });

export const useNews = (ticker) =>
  useQuery({
    queryKey: marketKeys.news(ticker),
    queryFn: () => getNews(ticker),
    enabled: !!ticker,
    staleTime: 10 * 60_000,
  });

export const useSentiment = (ticker) =>
  useQuery({
    queryKey: marketKeys.sentiment(ticker),
    queryFn: () => getSentiment(ticker),
    enabled: !!ticker,
    staleTime: 10 * 60_000,
  });

export const useCalendar = (daysAhead = 30) =>
  useQuery({
    queryKey: marketKeys.calendar(daysAhead),
    queryFn: () => getCalendar(daysAhead),
    staleTime: 60 * 60_000,
  });

// ---------------------------------------------------------------------------
// Watchlist queries
// ---------------------------------------------------------------------------

export const useWatchlists = () =>
  useQuery({
    queryKey: marketKeys.watchlists(),
    queryFn: listWatchlists,
    refetchInterval: 30_000,
  });

// ---------------------------------------------------------------------------
// Watchlist mutations
// ---------------------------------------------------------------------------

export const useCreateWatchlist = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createWatchlist,
    onSuccess: () => qc.invalidateQueries({ queryKey: marketKeys.watchlists() }),
  });
};

export const useDeleteWatchlist = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteWatchlist,
    onSuccess: () => qc.invalidateQueries({ queryKey: marketKeys.watchlists() }),
  });
};

export const useAddWatchlistItem = (watchlistId) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => addWatchlistItem(watchlistId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: marketKeys.watchlists() }),
  });
};

export const useDeleteWatchlistItem = (watchlistId) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId) => deleteWatchlistItem(watchlistId, itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: marketKeys.watchlists() }),
  });
};
