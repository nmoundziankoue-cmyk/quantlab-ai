import client from "./client";

const api = client;

export const multiAssetApi = {
  // Asset Registry
  registerAsset: (data) => api.post("/multi-asset/assets/register", data),
  getAsset: (ticker) => api.get(`/multi-asset/assets/${ticker}`),
  listAssets: () => api.get("/multi-asset/assets"),
  filterAssets: (data) => api.post("/multi-asset/assets/filter", data),
  searchAssets: (query) => api.get(`/multi-asset/assets/search/${query}`),
  assetStatistics: () => api.get("/multi-asset/assets/statistics"),

  // Cross-Asset
  correlationMatrix: (data) => api.post("/multi-asset/cross-asset/correlation-matrix", data),
  rollingCorrelation: (data) => api.post("/multi-asset/cross-asset/rolling-correlation", data),
  dynamicBeta: (data) => api.post("/multi-asset/cross-asset/dynamic-beta", data),
  relativeStrength: (data) => api.post("/multi-asset/cross-asset/relative-strength", data),
  leadLag: (data) => api.post("/multi-asset/cross-asset/lead-lag", data),
  spillover: (data) => api.post("/multi-asset/cross-asset/spillover", data),
  riskTransmission: (data) => api.post("/multi-asset/cross-asset/risk-transmission", data),
  synchronization: (data) => api.post("/multi-asset/cross-asset/synchronization", data),
  dependencyGraph: (data) => api.post("/multi-asset/cross-asset/dependency-graph", data),

  // Factors
  factorExposures: (data) => api.post("/multi-asset/factors/exposures", data),
  factorReturns: (data) => api.post("/multi-asset/factors/returns", data),
  factorAttribution: (data) => api.post("/multi-asset/factors/attribution", data),
  factorCorrelation: (data) => api.post("/multi-asset/factors/correlation", data),
  portfolioFactorExposure: (data) => api.post("/multi-asset/factors/portfolio-exposure", data),

  // ETF
  etfSectorExposure: (etf) => api.post("/multi-asset/etf/sector-exposure", etf),
  etfCountryExposure: (etf) => api.post("/multi-asset/etf/country-exposure", etf),
  etfOverlap: (data) => api.post("/multi-asset/etf/overlap", data),
  etfMultiOverlap: (data) => api.post("/multi-asset/etf/multi-overlap", data),
  etfTrackingDifference: (data) => api.post("/multi-asset/etf/tracking-difference", data),
  etfFlowEstimate: (data) => api.post("/multi-asset/etf/flow-estimate", data),
  etfSummary: (etf) => api.post("/multi-asset/etf/summary", etf),

  // Bonds
  bondAnalyze: (data) => api.post("/multi-asset/bonds/analyze", data),
  bondYtm: (data) => api.post("/multi-asset/bonds/ytm", data),
  bondDuration: (data) => api.post("/multi-asset/bonds/duration", data),
  portfolioBondDuration: (data) => api.post("/multi-asset/bonds/portfolio-duration", data),
  bondYieldBuckets: (data) => api.post("/multi-asset/bonds/yield-buckets", data),
  bondCreditBuckets: (data) => api.post("/multi-asset/bonds/credit-buckets", data),

  // Options
  optionPrice: (data) => api.post("/multi-asset/options/price", data),
  optionGreeks: (data) => api.post("/multi-asset/options/greeks", data),
  impliedVol: (data) => api.post("/multi-asset/options/implied-vol", data),
  optionAnalyze: (data) => api.post("/multi-asset/options/analyze", data),
  maxPain: (data) => api.post("/multi-asset/options/max-pain", data),
  gammaExposure: (data) => api.post("/multi-asset/options/gamma-exposure", data),
  ivRank: (data) => api.post("/multi-asset/options/iv-rank", data),

  // Futures
  termStructure: (data) => api.post("/multi-asset/futures/term-structure", data),
  rollYield: (data) => api.post("/multi-asset/futures/roll-yield", data),
  futuresBasis: (data) => api.post("/multi-asset/futures/basis", data),
  fairValue: (data) => api.post("/multi-asset/futures/fair-value", data),
  carryRanking: (data) => api.post("/multi-asset/futures/carry-ranking", data),

  // Crypto
  cryptoDominance: (assets) => api.post("/multi-asset/crypto/dominance", assets),
  stablecoinRatio: (assets) => api.post("/multi-asset/crypto/stablecoin-ratio", assets),
  cryptoBreadth: (data) => api.post("/multi-asset/crypto/breadth", data),
  cryptoCycle: (data) => api.post("/multi-asset/crypto/cycle-indicator", data),
  onChainProxy: (data) => api.post("/multi-asset/crypto/on-chain-proxy", data),
  cryptoSectorPerformance: (data) => api.post("/multi-asset/crypto/sector-performance", data),

  // Portfolio Exposure
  portfolioExposure: (data) => api.post("/multi-asset/portfolio/exposure", data),
  portfolioSector: (data) => api.post("/multi-asset/portfolio/sector-exposure", data),
  portfolioCountry: (data) => api.post("/multi-asset/portfolio/country-exposure", data),
  portfolioConcentration: (data) => api.post("/multi-asset/portfolio/concentration", data),
  portfolioRisk: (data) => api.post("/multi-asset/portfolio/risk-exposure", data),
  portfolioDrift: (data) => api.post("/multi-asset/portfolio/drift", data),
  activeWeights: (data) => api.post("/multi-asset/portfolio/active-weights", data),
};
