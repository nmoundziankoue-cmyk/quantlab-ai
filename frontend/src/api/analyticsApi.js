/**
 * Analytics API — M4 Portfolio & Risk Analytics
 * All calls go through the shared axios client.
 */
import api from "./client";

const base = (portfolioId) => `/analytics/${portfolioId}`;

// Risk metrics
export const fetchRiskMetrics = (portfolioId, params = {}) =>
  api.post(`${base(portfolioId)}/risk`, params).then((r) => r.data);

// Optimization
export const fetchOptimization = (portfolioId, params = {}) =>
  api.post(`${base(portfolioId)}/optimize`, params).then((r) => r.data);

export const fetchOptimizationMethods = (portfolioId) =>
  api.get(`${base(portfolioId)}/optimize/methods`).then((r) => r.data);

export const fetchEfficientFrontier = (portfolioId, params = {}, nPoints = 40) =>
  api
    .post(`${base(portfolioId)}/efficient-frontier?n_points=${nPoints}`, params)
    .then((r) => r.data);

// Stress testing
export const fetchStressScenarios = (portfolioId) =>
  api.get(`${base(portfolioId)}/stress/scenarios`).then((r) => r.data);

export const fetchAllStressTests = (portfolioId) =>
  api.get(`${base(portfolioId)}/stress/all`).then((r) => r.data);

export const fetchStressScenario = (portfolioId, scenarioKey) =>
  api.get(`${base(portfolioId)}/stress/${scenarioKey}`).then((r) => r.data);

export const runCustomStress = (portfolioId, body) =>
  api.post(`${base(portfolioId)}/stress/custom`, body).then((r) => r.data);

// Monte Carlo
export const runMonteCarlo = (portfolioId, params = {}) =>
  api.post(`${base(portfolioId)}/monte-carlo`, params).then((r) => r.data);

// Factor analytics
export const fetchFactorExposures = (portfolioId, lookbackDays = 252) =>
  api
    .get(`${base(portfolioId)}/factors?lookback_days=${lookbackDays}`)
    .then((r) => r.data);

// Correlation
export const fetchCorrelationMatrix = (portfolioId, lookbackDays = 252, method = "pearson") =>
  api
    .get(`${base(portfolioId)}/correlation?lookback_days=${lookbackDays}&method=${method}`)
    .then((r) => r.data);

export const fetchRollingCorrelation = (portfolioId, body) =>
  api.post(`${base(portfolioId)}/correlation/rolling`, body).then((r) => r.data);

export const fetchMST = (portfolioId, lookbackDays = 252) =>
  api.get(`${base(portfolioId)}/correlation/mst?lookback_days=${lookbackDays}`).then((r) => r.data);

export const fetchClusters = (portfolioId, lookbackDays = 252, nClusters = 3) =>
  api
    .get(`${base(portfolioId)}/correlation/clusters?lookback_days=${lookbackDays}&n_clusters=${nClusters}`)
    .then((r) => r.data);
