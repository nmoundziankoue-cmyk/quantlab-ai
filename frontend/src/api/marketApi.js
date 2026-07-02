import client from "./client";

// ---------------------------------------------------------------------------
// Quotes
// ---------------------------------------------------------------------------

export const getQuote = (ticker) =>
  client.get(`/market/quote/${ticker}`).then((r) => r.data);

export const getBatchQuotes = (tickers) =>
  client.post("/market/quotes", { tickers }).then((r) => r.data);

// ---------------------------------------------------------------------------
// OHLCV
// ---------------------------------------------------------------------------

export const getOHLCV = (ticker, { interval = "1d", period = "6mo" } = {}) =>
  client
    .get(`/market/ohlcv/${ticker}`, { params: { interval, period } })
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// News & Sentiment
// ---------------------------------------------------------------------------

export const getNews = (ticker, maxArticles = 15) =>
  client
    .get(`/market/news/${ticker}`, { params: { max_articles: maxArticles } })
    .then((r) => r.data);

export const getSentiment = (ticker) =>
  client.get(`/market/sentiment/${ticker}`).then((r) => r.data);

// ---------------------------------------------------------------------------
// Economic calendar
// ---------------------------------------------------------------------------

export const getCalendar = (daysAhead = 30) =>
  client
    .get("/market/calendar", { params: { days_ahead: daysAhead } })
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// Watchlists
// ---------------------------------------------------------------------------

export const listWatchlists = () =>
  client.get("/watchlists").then((r) => r.data);

export const getWatchlist = (id) =>
  client.get(`/watchlists/${id}`).then((r) => r.data);

export const createWatchlist = (payload) =>
  client.post("/watchlists", payload).then((r) => r.data);

export const updateWatchlist = (id, payload) =>
  client.put(`/watchlists/${id}`, payload).then((r) => r.data);

export const deleteWatchlist = (id) => client.delete(`/watchlists/${id}`);

export const addWatchlistItem = (watchlistId, payload) =>
  client
    .post(`/watchlists/${watchlistId}/items`, payload)
    .then((r) => r.data);

export const deleteWatchlistItem = (watchlistId, itemId) =>
  client.delete(`/watchlists/${watchlistId}/items/${itemId}`);
