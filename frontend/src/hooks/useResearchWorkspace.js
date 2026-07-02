import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/researchWorkspaceApi";

export const useProjects = (params) =>
  useQuery({ queryKey: ["projects", params], queryFn: () => api.listProjects(params) });

export const useProject = (id) =>
  useQuery({ queryKey: ["project", id], queryFn: () => api.getProject(id), enabled: !!id });

export const useCreateProject = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.createProject, onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }) });
};

export const useUpdateProject = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, ...d }) => api.updateProject(id, d), onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }) });
};

export const useDeleteProject = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.deleteProject, onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }) });
};

export const useFolders = (projectId) =>
  useQuery({ queryKey: ["folders", projectId], queryFn: () => api.listFolders(projectId), enabled: !!projectId });

export const useCreateFolder = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.createFolder, onSuccess: (_, v) => qc.invalidateQueries({ queryKey: ["folders", v.project_id] }) });
};

export const useNotes = (projectId, params) =>
  useQuery({ queryKey: ["notes", projectId, params], queryFn: () => api.listNotes(projectId, params), enabled: !!projectId });

export const useCreateNote = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.createNote, onSuccess: () => qc.invalidateQueries({ queryKey: ["notes"] }) });
};

export const useUpdateNote = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, ...d }) => api.updateNote(id, d), onSuccess: () => qc.invalidateQueries({ queryKey: ["notes"] }) });
};

export const useDeleteNote = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.deleteNote, onSuccess: () => qc.invalidateQueries({ queryKey: ["notes"] }) });
};

export const useBookmarks = (params) =>
  useQuery({ queryKey: ["bookmarks", params], queryFn: () => api.listBookmarks(params) });

export const useCreateBookmark = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.createBookmark, onSuccess: () => qc.invalidateQueries({ queryKey: ["bookmarks"] }) });
};

export const useDeleteBookmark = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.deleteBookmark, onSuccess: () => qc.invalidateQueries({ queryKey: ["bookmarks"] }) });
};

export const useSavedSearches = () =>
  useQuery({ queryKey: ["saved-searches"], queryFn: api.listSavedSearches });

export const useCreateSavedSearch = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.createSavedSearch, onSuccess: () => qc.invalidateQueries({ queryKey: ["saved-searches"] }) });
};

export const useReportDrafts = (params) =>
  useQuery({ queryKey: ["report-drafts", params], queryFn: () => api.listReportDrafts(params) });

export const useCreateReportDraft = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.createReportDraft, onSuccess: () => qc.invalidateQueries({ queryKey: ["report-drafts"] }) });
};

export const useUpdateReportDraft = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, ...d }) => api.updateReportDraft(id, d), onSuccess: () => qc.invalidateQueries({ queryKey: ["report-drafts"] }) });
};

export const usePinnedItems = () =>
  useQuery({ queryKey: ["pinned-items"], queryFn: api.listPinnedItems });

export const useCreatePinnedItem = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.createPinnedItem, onSuccess: () => qc.invalidateQueries({ queryKey: ["pinned-items"] }) });
};

export const useDeletePinnedItem = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.deletePinnedItem, onSuccess: () => qc.invalidateQueries({ queryKey: ["pinned-items"] }) });
};

export const useRecentActivity = (limit = 20) =>
  useQuery({ queryKey: ["recent-activity", limit], queryFn: () => api.getRecentActivity(limit) });

export const useWorkspaceSearch = (query, limit = 30) =>
  useQuery({ queryKey: ["workspace-search", query], queryFn: () => api.workspaceSearch(query, limit), enabled: !!query && query.length > 1 });
