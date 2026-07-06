import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/notificationsApi";

export const useNotificationLogs = (params = {}) =>
  useQuery({ queryKey: ["notification-logs", params], queryFn: () => api.listNotificationLogs(params), refetchInterval: 10000, select: (data) => (Array.isArray(data) ? data : []) });

export const useNotificationTemplates = (params = {}) =>
  useQuery({ queryKey: ["notification-templates", params], queryFn: () => api.listTemplates(params), select: (data) => (Array.isArray(data) ? data : []) });

export const useNotificationChannels = () =>
  useQuery({ queryKey: ["notification-channels"], queryFn: api.listChannels, select: (data) => (Array.isArray(data) ? data : []) });

export const useSendNotification = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.sendNotification,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-logs"] }),
  });
};

export const useCreateTemplate = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createTemplate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-templates"] }),
  });
};

export const useDeleteTemplate = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteTemplate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-templates"] }),
  });
};
