import client from "./client";

const BASE = "/options";

export const optionsApi = {
  priceOption: (body) => client.post(`${BASE}/price`, body).then((r) => r.data),
  getImpliedVol: (body) => client.post(`${BASE}/implied-vol`, body).then((r) => r.data),
  getChain: (body) => client.post(`${BASE}/chain`, body).then((r) => r.data),
  getIVSurface: (body) => client.post(`${BASE}/iv-surface`, body).then((r) => r.data),
  getMaxPain: (body) => client.post(`${BASE}/max-pain`, body).then((r) => r.data),
  getExpectedMove: (body) => client.post(`${BASE}/expected-move`, body).then((r) => r.data),
  getSkew: (body) => client.post(`${BASE}/skew`, body).then((r) => r.data),
  getTickerSummary: (ticker, underlyingPrice = 150, atmIv = 0.25) =>
    client.get(`${BASE}/ticker/${ticker}`, { params: { underlying_price: underlyingPrice, atm_iv: atmIv } }).then((r) => r.data),
};
