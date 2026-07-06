import client from "./client";

const BASE = "/orchestrator";

export const orchestratorApi = {
  createWorkflow: (body) => client.post(`${BASE}/workflows`, body).then((r) => r.data),
  listWorkflows: (status) => client.get(`${BASE}/workflows${status ? `?status=${status}` : ""}`).then((r) => r.data),
  getWorkflow: (id) => client.get(`${BASE}/workflows/${id}`).then((r) => r.data),
  executeWorkflow: (id, body) => client.post(`${BASE}/workflows/${id}/execute`, body).then((r) => r.data),
  getTimeline: (id) => client.get(`${BASE}/workflows/${id}/timeline`).then((r) => r.data),
  cancelWorkflow: (id) => client.post(`${BASE}/workflows/${id}/cancel`).then((r) => r.data),
  deleteWorkflow: (id) => client.delete(`${BASE}/workflows/${id}`).then((r) => r.data),
  getHealth: () => client.get(`${BASE}/health`).then((r) => r.data),
  quickRun: (ticker, agentIds) => client.get(`${BASE}/quick-run`, { params: { ticker, agent_ids: agentIds } }).then((r) => r.data),
};
