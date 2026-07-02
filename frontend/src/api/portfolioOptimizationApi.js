import client from "./client";

const BASE = "/portfolio-optimization";

export const portfolioOptimizationApi = {
  getMethods: () => client.get(`${BASE}/methods`),

  optimize: (payload) => client.post(`${BASE}/optimize`, payload),

  compare: (payload) => client.post(`${BASE}/compare`, payload),

  frontier: (payload) => client.post(`${BASE}/frontier`, payload),

  risk: (payload) => client.post(`${BASE}/risk`, payload),

  attribution: (payload) => client.post(`${BASE}/attribution`, payload),

  stress: (payload) => client.post(`${BASE}/stress`, payload),

  monteCarlo: (payload) => client.post(`${BASE}/monte-carlo`, payload),

  covariance: (payload) => client.post(`${BASE}/covariance`, payload),

  fullAnalysis: (payload) => client.post(`${BASE}/full-analysis`, payload),
};
