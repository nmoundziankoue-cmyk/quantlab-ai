import client from "./client";

export const getSystemHealth = () =>
  client.get("/system/health/detailed").then((r) => r.data);

export const getSystemInfo = () =>
  client.get("/system/info").then((r) => r.data);

export const listTasks = (params = {}) =>
  client.get("/system/tasks", { params }).then((r) => r.data);

export const getTask = (id) =>
  client.get(`/system/tasks/${id}`).then((r) => r.data);

export const getRateLimitStats = () =>
  client.get("/system/rate-limits").then((r) => r.data);
