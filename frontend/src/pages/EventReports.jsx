import { useState } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 12, fontFamily: "monospace" };
const BTN = (a) => ({ padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, background: a ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace" });

const REPORT_TYPES = ["daily","weekly","monthly","company","sector","macro","portfolio","catalyst"];
const LABEL = { fontSize: 11, color: "#8b949e", marginBottom: 4 };

function SectionBlock({ section }) {
  return (
    <div style={{ marginBottom: 20, borderLeft: "2px solid #21262d", paddingLeft: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 8 }}>{section.title}</div>
      <div style={{ fontSize: 12, color: "#c9d1d9", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>{section.content}</div>
      {section.data && Object.keys(section.data).length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary style={{ fontSize: 11, color: "#8b949e", cursor: "pointer" }}>Raw data</summary>
          <pre style={{ fontSize: 10, color: "#8b949e", marginTop: 6, overflow: "auto", maxHeight: 200 }}>
            {JSON.stringify(section.data, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}

export default function EventReports() {
  const [reportType, setReportType] = useState("daily");
  const [ticker, setTicker] = useState("");
  const [sector, setSector] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const payload = { report_type: reportType };
      if (ticker) payload.ticker = ticker.toUpperCase();
      if (sector) payload.sector = sector;
      const r = await eventsApi.generateReport(payload);
      setReport(r.data);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const needsTicker = reportType === "company";
  const needsSector = reportType === "sector";

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15</div>
      <h1 style={{ margin: "0 0 4px", fontSize: 22 }}>Research Reports</h1>
      <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 20 }}>Institutional research reports — Daily, Company, Sector, Macro, Catalyst</div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20, alignItems: "flex-end" }}>
        <div>
          <div style={LABEL}>Report Type</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {REPORT_TYPES.map((t) => (
              <button key={t} style={{ ...BTN(reportType === t), padding: "5px 12px" }} onClick={() => setReportType(t)}>{t}</button>
            ))}
          </div>
        </div>
        {needsTicker && (
          <div>
            <div style={LABEL}>Ticker</div>
            <input style={{ ...INPUT, width: 100 }} placeholder="AAPL" value={ticker}
              onChange={(e) => setTicker(e.target.value)} />
          </div>
        )}
        {needsSector && (
          <div>
            <div style={LABEL}>Sector</div>
            <input style={{ ...INPUT, width: 140 }} placeholder="technology" value={sector}
              onChange={(e) => setSector(e.target.value)} />
          </div>
        )}
        <button style={BTN(true)} disabled={loading} onClick={generate}>
          {loading ? "Generating…" : "Generate Report"}
        </button>
      </div>

      {error && <div style={{ color: "#f85149", fontSize: 12, marginBottom: 16 }}>{error}</div>}

      {report && (
        <div style={CARD}>
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 }}>{report.title}</div>
            <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 4 }}>{report.subtitle}</div>
            <div style={{ display: "flex", gap: 16, fontSize: 11, color: "#8b949e" }}>
              <span>Generated: {new Date(report.generated_at * 1000).toLocaleString()}</span>
              <span>Type: <span style={{ color: "#58a6ff" }}>{report.report_type}</span></span>
              <span>ID: <code style={{ color: "#3fb950", fontSize: 10 }}>{report.report_id}</code></span>
            </div>
          </div>

          <div style={{ ...CARD, marginBottom: 16, background: "#161b22", borderColor: "#30363d" }}>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 6 }}>EXECUTIVE SUMMARY</div>
            <div style={{ fontSize: 13, color: "#f0f6fc", lineHeight: 1.7 }}>{report.summary}</div>
          </div>

          {(report.sections || []).map((s, i) => <SectionBlock key={i} section={s} />)}

          {Object.keys(report.metadata || {}).length > 0 && (
            <details style={{ marginTop: 16 }}>
              <summary style={{ fontSize: 11, color: "#8b949e", cursor: "pointer" }}>Report Metadata</summary>
              <pre style={{ fontSize: 10, color: "#8b949e", marginTop: 6 }}>
                {JSON.stringify(report.metadata, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}

      {!report && !loading && (
        <div style={{ ...CARD, color: "#8b949e" }}>
          Select a report type and click Generate. Add corporate or macro events first for richer reports.
        </div>
      )}
    </div>
  );
}
