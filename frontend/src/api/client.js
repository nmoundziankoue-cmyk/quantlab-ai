import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8001",
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ── Token injection ──────────────────────────────────────────────────────────
// The auth store calls setAuthToken() after login and clearAuthToken() after logout.
// This avoids a circular import: the store imports authApi (standalone), not this client.
let _authToken = null;
let _isRefreshing = false;
let _refreshQueue = [];

export function setAuthToken(token) {
  _authToken = token;
}

export function clearAuthToken() {
  _authToken = null;
}

client.interceptors.request.use((config) => {
  if (_authToken) {
    config.headers.Authorization = `Bearer ${_authToken}`;
  }
  return config;
});

// ── 401 handling with single-flight refresh ───────────────────────────────────
client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config;
    const detail = err.response?.data?.detail ?? err.message ?? "Unknown error";
    const msg = Array.isArray(detail) ? detail[0]?.msg : detail;

    if (err.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (_isRefreshing) {
        return new Promise((resolve, reject) => {
          _refreshQueue.push({ resolve, reject });
        }).then((newToken) => {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return client(originalRequest);
        });
      }

      _isRefreshing = true;
      try {
        // Lazy import to avoid circular dependency at module load time.
        const { default: useAuthStore } = await import("../store/useAuthStore");
        const newToken = await useAuthStore.getState().refreshAccessToken();
        _refreshQueue.forEach(({ resolve }) => resolve(newToken));
        _refreshQueue = [];
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return client(originalRequest);
      } catch {
        _refreshQueue.forEach(({ reject }) => reject(new Error("Session expired")));
        _refreshQueue = [];
        const { default: useAuthStore } = await import("../store/useAuthStore");
        useAuthStore.getState().logout();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        return Promise.reject(new Error("Session expired. Please log in again."));
      } finally {
        _isRefreshing = false;
      }
    }

    return Promise.reject(new Error(msg));
  }
);

export default client;
