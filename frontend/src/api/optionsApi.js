const BASE = "http://localhost:8001/options";

export const optionsApi = {
  priceOption: (body) => fetch(`${BASE}/price`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  getImpliedVol: (body) => fetch(`${BASE}/implied-vol`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  getChain: (body) => fetch(`${BASE}/chain`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  getIVSurface: (body) => fetch(`${BASE}/iv-surface`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  getMaxPain: (body) => fetch(`${BASE}/max-pain`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  getExpectedMove: (body) => fetch(`${BASE}/expected-move`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  getSkew: (body) => fetch(`${BASE}/skew`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  getTickerSummary: (ticker, underlyingPrice = 150, atmIv = 0.25) => fetch(`${BASE}/ticker/${ticker}?underlying_price=${underlyingPrice}&atm_iv=${atmIv}`).then((r) => r.json()),
};
