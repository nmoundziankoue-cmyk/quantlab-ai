import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  cancelOrder,
  createBasketOrder,
  createOrder,
  getBasketOrders,
  getOrder,
  getOrderAuditLog,
  listOrders,
  modifyOrder,
  previewOrder,
  submitOrder,
} from "../api/tradingApi";

export const useOrders = (params = {}) =>
  useQuery({
    queryKey: ["orders", params],
    queryFn: () => listOrders(params),
    refetchInterval: 5000,
  });

export const useOrder = (orderId) =>
  useQuery({
    queryKey: ["order", orderId],
    queryFn: () => getOrder(orderId),
    enabled: !!orderId,
    refetchInterval: 3000,
  });

export const useOrderAuditLog = (orderId) =>
  useQuery({
    queryKey: ["order-audit", orderId],
    queryFn: () => getOrderAuditLog(orderId),
    enabled: !!orderId,
  });

export const useBasketOrders = (basketId) =>
  useQuery({
    queryKey: ["basket", basketId],
    queryFn: () => getBasketOrders(basketId),
    enabled: !!basketId,
  });

export const useCreateOrder = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ data, options }) => createOrder(data, options),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });
};

export const useSubmitOrder = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderId) => submitOrder(orderId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });
};

export const useModifyOrder = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ orderId, data }) => modifyOrder(orderId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });
};

export const useCancelOrder = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ orderId, reason }) => cancelOrder(orderId, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });
};

export const usePreviewOrder = () =>
  useMutation({
    mutationFn: (data) => previewOrder(data),
  });

export const useCreateBasketOrder = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ data, options }) => createBasketOrder(data, options),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });
};
