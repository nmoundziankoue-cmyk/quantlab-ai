import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createPaperAccount,
  getPaperAccount,
  listPaperAccounts,
  listPaperPositions,
  listPaperTrades,
  refreshPaperPrices,
  submitPaperOrder,
  updatePaperAccount,
} from "../api/tradingApi";

export const usePaperAccounts = () =>
  useQuery({
    queryKey: ["paper-accounts"],
    queryFn: () => listPaperAccounts(),
  });

export const usePaperAccount = (accountId) =>
  useQuery({
    queryKey: ["paper-account", accountId],
    queryFn: () => getPaperAccount(accountId),
    enabled: !!accountId,
    refetchInterval: 10000,
  });

export const usePaperPositions = (accountId) =>
  useQuery({
    queryKey: ["paper-positions", accountId],
    queryFn: () => listPaperPositions(accountId),
    enabled: !!accountId,
    refetchInterval: 10000,
  });

export const usePaperTrades = (accountId, params = {}) =>
  useQuery({
    queryKey: ["paper-trades", accountId, params],
    queryFn: () => listPaperTrades(accountId, params),
    enabled: !!accountId,
  });

export const useCreatePaperAccount = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => createPaperAccount(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["paper-accounts"] }),
  });
};

export const useUpdatePaperAccount = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, data }) => updatePaperAccount(accountId, data),
    onSuccess: (_, { accountId }) => {
      qc.invalidateQueries({ queryKey: ["paper-account", accountId] });
      qc.invalidateQueries({ queryKey: ["paper-accounts"] });
    },
  });
};

export const useRefreshPaperPrices = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (accountId) => refreshPaperPrices(accountId),
    onSuccess: (_, accountId) => {
      qc.invalidateQueries({ queryKey: ["paper-account", accountId] });
      qc.invalidateQueries({ queryKey: ["paper-positions", accountId] });
    },
  });
};

export const useSubmitPaperOrder = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, data }) => submitPaperOrder(accountId, data),
    onSuccess: (_, { accountId }) => {
      qc.invalidateQueries({ queryKey: ["paper-account", accountId] });
      qc.invalidateQueries({ queryKey: ["paper-positions", accountId] });
      qc.invalidateQueries({ queryKey: ["paper-trades", accountId] });
      qc.invalidateQueries({ queryKey: ["orders"] });
    },
  });
};
