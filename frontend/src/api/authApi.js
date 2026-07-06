import axios from "axios";
import { formatApiError } from "../utils/formatApiError";

const BASE = "/auth";

// Standalone client — no auth-header injection (used for auth endpoints themselves).
const _client = axios.create({
  baseURL: "",
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

_client.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err.response?.data?.detail ?? err.message ?? "Unknown error";
    return Promise.reject(new Error(formatApiError(detail, "Unknown error")));
  }
);

export const authApi = {
  register: (body) => _client.post("/auth/register", body).then((r) => r.data),
  login: (body) => _client.post("/auth/login", body).then((r) => r.data),
  enterpriseLogin: (body) => _client.post("/auth/enterprise/login", body).then((r) => r.data),
  verifyToken: (token) => _client.post("/auth/verify-token", { token }).then((r) => r.data),
  refresh: (refresh_token) => _client.post("/auth/refresh", { refresh_token }).then((r) => r.data),
  logout: (token) =>
    _client
      .post("/auth/logout", {}, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.data)
      .catch(() => ({ logged_out: true })),
  me: (token) =>
    _client.get("/auth/me", { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data),

  // Legacy fetch-based helpers (kept for backwards compat with existing pages)
  listUsers: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${BASE}/users${qs ? `?${qs}` : ""}`).then((r) => r.json());
  },
  getUser: (id) => fetch(`${BASE}/users/${id}`).then((r) => r.json()),
  updateUser: (id, body) =>
    fetch(`${BASE}/users/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  createTeam: (body) =>
    fetch(`${BASE}/teams`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  listTeams: () => fetch(`${BASE}/teams`).then((r) => r.json()),
  getTeam: (id) => fetch(`${BASE}/teams/${id}`).then((r) => r.json()),
  addTeamMember: (teamId, body) =>
    fetch(`${BASE}/teams/${teamId}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  listAuditLogs: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${BASE}/audit-logs${qs ? `?${qs}` : ""}`).then((r) => r.json());
  },
};

export default authApi;
