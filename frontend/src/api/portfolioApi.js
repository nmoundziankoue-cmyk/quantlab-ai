import client from "./client";

// ---------------------------------------------------------------------------
// Portfolios
// ---------------------------------------------------------------------------

export const listPortfolios = () =>
  client.get("/portfolios").then((r) => r.data);

export const getPortfolio = (id) =>
  client.get(`/portfolios/${id}`).then((r) => r.data);

export const createPortfolio = (payload) =>
  client.post("/portfolios", payload).then((r) => r.data);

export const updatePortfolio = (id, payload) =>
  client.put(`/portfolios/${id}`, payload).then((r) => r.data);

export const deletePortfolio = (id) =>
  client.delete(`/portfolios/${id}`);

// ---------------------------------------------------------------------------
// Computed views
// ---------------------------------------------------------------------------

export const getPortfolioSummary = (id) =>
  client.get(`/portfolios/${id}/summary`).then((r) => r.data);

export const getPortfolioPerformance = (id) =>
  client.get(`/portfolios/${id}/performance`).then((r) => r.data);

export const getPortfolioAllocation = (id) =>
  client.get(`/portfolios/${id}/allocation`).then((r) => r.data);

// ---------------------------------------------------------------------------
// Transactions
// ---------------------------------------------------------------------------

export const listTransactions = (id, { limit = 200, offset = 0 } = {}) =>
  client
    .get(`/portfolios/${id}/transactions`, { params: { limit, offset } })
    .then((r) => r.data);

export const addTransaction = (id, payload) =>
  client.post(`/portfolios/${id}/transactions`, payload).then((r) => r.data);

export const deleteTransaction = (portfolioId, transactionId) =>
  client.delete(`/portfolios/${portfolioId}/transactions/${transactionId}`);
