import axios from "axios";

const API = "http://localhost:8001";

export const enterpriseLogin = (data) =>
  axios.post(`${API}/auth/enterprise/login`, data).then((r) => r.data);

export const refreshTokens = (refreshToken) =>
  axios.post(`${API}/auth/enterprise/refresh`, { refresh_token: refreshToken }).then((r) => r.data);

export const listSessions = (token) =>
  axios.get(`${API}/auth/enterprise/sessions`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const revokeSession = (sessionId, token) =>
  axios.delete(`${API}/auth/enterprise/sessions/${sessionId}`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const revokeAllSessions = (token) =>
  axios.delete(`${API}/auth/enterprise/sessions`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const getLoginHistory = (token, limit = 50) =>
  axios.get(`${API}/auth/enterprise/login-history`, { params: { limit }, headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const setupMFA = (token) =>
  axios.post(`${API}/auth/enterprise/mfa/setup`, {}, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const enableMFA = (code, token) =>
  axios.post(`${API}/auth/enterprise/mfa/enable`, { code }, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const disableMFA = (code, token) =>
  axios.post(`${API}/auth/enterprise/mfa/disable`, { code }, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);

export const getMFAStatus = (token) =>
  axios.get(`${API}/auth/enterprise/mfa/status`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data);
