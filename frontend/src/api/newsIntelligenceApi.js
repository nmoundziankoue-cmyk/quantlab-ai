import client from "./client";

export const getNewsFeed = (params) =>
  client.get("/news/feed", { params }).then((r) => r.data);

export const getBreakingNews = (params) =>
  client.get("/news/breaking", { params }).then((r) => r.data);

export const getTickerNews = (ticker, params) =>
  client.get(`/news/ticker/${ticker}`, { params }).then((r) => r.data);

export const getSectorNews = (sector, params) =>
  client.get(`/news/sector/${sector}`, { params }).then((r) => r.data);

export const getDailySummary = () =>
  client.get("/news/summary/daily").then((r) => r.data);

export const getNewsClusters = () =>
  client.get("/news/clusters").then((r) => r.data);

export const getNewsImpact = (params) =>
  client.get("/news/impact", { params }).then((r) => r.data);
