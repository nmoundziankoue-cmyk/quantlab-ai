import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAlert,
  deleteAlert,
  getAlert,
  listAlertTypes,
  listAlerts,
  updateAlert,
} from "../api/tradingApi";

export const useAlertTypes = () =>
  useQuery({
    queryKey: ["alert-types"],
    queryFn: listAlertTypes,
    staleTime: Infinity,
  });

export const useAlerts = (params = {}) =>
  useQuery({
    queryKey: ["alerts", params],
    queryFn: () => listAlerts(params),
  });

export const useAlert = (alertId) =>
  useQuery({
    queryKey: ["alert", alertId],
    queryFn: () => getAlert(alertId),
    enabled: !!alertId,
  });

export const useCreateAlert = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => createAlert(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
};

export const useUpdateAlert = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, data }) => updateAlert(alertId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
};

export const useDeleteAlert = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertId) => deleteAlert(alertId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
};
