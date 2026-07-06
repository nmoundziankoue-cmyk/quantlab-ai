import client from "./client";

const BASE = "/economic-calendar";

export const economicCalendarApi = {
  createEvent: (body) => client.post(`${BASE}/events`, body).then((r) => r.data),
  listEvents: (params = {}) => client.get(`${BASE}/events`, { params }).then((r) => r.data),
  getUpcoming: (days = 7) => client.get(`${BASE}/events/upcoming`, { params: { days } }).then((r) => r.data),
  getHighImpact: (limit = 20) => client.get(`${BASE}/events/high-impact`, { params: { limit } }).then((r) => r.data),
  getEvent: (id) => client.get(`${BASE}/events/${id}`).then((r) => r.data),
  updateEvent: (id, body) => client.put(`${BASE}/events/${id}`, body).then((r) => r.data),
  deleteEvent: (id) => client.delete(`${BASE}/events/${id}`).then((r) => r.data),
  getByCountry: () => client.get(`${BASE}/by-country`).then((r) => r.data),
  seed: () => client.post(`${BASE}/seed`).then((r) => r.data),
  getImpactSummary: () => client.get(`${BASE}/impact-summary`).then((r) => r.data),
};
