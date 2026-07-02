import client from "./client";

export const listDocuments = (params) =>
  client.get("/documents", { params }).then((r) => r.data);

export const ingestDocument = (payload) =>
  client.post("/documents", payload).then((r) => r.data);

export const deleteDocument = (id) =>
  client.delete(`/documents/${id}`);

export const reindexDocument = (id) =>
  client.post(`/documents/${id}/reindex`).then((r) => r.data);

export const searchDocuments = (payload) =>
  client.post("/documents/search", payload).then((r) => r.data);

export const askDocument = (payload) =>
  client.post("/documents/ask", payload).then((r) => r.data);
