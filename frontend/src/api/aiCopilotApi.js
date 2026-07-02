import client from "./client";

// Sessions
export const listCopilotSessions = (params) =>
  client.get("/copilot/sessions", { params }).then((r) => r.data);

export const getCopilotSession = (id) =>
  client.get(`/copilot/sessions/${id}`).then((r) => r.data);

export const createCopilotSession = (payload) =>
  client.post("/copilot/sessions", payload).then((r) => r.data);

// Messages
export const sendMessage = (sessionId, payload) =>
  client.post(`/copilot/sessions/${sessionId}/messages`, payload).then((r) => r.data);

// Generation
export const generateThesis = (payload) =>
  client.post("/copilot/generate/thesis", payload).then((r) => r.data);

export const generateMemo = (payload) =>
  client.post("/copilot/generate/memo", payload).then((r) => r.data);

export const generateReport = (payload) =>
  client.post("/copilot/generate/report", payload).then((r) => r.data);

// Templates
export const listPromptTemplates = () =>
  client.get("/copilot/templates").then((r) => r.data);
