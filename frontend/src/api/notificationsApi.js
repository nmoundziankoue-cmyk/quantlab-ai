import client from "./client";

export const sendNotification = (data) =>
  client.post("/notifications/send", data).then((r) => r.data);

export const sendFromTemplate = (data) =>
  client.post("/notifications/send-template", data).then((r) => r.data);

export const listNotificationLogs = (params = {}) =>
  client.get("/notifications/logs", { params }).then((r) => r.data);

export const getNotificationLog = (id) =>
  client.get(`/notifications/logs/${id}`).then((r) => r.data);

export const listTemplates = (params = {}) =>
  client.get("/notifications/templates", { params }).then((r) => r.data);

export const getTemplate = (id) =>
  client.get(`/notifications/templates/${id}`).then((r) => r.data);

export const createTemplate = (data) =>
  client.post("/notifications/templates", data).then((r) => r.data);

export const updateTemplate = (id, data) =>
  client.put(`/notifications/templates/${id}`, data).then((r) => r.data);

export const deleteTemplate = (id) =>
  client.delete(`/notifications/templates/${id}`).then((r) => r.data);

export const listChannels = () =>
  client.get("/notifications/channels").then((r) => r.data);
