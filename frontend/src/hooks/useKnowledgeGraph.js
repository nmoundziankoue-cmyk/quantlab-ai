import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knowledgeGraphApi } from "../api/knowledgeGraphApi";

export function useEntities(params = {}) {
  return useQuery({
    queryKey: ["kg-entities", params],
    queryFn: () => knowledgeGraphApi.listEntities(params),
  });
}

export function useFullGraph(params = {}) {
  return useQuery({
    queryKey: ["kg-full-graph", params],
    queryFn: () => knowledgeGraphApi.getFullGraph(params),
  });
}

export function useCreateEntity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: knowledgeGraphApi.createEntity,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kg-entities"] }),
  });
}

export function useDeleteEntity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: knowledgeGraphApi.deleteEntity,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kg-entities"] }),
  });
}

export function useCreateEdge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: knowledgeGraphApi.createEdge,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kg-full-graph"] }),
  });
}

export function useExtractEntities() {
  return useMutation({ mutationFn: ({ text, persist }) => knowledgeGraphApi.extractEntities(text, persist) });
}

export function useEntityNeighbors(id, depth = 1, enabled = true) {
  return useQuery({
    queryKey: ["kg-neighbors", id, depth],
    queryFn: () => knowledgeGraphApi.getNeighbors(id, depth),
    enabled: !!id && enabled,
  });
}
