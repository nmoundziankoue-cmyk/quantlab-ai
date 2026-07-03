/**
 * M9 Phase 2 — Streaming channel constants and WebSocket URL helpers.
 *
 * Channel names match the server-side CHANNEL_REGISTRY keys.
 */

export const CHANNELS = {
  // Trading
  ORDERS: "orders",
  EXECUTIONS: "executions",
  POSITIONS: "positions",
  ALERTS: "alerts",
  EXECUTION_UPDATES: "execution_updates",
  // Market data (parameterized — use channelFor helpers)
  MARKET_DATA: (ticker) => `market_data:${ticker.toUpperCase()}`,
  PRICES: (ticker) => `prices:${ticker.toUpperCase()}`,
  // AI / research
  AGENT_PROGRESS: (sessionId) => `agent_progress:${sessionId}`,
  // System
  TASK_QUEUE: "task_queue",
  SYSTEM_METRICS: "system_metrics",
  PROVIDER_HEALTH: "provider_health",
  NEWS_FEED: "news_feed",
};

const WS_BASE = (() => {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/^https?:/, proto)
    : `${proto}//localhost:8001`;
  return host;
})();

/** Build a ws://... URL for the v2 endpoint. */
export function getWsV2Url({ channels = [], token } = {}) {
  const params = new URLSearchParams();
  if (channels.length > 0) params.set("channels", channels.join(","));
  if (token) params.set("token", token);
  const qs = params.toString();
  return `${WS_BASE}/ws/v2${qs ? `?${qs}` : ""}`;
}

/** Convenience URL for a single-ticker market data stream. */
export function getMarketStreamUrl(ticker, { token } = {}) {
  const params = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${WS_BASE}/ws/v2/market/${ticker.toUpperCase()}${params}`;
}

/** Convenience URL for an agent-progress stream. */
export function getAgentStreamUrl(sessionId, { token } = {}) {
  const params = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${WS_BASE}/ws/v2/agent/${sessionId}${params}`;
}

/** Legacy v1 URL (unchanged). */
export function getWsUrl({ channels = [] } = {}) {
  const qs = channels.length > 0 ? `?channels=${channels.join(",")}` : "";
  return `${WS_BASE}/ws${qs}`;
}

/** Fetch the channel registry from the server. */
export async function fetchChannels() {
  const base = import.meta.env.VITE_API_URL || "http://localhost:8001";
  const res = await fetch(`${base}/ws/v2/channels`);
  return res.json();
}

/** Fetch v2 streaming status. */
export async function fetchStreamingStatus() {
  const base = import.meta.env.VITE_API_URL || "http://localhost:8001";
  const res = await fetch(`${base}/ws/v2/status`);
  return res.json();
}
