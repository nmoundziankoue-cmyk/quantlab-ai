import { useState } from "react";
import { useEconomicEvents, useHighImpactEvents, useImpactSummary, useSeedEvents } from "../hooks/useEconomicCalendar";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 340px", gap: 16 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sectionTitle: { fontSize: 12, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { padding: "8px 12px", textAlign: "left", fontSize: 11, color: "#8b949e", fontWeight: 600, borderBottom: "1px solid #30363d" },
  td: { padding: "10px 12px", fontSize: 13, borderBottom: "1px solid #21262d" },
  btn: (c = "#238636") => ({ background: c, border: "none", borderRadius: 6, padding: "7px 14px", color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600, marginRight: 6 }),
  metricRow: { display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid #21262d" },
  metricLabel: { fontSize: 12, color: "#8b949e" },
  metricVal: { fontSize: 13, fontWeight: 600 },
  select: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "7px 10px", color: "#e6edf3", fontSize: 12, outline: "none", marginRight: 8 },
};

const IMPORTANCE_COLORS = { HIGH: "#f85149", MEDIUM: "#f0883e", LOW: "#8b949e" };
const IMPACT_BAR = (score) => {
  const w = Math.min((score || 0) * 100, 100);
  const c = w > 70 ? "#f85149" : w > 40 ? "#f0883e" : "#3fb950";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ width: 60, height: 6, background: "#21262d", borderRadius: 3 }}>
        <div style={{ width: `${w}%`, height: "100%", background: c, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 11, color: "#8b949e" }}>{(score || 0).toFixed(2)}</span>
    </div>
  );
};

function SurpriseBadge({ actual, forecast }) {
  if (actual == null || forecast == null) return null;
  const surprise = actual - forecast;
  const color = surprise > 0 ? "#3fb950" : surprise < 0 ? "#f85149" : "#8b949e";
  return <span style={{ fontSize: 11, color, fontWeight: 600 }}>{surprise > 0 ? "▲" : surprise < 0 ? "▼" : "—"} {Math.abs(surprise).toFixed(2)}</span>;
}

