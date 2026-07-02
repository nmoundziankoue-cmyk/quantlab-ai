/**
 * TanStack Query hooks for M4 Analytics endpoints.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import * as api from "../api/analyticsApi";

// ── Risk Metrics ───────────────────────────────────────────────────────────

export const useRiskMetrics = (portfolioId, params, enabled = true) =>
  useMutation({
    mutationFn: () => api.fetchRiskMetrics(portfolioId, params),
  });

// ── Optimization ───────────────────────────────────────────────────────────

export const useOptimizationMethods = (portfolioId) =>
  useQuery({
    queryKey: ["analytics", portfolioId, "optimize-methods"],
    queryFn: () => api.fetchOptimizationMethods(portfolioId),
    enabled: !!portfolioId,
    staleTime: Infinity,
  });

export const useRunOptimization = (portfolioId) =>
  useMutation({
    mutationFn: (params) => api.fetchOptimization(portfolioId, params),
  });

export const useEfficientFrontier = (portfolioId) =>
  useMutation({
    mutationFn: ({ params, nPoints }) => api.fetchEfficientFrontier(portfolioId, params, nPoints),
  });

// ── Stress Testing ─────────────────────────────────────────────────────────

export const useStressScenarios = (portfolioId) =>
  useQuery({
    queryKey: ["analytics", portfolioId, "stress-scenarios"],
    queryFn: () => api.fetchStressScenarios(portfolioId),
    enabled: !!portfolioId,
    staleTime: Infinity,
  });

export const useAllStressTests = (portfolioId) =>
  useMutation({
    mutationFn: () => api.fetchAllStressTests(portfolioId),
  });

export const useRunStressScenario = (portfolioId) =>
  useMutation({
    mutationFn: (scenarioKey) => api.fetchStressScenario(portfolioId, scenarioKey),
  });

export const useRunCustomStress = (portfolioId) =>
  useMutation({
    mutationFn: (body) => api.runCustomStress(portfolioId, body),
  });

// ── Monte Carlo ────────────────────────────────────────────────────────────

export const useRunMonteCarlo = (portfolioId) =>
  useMutation({
    mutationFn: (params) => api.runMonteCarlo(portfolioId, params),
  });

// ── Factor Analytics ───────────────────────────────────────────────────────

export const useFactorExposures = (portfolioId) =>
  useMutation({
    mutationFn: (lookbackDays) => api.fetchFactorExposures(portfolioId, lookbackDays),
  });

// ── Correlation ────────────────────────────────────────────────────────────

export const useCorrelationMatrix = (portfolioId) =>
  useMutation({
    mutationFn: ({ lookbackDays, method }) => api.fetchCorrelationMatrix(portfolioId, lookbackDays, method),
  });

export const useRollingCorrelation = (portfolioId) =>
  useMutation({
    mutationFn: (body) => api.fetchRollingCorrelation(portfolioId, body),
  });

export const useMST = (portfolioId) =>
  useMutation({
    mutationFn: (lookbackDays) => api.fetchMST(portfolioId, lookbackDays),
  });

export const useClusters = (portfolioId) =>
  useMutation({
    mutationFn: ({ lookbackDays, nClusters }) => api.fetchClusters(portfolioId, lookbackDays, nClusters),
  });
