import client from "./client";
const BASE = "/events";

export const eventsApi = {
  // Corporate events
  listCorporate: (params) => client.get(`${BASE}/company`, { params }),
  addCorporate: (payload) => client.post(`${BASE}/company`, payload),
  getCorporate: (id) => client.get(`${BASE}/company/${encodeURIComponent(id)}`),

  // Macro events
  listMacro: (params) => client.get(`${BASE}/macro`, { params }),
  addMacro: (payload) => client.post(`${BASE}/macro`, payload),
  getMacro: (id) => client.get(`${BASE}/macro/${encodeURIComponent(id)}`),

  // Statistics
  statistics: () => client.get(`${BASE}/statistics`),

  // Timeline
  timeline: (payload) => client.post(`${BASE}/timeline`, payload),

  // Upcoming
  upcoming: (params) => client.get(`${BASE}/upcoming`, { params }),

  // Calendar
  calendar: (payload) => client.post(`${BASE}/calendar`, payload),
  heatmap: (params) => client.get(`${BASE}/heatmap`, { params }),

  // Event study
  runStudy: (payload) => client.post(`${BASE}/study`, payload),

  // Event impact
  computeImpact: (payload) => client.post(`${BASE}/impact`, payload),

  // Catalysts
  listCatalysts: (params) => client.get(`${BASE}/catalysts`, { params }),
  scoreCatalyst: (payload) => client.post(`${BASE}/catalysts/score`, payload),

  // Intelligence
  getIntelligence: (payload) => client.post(`${BASE}/intelligence`, payload),
  getMacroIntelligence: (payload) => client.post(`${BASE}/intelligence/macro`, payload),
  intelligenceScore: (id) => client.get(`${BASE}/intelligence/score/${encodeURIComponent(id)}`),

  // Clustering
  clusters: (params) => client.get(`${BASE}/clusters`, { params }),

  // Search
  search: (payload) => client.post(`${BASE}/search`, payload),
  searchFacets: () => client.get(`${BASE}/search/facets`),
  autocomplete: (q) => client.get(`${BASE}/search/autocomplete`, { params: { q } }),

  // Reports
  generateReport: (payload) => client.post(`${BASE}/report`, payload),

  // Export
  exportEvents: (params) => client.get(`${BASE}/export`, { params }),
};
