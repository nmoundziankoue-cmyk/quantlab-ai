const BASE = "http://localhost:8001/knowledge-graph";

export const knowledgeGraphApi = {
  createEntity: (body) => fetch(`${BASE}/entities`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  listEntities: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${BASE}/entities${qs ? `?${qs}` : ""}`).then((r) => r.json());
  },
  getEntity: (id) => fetch(`${BASE}/entities/${id}`).then((r) => r.json()),
  deleteEntity: (id) => fetch(`${BASE}/entities/${id}`, { method: "DELETE" }).then((r) => r.json()),
  createEdge: (body) => fetch(`${BASE}/edges`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  listEdges: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${BASE}/edges${qs ? `?${qs}` : ""}`).then((r) => r.json());
  },
  getNeighbors: (id, depth = 1) => fetch(`${BASE}/entities/${id}/neighbors?depth=${depth}`).then((r) => r.json()),
  getFullGraph: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${BASE}/graph${qs ? `?${qs}` : ""}`).then((r) => r.json());
  },
  extractEntities: (text, persist = false) => fetch(`${BASE}/extract`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, persist }) }).then((r) => r.json()),
};
