import client from "./client";

const BASE = "/market-data";

export const marketDataApi = {
  listProviders: () => client.get(`${BASE}/providers`),
  providerCapabilities: () => client.get(`${BASE}/providers/capabilities`),
  providerHealth: () => client.get(`${BASE}/providers/health`),
  allProviderNames: () => client.get(`${BASE}/providers/all-names`),

  getOHLCV: (payload) => client.post(`${BASE}/ohlcv`, payload),
  validateBars: (payload) => client.post(`${BASE}/validate`, payload),

  featureCatalog: () => client.get(`${BASE}/features/catalog`),
  computeFeatures: (payload) => client.post(`${BASE}/features`, payload),

  buildDataset: (payload) => client.post(`${BASE}/datasets`, payload),

  warehouseStats: () => client.get(`${BASE}/warehouse/stats`),
  listPartitions: (params) => client.get(`${BASE}/warehouse/partitions`, { params }),
  cleanupWarehouse: () => client.delete(`${BASE}/warehouse/cleanup`),

  cacheStats: () => client.get(`${BASE}/cache/stats`),
};
