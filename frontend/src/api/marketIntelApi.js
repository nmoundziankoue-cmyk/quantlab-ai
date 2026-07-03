const BASE = `${import.meta.env.VITE_API_URL ?? "http://localhost:8001"}/market-intel`;

export const marketIntelApi = {
  getSectorHeatmap: (period = "1D") => fetch(`${BASE}/sector-heatmap?period=${period}`).then((r) => r.json()),
  getBreadth: () => fetch(`${BASE}/breadth`).then((r) => r.json()),
  getRegime: () => fetch(`${BASE}/regime`).then((r) => r.json()),
  getYieldCurve: () => fetch(`${BASE}/yield-curve`).then((r) => r.json()),
  getMacro: () => fetch(`${BASE}/macro`).then((r) => r.json()),
  getCorrelation: (tickers) => fetch(`${BASE}/correlation`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tickers }) }).then((r) => r.json()),
  getLiquidity: (ticker) => fetch(`${BASE}/liquidity/${ticker}`).then((r) => r.json()),
  getDashboard: () => fetch(`${BASE}/dashboard`).then((r) => r.json()),
};
