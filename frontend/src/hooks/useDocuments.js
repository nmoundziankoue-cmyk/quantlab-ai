import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/documentsApi";

export const useDocuments = (params) =>
  useQuery({ queryKey: ["documents", params], queryFn: () => api.listDocuments(params) });

export const useIngestDocument = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.ingestDocument, onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }) });
};

export const useDeleteDocument = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.deleteDocument, onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }) });
};

export const useReindexDocument = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.reindexDocument, onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }) });
};

export const useSearchDocuments = () =>
  useMutation({ mutationFn: api.searchDocuments });

export const useAskDocument = () =>
  useMutation({ mutationFn: api.askDocument });
