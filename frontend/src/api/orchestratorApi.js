const BASE = "http://localhost:8001/orchestrator";

export const orchestratorApi = {
  createWorkflow: (body) => fetch(`${BASE}/workflows`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  listWorkflows: (status) => fetch(`${BASE}/workflows${status ? `?status=${status}` : ""}`).then((r) => r.json()),
  getWorkflow: (id) => fetch(`${BASE}/workflows/${id}`).then((r) => r.json()),
  executeWorkflow: (id, body) => fetch(`${BASE}/workflows/${id}/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  getTimeline: (id) => fetch(`${BASE}/workflows/${id}/timeline`).then((r) => r.json()),
  cancelWorkflow: (id) => fetch(`${BASE}/workflows/${id}/cancel`, { method: "POST" }).then((r) => r.json()),
  deleteWorkflow: (id) => fetch(`${BASE}/workflows/${id}`, { method: "DELETE" }).then((r) => r.json()),
  getHealth: () => fetch(`${BASE}/health`).then((r) => r.json()),
  quickRun: (ticker, agentIds) => fetch(`${BASE}/quick-run?ticker=${ticker}&agent_ids=${agentIds}`).then((r) => r.json()),
};
