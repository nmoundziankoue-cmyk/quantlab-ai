import axios from "axios";

const API = "http://localhost:8001";

export const getSystemHealth = () =>
  axios.get(`${API}/system/health/detailed`).then((r) => r.data);

export const getSystemInfo = () =>
  axios.get(`${API}/system/info`).then((r) => r.data);

export const listTasks = (params = {}) =>
  axios.get(`${API}/system/tasks`, { params }).then((r) => r.data);

export const getTask = (id) =>
  axios.get(`${API}/system/tasks/${id}`).then((r) => r.data);

export const getRateLimitStats = () =>
  axios.get(`${API}/system/rate-limits`).then((r) => r.data);
