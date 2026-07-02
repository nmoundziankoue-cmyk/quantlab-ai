import client from "./client";

const BASE = "/alt-intelligence";

export const altIntelligenceApi = {
  // Providers
  listProviders: () => client.get(`${BASE}/providers`),
  providerCapabilities: () => client.get(`${BASE}/providers/capabilities`),
  providerHealth: () => client.get(`${BASE}/providers/health`),

  // Documents
  ingestDocument: (payload) => client.post(`${BASE}/documents/ingest`, payload),
  listDocuments: (params) => client.get(`${BASE}/documents`, { params }),
  parseDocument: (docId, params) => client.get(`${BASE}/documents/${encodeURIComponent(docId)}/parse`, { params }),
  documentStats: () => client.get(`${BASE}/documents/stats`),

  // Document AI
  enrichText: (payload) => client.post(`${BASE}/documents/enrich`, payload),
  askQuestion: (payload) => client.post(`${BASE}/documents/qa`, payload),

  // Events
  detectEvents: (payload) => client.post(`${BASE}/events/detect`, payload),

  // Features
  computeFeatures: (payload) => client.post(`${BASE}/features/compute`, payload),
  featureCatalog: () => client.get(`${BASE}/features/catalog`),

  // Search
  search: (payload) => client.post(`${BASE}/search`, payload),
  searchCompanies: (q) => client.get(`${BASE}/search/companies`, { params: { q } }),
  searchExecutives: (q) => client.get(`${BASE}/search/executives`, { params: { q } }),

  // Knowledge graph
  linkExecutive: (payload) => client.post(`${BASE}/knowledge/executives`, payload),
  linkSupplier: (payload) => client.post(`${BASE}/knowledge/suppliers`, payload),
  graphMetrics: () => client.get(`${BASE}/knowledge/metrics`),
  dependencyChain: (payload) => client.post(`${BASE}/knowledge/dependency-chain`, payload),

  // Data quality
  checkQuality: (payload) => client.post(`${BASE}/quality/check`, payload),
};
