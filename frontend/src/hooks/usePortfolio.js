import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addTransaction,
  createPortfolio,
  deletePortfolio,
  deleteTransaction,
  getPortfolioAllocation,
  getPortfolioPerformance,
  getPortfolioSummary,
  listPortfolios,
  listTransactions,
  updatePortfolio,
} from "../api/portfolioApi";

// ---------------------------------------------------------------------------
// Query key factories
// ---------------------------------------------------------------------------

export const portfolioKeys = {
  all: ["portfolios"],
  list: () => [...portfolioKeys.all, "list"],
  summary: (id) => [...portfolioKeys.all, id, "summary"],
  performance: (id) => [...portfolioKeys.all, id, "performance"],
  allocation: (id) => [...portfolioKeys.all, id, "allocation"],
  transactions: (id) => [...portfolioKeys.all, id, "transactions"],
};

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export const usePortfolios = () =>
  useQuery({ queryKey: portfolioKeys.list(), queryFn: listPortfolios });

export const usePortfolioSummary = (id) =>
  useQuery({
    queryKey: portfolioKeys.summary(id),
    queryFn: () => getPortfolioSummary(id),
    enabled: !!id,
    refetchInterval: 60_000,
  });

export const usePortfolioPerformance = (id) =>
  useQuery({
    queryKey: portfolioKeys.performance(id),
    queryFn: () => getPortfolioPerformance(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });

export const usePortfolioAllocation = (id) =>
  useQuery({
    queryKey: portfolioKeys.allocation(id),
    queryFn: () => getPortfolioAllocation(id),
    enabled: !!id,
    refetchInterval: 60_000,
  });

export const useTransactions = (id) =>
  useQuery({
    queryKey: portfolioKeys.transactions(id),
    queryFn: () => listTransactions(id),
    enabled: !!id,
  });

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export const useCreatePortfolio = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createPortfolio,
    onSuccess: () => qc.invalidateQueries({ queryKey: portfolioKeys.list() }),
  });
};

export const useUpdatePortfolio = (id) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => updatePortfolio(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: portfolioKeys.all }),
  });
};

export const useDeletePortfolio = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deletePortfolio,
    onSuccess: () => qc.invalidateQueries({ queryKey: portfolioKeys.list() }),
  });
};

export const useAddTransaction = (portfolioId) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => addTransaction(portfolioId, payload),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: portfolioKeys.all }),
  });
};

export const useDeleteTransaction = (portfolioId) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (transactionId) => deleteTransaction(portfolioId, transactionId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: portfolioKeys.all }),
  });
};
