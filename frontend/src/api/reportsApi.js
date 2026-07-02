import client from "./client";

export const generateReport = (params) =>
  client.post("/reports/generate", null, { params }).then((r) => r.data);

export const listReportSections = () =>
  client.get("/reports/sections").then((r) => r.data);

export const generateSection = (payload) =>
  client.post("/reports/section", payload).then((r) => r.data);

export const exportReportHtml = (payload) =>
  client.post("/reports/export/html", payload).then((r) => r.data);
