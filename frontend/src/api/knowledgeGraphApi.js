import client from "./client";

const BASE = "/knowledge-graph";

export const knowledgeGraphApi = {
  createEntity: (body) => client.post(`${BASE}/entities`, body).then((r) => r.data),
  listEntities: (params = {}) => client.get(`${BASE}/entities`, { params }).then((r) => r.data),
  getEntity: (id) => client.get(`${BASE}/entities/${id}`).then((r) => r.data),
  deleteEntity: (id) => client.delete(`${BASE}/entities/${id}`).then((r) => r.data),
  createEdge: (body) => client.post(`${BASE}/edges`, body).then((r) => r.data),
  listEdges: (params = {}) => client.get(`${BASE}/edges`, { params }).then((r) => r.data),
  getNeighbors: (id, depth = 1) => client.get(`${BASE}/entities/${id}/neighbors`, { params: { depth } }).then((r) => r.data),
  getFullGraph: (params = {}) => client.get(`${BASE}/graph`, { params }).then((r) => r.data),
  extractEntities: (text, persist = false) => client.post(`${BASE}/extract`, { text, persist }).then((r) => r.data),
};
