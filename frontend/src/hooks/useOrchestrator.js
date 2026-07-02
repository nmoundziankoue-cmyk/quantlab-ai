import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { orchestratorApi } from "../api/orchestratorApi";

export function useWorkflows(status) {
  return useQuery({
    queryKey: ["workflows", status],
    queryFn: () => orchestratorApi.listWorkflows(status),
    refetchInterval: 5000,
  });
}

export function useWorkflow(id) {
  return useQuery({
    queryKey: ["workflow", id],
    queryFn: () => orchestratorApi.getWorkflow(id),
    enabled: !!id,
  });
}

export function useOrchestratorHealth() {
  return useQuery({
    queryKey: ["orchestrator-health"],
    queryFn: orchestratorApi.getHealth,
    refetchInterval: 10000,
  });
}

export function useCreateWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: orchestratorApi.createWorkflow,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}

export function useExecuteWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }) => orchestratorApi.executeWorkflow(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}

export function useCancelWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: orchestratorApi.cancelWorkflow,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}

export function useDeleteWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: orchestratorApi.deleteWorkflow,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}

export function useQuickRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ticker, agentIds }) => orchestratorApi.quickRun(ticker, agentIds),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}
