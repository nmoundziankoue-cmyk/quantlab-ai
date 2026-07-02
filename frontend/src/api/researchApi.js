import client from "./client";

export const researchApi = {
  // Indicator overlays
  getIndicators: (body) => client.post("/research/indicators", body).then((r) => r.data),

  // Available built-in strategies
  getAvailableStrategies: () =>
    client.get("/research/strategies/available").then((r) => r.data),

  // Saved strategy CRUD
  listStrategies: () => client.get("/research/strategies").then((r) => r.data),
  createStrategy: (body) => client.post("/research/strategies", body).then((r) => r.data),
  deleteStrategy: (id) => client.delete(`/research/strategies/${id}`),

  // Backtesting
  runBacktest: (body) => client.post("/research/backtest/run", body).then((r) => r.data),
  listBacktests: () => client.get("/research/backtest").then((r) => r.data),
  getBacktest: (id) => client.get(`/research/backtest/${id}`).then((r) => r.data),
  deleteBacktest: (id) => client.delete(`/research/backtest/${id}`),
};
