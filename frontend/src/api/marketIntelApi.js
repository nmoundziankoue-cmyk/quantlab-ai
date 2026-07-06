import client from "./client";

const BASE = "/market-intel";

export const marketIntelApi = {
  getSectorHeatmap: (period = "1D") => client.get(`${BASE}/sector-heatmap`, { params: { period } }).then((r) => r.data),
  getBreadth: () => client.get(`${BASE}/breadth`).then((r) => r.data),
  getRegime: () => client.get(`${BASE}/regime`).then((r) => r.data),
  getYieldCurve: () => client.get(`${BASE}/yield-curve`).then((r) => r.data),
  getMacro: () => client.get(`${BASE}/macro`).then((r) => r.data),
  getCorrelation: (tickers) => client.post(`${BASE}/correlation`, { tickers }).then((r) => r.data),
  getLiquidity: (ticker) => client.get(`${BASE}/liquidity/${ticker}`).then((r) => r.data),
  getDashboard: () => client.get(`${BASE}/dashboard`).then((r) => r.data),
};
