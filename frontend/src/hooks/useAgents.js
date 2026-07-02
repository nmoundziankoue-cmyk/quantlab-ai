import { useMutation, useQuery } from "@tanstack/react-query";
import * as api from "../api/agentsApi";

export const useAgents = () =>
  useQuery({ queryKey: ["agents"], queryFn: api.listAgents, staleTime: Infinity });

export const useAgentCapabilities = (agentId) =>
  useQuery({ queryKey: ["agent-capabilities", agentId], queryFn: () => api.getAgentCapabilities(agentId), enabled: !!agentId, staleTime: Infinity });

export const useRunAgent = () =>
  useMutation({ mutationFn: api.runAgent });

export const useRunWorkflow = () =>
  useMutation({ mutationFn: api.runWorkflow });
