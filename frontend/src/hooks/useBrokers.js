import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createBrokerConnection,
  deleteBrokerConnection,
  getBrokerConnection,
  listBrokerConnections,
  listBrokerTypes,
  testBrokerConnection,
  updateBrokerConnection,
} from "../api/tradingApi";

export const useBrokerTypes = () =>
  useQuery({
    queryKey: ["broker-types"],
    queryFn: listBrokerTypes,
    staleTime: Infinity,
    select: (data) => (Array.isArray(data) ? data : []),
  });

export const useBrokerConnections = () =>
  useQuery({
    queryKey: ["broker-connections"],
    queryFn: listBrokerConnections,
    refetchInterval: 30000,
    select: (data) => (Array.isArray(data) ? data : []),
  });

export const useBrokerConnection = (connectionId) =>
  useQuery({
    queryKey: ["broker-connection", connectionId],
    queryFn: () => getBrokerConnection(connectionId),
    enabled: !!connectionId,
  });

export const useCreateBrokerConnection = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => createBrokerConnection(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["broker-connections"] }),
  });
};

export const useUpdateBrokerConnection = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ connectionId, data }) => updateBrokerConnection(connectionId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["broker-connections"] }),
  });
};

export const useDeleteBrokerConnection = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectionId) => deleteBrokerConnection(connectionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["broker-connections"] }),
  });
};

export const useTestBrokerConnection = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectionId) => testBrokerConnection(connectionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["broker-connections"] }),
  });
};
