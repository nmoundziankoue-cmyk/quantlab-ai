/**
 * M5 Trading & Execution API client.
 * All functions return Axios response data (already unwrapped by interceptor).
 */
import client from "./client";

// ---------------------------------------------------------------------------
// Orders
// ---------------------------------------------------------------------------

export const createOrder = (data, { portfolioId, paperAccountId, brokerConnectionId } = {}) => {
  const params = {};
  if (portfolioId) params.portfolio_id = portfolioId;
  if (paperAccountId) params.paper_account_id = paperAccountId;
  if (brokerConnectionId) params.broker_connection_id = brokerConnectionId;
  return client.post("/orders", data, { params }).then((r) => r.data);
};

export const listOrders = (params = {}) =>
  client.get("/orders", { params }).then((r) => r.data);

export const getOrder = (orderId) =>
  client.get(`/orders/${orderId}`).then((r) => r.data);

export const modifyOrder = (orderId, data) =>
  client.patch(`/orders/${orderId}`, data).then((r) => r.data);

export const cancelOrder = (orderId, reason) =>
  client.delete(`/orders/${orderId}`, { params: { reason } }).then((r) => r.data);

export const submitOrder = (orderId) =>
  client.post(`/orders/${orderId}/submit`).then((r) => r.data);

export const getOrderAuditLog = (orderId) =>
  client.get(`/orders/${orderId}/audit`).then((r) => r.data);

export const previewOrder = (data) =>
  client.post("/orders/preview", data).then((r) => r.data);

export const createBasketOrder = (data, { portfolioId, paperAccountId } = {}) => {
  const params = {};
  if (portfolioId) params.portfolio_id = portfolioId;
  if (paperAccountId) params.paper_account_id = paperAccountId;
  return client.post("/orders/basket", data, { params }).then((r) => r.data);
};

export const getBasketOrders = (basketId) =>
  client.get(`/orders/basket/${basketId}`).then((r) => r.data);

// ---------------------------------------------------------------------------
// Executions & Blotter
// ---------------------------------------------------------------------------

export const listExecutions = (params = {}) =>
  client.get("/executions", { params }).then((r) => r.data);

export const getExecution = (executionId) =>
  client.get(`/executions/${executionId}`).then((r) => r.data);

export const getOrderExecutions = (orderId) =>
  client.get(`/executions/order/${orderId}`).then((r) => r.data);

export const getExecutionQuality = (orderId) =>
  client.get(`/executions/order/${orderId}/quality`).then((r) => r.data);

export const getBlotter = (params = {}) =>
  client.get("/executions/blotter", { params }).then((r) => r.data);

export const exportBlotterCsv = (params = {}) =>
  client.get("/executions/blotter/csv", { params, responseType: "text" }).then((r) => r.data);

export const getExecutionAnalytics = (params = {}) =>
  client.get("/executions/analytics", { params }).then((r) => r.data);

export const listAlgorithms = () =>
  client.get("/executions/algorithms").then((r) => r.data);

export const scheduleTWAP = (data) =>
  client.post("/executions/algorithms/twap", data).then((r) => r.data);

export const scheduleVWAP = (data) =>
  client.post("/executions/algorithms/vwap", data).then((r) => r.data);

export const schedulePOV = (data) =>
  client.post("/executions/algorithms/pov", data).then((r) => r.data);

export const scheduleIceberg = (data) =>
  client.post("/executions/algorithms/iceberg", data).then((r) => r.data);

// ---------------------------------------------------------------------------
// Paper Trading
// ---------------------------------------------------------------------------

export const createPaperAccount = (data) =>
  client.post("/paper/accounts", data).then((r) => r.data);

export const listPaperAccounts = (params = {}) =>
  client.get("/paper/accounts", { params }).then((r) => r.data);

export const getPaperAccount = (accountId) =>
  client.get(`/paper/accounts/${accountId}`).then((r) => r.data);

export const updatePaperAccount = (accountId, data) =>
  client.patch(`/paper/accounts/${accountId}`, data).then((r) => r.data);

export const refreshPaperPrices = (accountId) =>
  client.post(`/paper/accounts/${accountId}/refresh`).then((r) => r.data);

export const submitPaperOrder = (accountId, data) =>
  client.post(`/paper/accounts/${accountId}/orders`, data).then((r) => r.data);

export const listPaperPositions = (accountId) =>
  client.get(`/paper/accounts/${accountId}/positions`).then((r) => r.data);

export const listPaperTrades = (accountId, params = {}) =>
  client.get(`/paper/accounts/${accountId}/trades`, { params }).then((r) => r.data);

// ---------------------------------------------------------------------------
// Broker Connections
// ---------------------------------------------------------------------------

export const listBrokerTypes = () =>
  client.get("/brokers/types").then((r) => r.data);

export const createBrokerConnection = (data) =>
  client.post("/brokers", data).then((r) => r.data);

export const listBrokerConnections = () =>
  client.get("/brokers").then((r) => r.data);

export const getBrokerConnection = (connectionId) =>
  client.get(`/brokers/${connectionId}`).then((r) => r.data);

export const updateBrokerConnection = (connectionId, data) =>
  client.patch(`/brokers/${connectionId}`, data).then((r) => r.data);

export const deleteBrokerConnection = (connectionId) =>
  client.delete(`/brokers/${connectionId}`).then((r) => r.data);

export const testBrokerConnection = (connectionId) =>
  client.post(`/brokers/${connectionId}/test`).then((r) => r.data);

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export const listAlertTypes = () =>
  client.get("/trading-alerts/types").then((r) => r.data);

export const createAlert = (data) =>
  client.post("/trading-alerts", data).then((r) => r.data);

export const listAlerts = (params = {}) =>
  client.get("/trading-alerts", { params }).then((r) => r.data);

export const getAlert = (alertId) =>
  client.get(`/trading-alerts/${alertId}`).then((r) => r.data);

export const updateAlert = (alertId, data) =>
  client.patch(`/trading-alerts/${alertId}`, data).then((r) => r.data);

export const deleteAlert = (alertId) =>
  client.delete(`/trading-alerts/${alertId}`).then((r) => r.data);
