import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/alternativeDataApi";

export const useAltDataEvents = (params) =>
  useQuery({ queryKey: ["alt-data-events", params], queryFn: () => api.listEvents(params), select: (data) => (Array.isArray(data) ? data : []) });

export const useAltDataEvent = (id) =>
  useQuery({ queryKey: ["alt-data-event", id], queryFn: () => api.getEvent(id), enabled: !!id });

export const useIngestEvent = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.ingestEvent, onSuccess: () => qc.invalidateQueries({ queryKey: ["alt-data-events"] }) });
};

export const useBatchIngest = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.batchIngest, onSuccess: () => qc.invalidateQueries({ queryKey: ["alt-data-events"] }) });
};

export const useSearchEvents = () =>
  useMutation({ mutationFn: api.searchEvents });

export const useTickerTimeline = (ticker, params) =>
  useQuery({ queryKey: ["ticker-timeline", ticker, params], queryFn: () => api.getTickerTimeline(ticker, params), enabled: !!ticker });

export const useTickerSentiment = (ticker) =>
  useQuery({ queryKey: ["ticker-sentiment", ticker], queryFn: () => api.getTickerSentiment(ticker), enabled: !!ticker });

export const useImportanceFeed = (params) =>
  useQuery({ queryKey: ["importance-feed", params], queryFn: () => api.getImportanceFeed(params), select: (data) => (Array.isArray(data) ? data : []) });

export const useAltDataClusters = () =>
  useQuery({ queryKey: ["alt-data-clusters"], queryFn: api.listClusters, select: (data) => (Array.isArray(data) ? data : []) });

export const useBuildClusters = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.buildClusters, onSuccess: () => qc.invalidateQueries({ queryKey: ["alt-data-clusters"] }) });
};
