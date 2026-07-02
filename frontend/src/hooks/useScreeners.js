import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/screenerApi";

export const useScreenerTypes = () =>
  useQuery({ queryKey: ["screener-types"], queryFn: api.getScreenerTypes, staleTime: Infinity });

export const useScreeners = () =>
  useQuery({ queryKey: ["screeners"], queryFn: api.listScreeners });

export const useScreener = (id) =>
  useQuery({ queryKey: ["screener", id], queryFn: () => api.getScreener(id), enabled: !!id });

export const useCreateScreener = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.createScreener, onSuccess: () => qc.invalidateQueries({ queryKey: ["screeners"] }) });
};

export const useUpdateScreener = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, ...d }) => api.updateScreener(id, d), onSuccess: () => qc.invalidateQueries({ queryKey: ["screeners"] }) });
};

export const useDeleteScreener = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.deleteScreener, onSuccess: () => qc.invalidateQueries({ queryKey: ["screeners"] }) });
};

export const useRunScreener = () =>
  useMutation({ mutationFn: ({ payload, save }) => api.runScreener(payload, save) });

export const useScreenerResults = (id) =>
  useQuery({ queryKey: ["screener-results", id], queryFn: () => api.getScreenerResults(id), enabled: !!id });
