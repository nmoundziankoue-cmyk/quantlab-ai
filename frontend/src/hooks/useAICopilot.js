import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/aiCopilotApi";

export const useCopilotSessions = (params) =>
  useQuery({ queryKey: ["copilot-sessions", params], queryFn: () => api.listCopilotSessions(params), select: (data) => (Array.isArray(data) ? data : []) });

export const useCopilotSession = (id) =>
  useQuery({ queryKey: ["copilot-session", id], queryFn: () => api.getCopilotSession(id), enabled: !!id });

export const useCreateCopilotSession = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.createCopilotSession, onSuccess: () => qc.invalidateQueries({ queryKey: ["copilot-sessions"] }) });
};

export const useSendMessage = (sessionId) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => api.sendMessage(sessionId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["copilot-session", sessionId] }),
  });
};

export const useGenerateThesis = () =>
  useMutation({ mutationFn: api.generateThesis });

export const useGenerateMemo = () =>
  useMutation({ mutationFn: api.generateMemo });

export const useGenerateReport = () =>
  useMutation({ mutationFn: api.generateReport });

export const usePromptTemplates = () =>
  useQuery({ queryKey: ["prompt-templates"], queryFn: api.listPromptTemplates, staleTime: Infinity, select: (data) => (Array.isArray(data) ? data : []) });
