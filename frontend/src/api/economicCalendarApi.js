const BASE = "http://localhost:8001/economic-calendar";

export const economicCalendarApi = {
  createEvent: (body) => fetch(`${BASE}/events`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  listEvents: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${BASE}/events${qs ? `?${qs}` : ""}`).then((r) => r.json());
  },
  getUpcoming: (days = 7) => fetch(`${BASE}/events/upcoming?days=${days}`).then((r) => r.json()),
  getHighImpact: (limit = 20) => fetch(`${BASE}/events/high-impact?limit=${limit}`).then((r) => r.json()),
  getEvent: (id) => fetch(`${BASE}/events/${id}`).then((r) => r.json()),
  updateEvent: (id, body) => fetch(`${BASE}/events/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  deleteEvent: (id) => fetch(`${BASE}/events/${id}`, { method: "DELETE" }).then((r) => r.json()),
  getByCountry: () => fetch(`${BASE}/by-country`).then((r) => r.json()),
  seed: () => fetch(`${BASE}/seed`, { method: "POST" }).then((r) => r.json()),
  getImpactSummary: () => fetch(`${BASE}/impact-summary`).then((r) => r.json()),
};
