import client from "./client";

// Projects
export const listProjects = (params) =>
  client.get("/workspace/projects", { params }).then((r) => r.data);
export const getProject = (id) =>
  client.get(`/workspace/projects/${id}`).then((r) => r.data);
export const createProject = (payload) =>
  client.post("/workspace/projects", payload).then((r) => r.data);
export const updateProject = (id, payload) =>
  client.patch(`/workspace/projects/${id}`, payload).then((r) => r.data);
export const deleteProject = (id) =>
  client.delete(`/workspace/projects/${id}`);

// Folders
export const listFolders = (projectId) =>
  client.get(`/workspace/projects/${projectId}/folders`).then((r) => r.data);
export const createFolder = (payload) =>
  client.post("/workspace/folders", payload).then((r) => r.data);
export const updateFolder = (id, payload) =>
  client.patch(`/workspace/folders/${id}`, payload).then((r) => r.data);
export const deleteFolder = (id) =>
  client.delete(`/workspace/folders/${id}`);

// Notes
export const listNotes = (projectId, params) =>
  client.get(`/workspace/projects/${projectId}/notes`, { params }).then((r) => r.data);
export const getNote = (id) =>
  client.get(`/workspace/notes/${id}`).then((r) => r.data);
export const createNote = (payload) =>
  client.post("/workspace/notes", payload).then((r) => r.data);
export const updateNote = (id, payload) =>
  client.patch(`/workspace/notes/${id}`, payload).then((r) => r.data);
export const deleteNote = (id) =>
  client.delete(`/workspace/notes/${id}`);

// Bookmarks
export const listBookmarks = (params) =>
  client.get("/workspace/bookmarks", { params }).then((r) => r.data);
export const createBookmark = (payload) =>
  client.post("/workspace/bookmarks", payload).then((r) => r.data);
export const deleteBookmark = (id) =>
  client.delete(`/workspace/bookmarks/${id}`);

// Saved Searches
export const listSavedSearches = () =>
  client.get("/workspace/saved-searches").then((r) => r.data);
export const createSavedSearch = (payload) =>
  client.post("/workspace/saved-searches", payload).then((r) => r.data);
export const deleteSavedSearch = (id) =>
  client.delete(`/workspace/saved-searches/${id}`);

// Sessions
export const listSessions = (params) =>
  client.get("/workspace/sessions", { params }).then((r) => r.data);
export const createSession = (payload) =>
  client.post("/workspace/sessions", payload).then((r) => r.data);
export const endSession = (id) =>
  client.post(`/workspace/sessions/${id}/end`).then((r) => r.data);

// Report Drafts
export const listReportDrafts = (params) =>
  client.get("/workspace/report-drafts", { params }).then((r) => r.data);
export const getReportDraft = (id) =>
  client.get(`/workspace/report-drafts/${id}`).then((r) => r.data);
export const createReportDraft = (payload) =>
  client.post("/workspace/report-drafts", payload).then((r) => r.data);
export const updateReportDraft = (id, payload) =>
  client.patch(`/workspace/report-drafts/${id}`, payload).then((r) => r.data);
export const deleteReportDraft = (id) =>
  client.delete(`/workspace/report-drafts/${id}`);

// Pinned Items
export const listPinnedItems = () =>
  client.get("/workspace/pinned").then((r) => r.data);
export const createPinnedItem = (payload) =>
  client.post("/workspace/pinned", payload).then((r) => r.data);
export const deletePinnedItem = (id) =>
  client.delete(`/workspace/pinned/${id}`);

// Recent Activity
export const getRecentActivity = (limit = 20) =>
  client.get("/workspace/activity", { params: { limit } }).then((r) => r.data);

// Search
export const workspaceSearch = (query, limit = 30) =>
  client.get("/workspace/search", { params: { q: query, limit } }).then((r) => r.data);
