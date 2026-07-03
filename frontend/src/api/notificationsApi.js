import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

export const sendNotification = (data) =>
  axios.post(`${API}/notifications/send`, data).then((r) => r.data);

export const sendFromTemplate = (data) =>
  axios.post(`${API}/notifications/send-template`, data).then((r) => r.data);

export const listNotificationLogs = (params = {}) =>
  axios.get(`${API}/notifications/logs`, { params }).then((r) => r.data);

export const getNotificationLog = (id) =>
  axios.get(`${API}/notifications/logs/${id}`).then((r) => r.data);

export const listTemplates = (params = {}) =>
  axios.get(`${API}/notifications/templates`, { params }).then((r) => r.data);

export const getTemplate = (id) =>
  axios.get(`${API}/notifications/templates/${id}`).then((r) => r.data);

export const createTemplate = (data) =>
  axios.post(`${API}/notifications/templates`, data).then((r) => r.data);

export const updateTemplate = (id, data) =>
  axios.put(`${API}/notifications/templates/${id}`, data).then((r) => r.data);

export const deleteTemplate = (id) =>
  axios.delete(`${API}/notifications/templates/${id}`).then((r) => r.data);

export const listChannels = () =>
  axios.get(`${API}/notifications/channels`).then((r) => r.data);
