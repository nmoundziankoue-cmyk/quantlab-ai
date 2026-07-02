import client from "./client";

export const listAgents = () =>
  client.get("/agents").then((r) => r.data);

export const getAgentCapabilities = (agentId) =>
  client.get(`/agents/${agentId}/capabilities`).then((r) => r.data);

export const runAgent = (payload) =>
  client.post("/agents/run", payload).then((r) => r.data);

export const runWorkflow = (payload) =>
  client.post("/agents/workflow", payload).then((r) => r.data);
