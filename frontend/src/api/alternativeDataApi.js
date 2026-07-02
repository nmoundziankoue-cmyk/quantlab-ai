import client from "./client";

export const ingestEvent = (payload) =>
  client.post("/alternative-data/ingest", payload).then((r) => r.data);

export const batchIngest = (payload) =>
  client.post("/alternative-data/ingest/batch", payload).then((r) => r.data);

export const listEvents = (params) =>
  client.get("/alternative-data/events", { params }).then((r) => r.data);

export const searchEvents = (payload) =>
  client.post("/alternative-data/events/search", payload).then((r) => r.data);

export const getEvent = (id) =>
  client.get(`/alternative-data/events/${id}`).then((r) => r.data);

export const getTickerTimeline = (ticker, params) =>
  client.get(`/alternative-data/ticker/${ticker}/timeline`, { params }).then((r) => r.data);

export const getTickerSentiment = (ticker) =>
  client.get(`/alternative-data/ticker/${ticker}/sentiment`).then((r) => r.data);

export const getImportanceFeed = (params) =>
  client.get("/alternative-data/feed/importance", { params }).then((r) => r.data);

export const listClusters = () =>
  client.get("/alternative-data/clusters").then((r) => r.data);

export const buildClusters = () =>
  client.post("/alternative-data/clusters/build").then((r) => r.data);
