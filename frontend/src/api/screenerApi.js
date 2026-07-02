import client from "./client";

export const getScreenerTypes = () =>
  client.get("/screeners/types").then((r) => r.data);

export const listScreeners = () =>
  client.get("/screeners").then((r) => r.data);

export const getScreener = (id) =>
  client.get(`/screeners/${id}`).then((r) => r.data);

export const createScreener = (payload) =>
  client.post("/screeners", payload).then((r) => r.data);

export const updateScreener = (id, payload) =>
  client.patch(`/screeners/${id}`, payload).then((r) => r.data);

export const deleteScreener = (id) =>
  client.delete(`/screeners/${id}`);

export const runScreener = (payload, save = false) =>
  client.post("/screeners/run", payload, { params: { save } }).then((r) => r.data);

export const getScreenerResults = (id) =>
  client.get(`/screeners/${id}/results`).then((r) => r.data);