export default function EconomicCalendar() {
  const [importance, setImportance] = useState("");
  const [country, setCountry] = useState("");
  const [tab, setTab] = useState("all");

  const { data: allEvents = [] } = useEconomicEvents({ importance: importance || undefined, country: country || undefined, limit: 100 });
  const { data: highImpact = [] } = useHighImpactEvents();
  const { data: summary } = useImpactSummary();
  const seedEvents = useSeedEvents();

  const displayEvents = tab === "high" ? highImpact : allEvents;
  const tabs = [{ k: "all", l: "All Events" }, { k: "high", l: "High Impact" }];

  return (
    <div style={S.page}>
      <div style={S.title}>Economic Calendar</div>
      <div style={S.grid2}>
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ display: "flex", gap: 4, borderBottom: "1px solid #30363d" }}>
              {tabs.map(({ k, l }) => (
                <div key={k} style={{ padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600, borderBottom: `2px solid ${tab === k ? "#58a6ff" : "transparent"}`, color: tab === k ? "#58a6ff" : "#8b949e", marginBottom: -1 }} onClick={() => setTab(k)}>{l}</div>
              ))}
            </div>
            <div style={{ display: "flex", alignItems: "center" }}>
              <select style={S.select} value={importance} onChange={(e) => setImportance(e.target.value)}>
                <option value="">All Importance</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
              <select style={S.select} value={country} onChange={(e) => setCountry(e.target.value)}>
                <option value="">All Countries</option>
                {["US", "EU", "UK", "CN", "JP"].map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <button style={S.btn("#1f6feb")} onClick={() => seedEvents.mutate()} disabled={seedEvents.isPending}>
                {seedEvents.isPending ? "Seeding..." : "Seed Data"}
              </button>
            </div>
          </div>

          <div style={S.card}>
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={S.th}>Event</th>
                  <th style={S.th}>Country</th>
                  <th style={S.th}>Importance</th>
                  <th style={S.th}>Category</th>
                  <th style={S.th}>Actual</th>
                  <th style={S.th}>Forecast</th>
                  <th style={S.th}>Surprise</th>
                  <th style={S.th}>Impact</th>
                </tr>
              </thead>
              <tbody>
                {displayEvents.length === 0 ? (
                  <tr><td colSpan={8} style={{ ...S.td, textAlign: "center", color: "#8b949e", padding: 30 }}>
                    No events found. Click "Seed Data" to load sample events.
                  </td></tr>
                ) : displayEvents.map((ev) => (
                  <tr key={ev.id}>
                    <td style={{ ...S.td, fontWeight: 600, maxWidth: 220 }}>{ev.name}</td>
                    <td style={S.td}>
                      <span style={{ background: "#21262d", borderRadius: 4, padding: "2px 6px", fontSize: 11 }}>{ev.country}</span>
                    </td>
                    <td style={S.td}>
                      <span style={{ color: IMPORTANCE_COLORS[ev.importance], fontWeight: 600, fontSize: 12 }}>
                        {ev.importance === "HIGH" ? "●" : ev.importance === "MEDIUM" ? "◉" : "○"} {ev.importance}
                      </span>
                    </td>
                    <td style={{ ...S.td, color: "#8b949e" }}>{ev.category}</td>
                    <td style={{ ...S.td, fontWeight: ev.actual != null ? 700 : 400, color: ev.actual != null ? "#e6edf3" : "#8b949e" }}>
                      {ev.actual != null ? `${ev.actual}${ev.unit ? ` ${ev.unit}` : ""}` : "—"}
                    </td>
                    <td style={{ ...S.td, color: "#8b949e" }}>
                      {ev.forecast != null ? `${ev.forecast}${ev.unit ? ` ${ev.unit}` : ""}` : "—"}
                    </td>
                    <td style={S.td}><SurpriseBadge actual={ev.actual} forecast={ev.forecast} /></td>
                    <td style={S.td}>{IMPACT_BAR(ev.impact_score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          {summary && (
            <div style={S.card}>
              <div style={S.sectionTitle}>Impact Summary</div>
              {[
                ["Total Events", summary.total_events],
                ["High Impact", summary.by_importance?.HIGH || 0],
                ["Medium Impact", summary.by_importance?.MEDIUM || 0],
                ["Low Impact", summary.by_importance?.LOW || 0],
                ["Avg Impact Score", summary.avg_impact_score?.toFixed(3)],
              ].map(([k, v]) => (
                <div key={k} style={S.metricRow}>
                  <span style={S.metricLabel}>{k}</span>
                  <span style={S.metricVal}>{v}</span>
                </div>
              ))}
            </div>
          )}

          {summary?.by_country && Object.keys(summary.by_country).length > 0 && (
            <div style={S.card}>
              <div style={S.sectionTitle}>Events by Country</div>
              {Object.entries(summary.by_country).sort((a, b) => b[1] - a[1]).map(([c, n]) => (
                <div key={c} style={S.metricRow}>
                  <span style={S.metricLabel}>{c}</span>
                  <span style={S.metricVal}>{n}</span>
                </div>
              ))}
            </div>
          )}

          <div style={{ ...S.card, background: "#0d1117", border: "1px solid #1f6feb33" }}>
            <div style={{ fontSize: 12, color: "#58a6ff", fontWeight: 600, marginBottom: 8 }}>Impact Score Guide</div>
            {[["0.8 – 1.0", "#f85149", "Extreme Market Impact"], ["0.5 – 0.8", "#f0883e", "High Market Impact"], ["0.2 – 0.5", "#3fb950", "Moderate Impact"], ["0.0 – 0.2", "#8b949e", "Low Impact"]].map(([range, color, label]) => (
              <div key={range} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                <div style={{ width: 12, height: 12, background: color, borderRadius: 2 }} />
                <span style={{ fontSize: 11, color: "#8b949e" }}>{range} — {label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
