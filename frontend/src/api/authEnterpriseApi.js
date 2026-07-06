import axios from "axios";

const _api = axios.create({ baseURL: "", timeout: 15_000 });

export const enterpriseLogin = (data) =>
  _api.post("/auth/enterprise/login", data).then((r) => r.data);

export const refreshTokens = (refreshToken) =>
  _api.post("/auth/enterprise/refresh", { refresh_token: refreshToken }).then((r) => r.data);

export const listSessions = (token) =>
  _api.get("/auth/enterprise/sessions", { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const revokeSession = (sessionId, token) =>
  _api.delete(`/auth/enterprise/sessions/${sessionId}`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const revokeAllSessions = (token) =>
  _api.delete("/auth/enterprise/sessions", { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const getLoginHistory = (token, limit = 50) =>
  _api.get("/auth/enterprise/login-history", { params: { limit }, headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const setupMFA = (token) =>
  _api.post("/auth/enterprise/mfa/setup", {}, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const enableMFA = (code, token) =>
  _api.post("/auth/enterprise/mfa/enable", { code }, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const disableMFA = (code, token) =>
  _api.post("/auth/enterprise/mfa/disable", { code }, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const getMFAStatus = (token) =>
  _api.get("/auth/enterprise/mfa/status", { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);
