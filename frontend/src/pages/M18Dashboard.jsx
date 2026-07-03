import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const DEMO_METRICS = {
  total_published: 1842,
  sequence: 9173,
  subscribers: 12,
  by_type: { PRICE_UPDATE: 847, ALERT: 63, NEWS: 412, AGENT_OUTPUT: 180, REGIME_CHANGE: 28 },
};
const DEMO_RISK = {
  var_95: 0.031,
  gross_leverage: 1.23,
  active_alerts: [
    { alert_id: "a1", message: "NVDA position VaR exceeds 2% threshold", severity: "HIGH" },
    { alert_id: "a2", message: "Portfolio leverage approaching 1.5× limit", severity: "MEDIUM" },
  ],
};
const DEMO_NEWS   = { total_articles: 3847 };
const DEMO_AGENTS = Array(10).fill({ status: "IDLE" });

const MODULES = [
  { label: "Streaming Monitor",  path: "/m18-streaming",          color: "#567EFF",  desc: "Event bus & metrics" },
  { label: "Market Gateway",     path: "/m18-gateway",            color: "#27C784",  desc: "Multi-venue connector" },
  { label: "Microstructure",     path: "/m18-microstructure",     color: "#E2A52B",  desc: "L1/L2/L3 + manipulation" },
  { label: "Feature Engine",     path: "/m18-features",           color: "#E2A52B",  desc: "21 technical indicators" },
  { label: "Risk Engine",        path: "/m18-risk",               color: "#E5473E",  desc: "VaR, ES, leverage, alerts" },
  { label: "Portfolio Intel",    path: "/m18-portfolio-intel",    color: "#9D7FEA",  desc: "Attribution & frontier" },
  { label: "Alert Center",       path: "/m18-alerts",             color: "#E5473E",  desc: "Configurable alert rules" },
  { label: "Economic Intel",     path: "/m18-economic",           color: "#567EFF",  desc: "Macro data & cycles" },
  { label: "News Intel",         path: "/m18-news",               color: "#27C784",  desc: "NLP & sentiment" },
  { label: "Earnings Intel",     path: "/m18-earnings",           color: "#9D7FEA",  desc: "Surprise & signals" },
  { label: "AI Agents",          path: "/m18-agents",             color: "#E2A52B",  desc: "10 autonomous agents" },
  { label: "Watchlists",         path: "/m18-watchlists",         color: "#567EFF",  desc: "Multi-list tracking" },
  { label: "Yield Curve",        path: "/m18-yield-curve",        color: "#27C784",  desc: "Tenor spreads" },
  { label: "Stress Tests",       path: "/m18-stress-test",        color: "#E5473E",  desc: "Scenario analysis" },
  { label: "Attribution Center", path: "/m18-attribution",        color: "#9D7FEA",  desc: "Brinson & factor" },
  { label: "Eff. Frontier",      path: "/m18-frontier",           color: "#567EFF",  desc: "Portfolio optimisation" },
  { label: "News Trends",        path: "/m18-trends",             color: "#7A84A0",  desc: "Emerging topics" },
  { label: "Earnings Calendar",  path: "/m18-earnings-calendar",  color: "#7A84A0",  desc: "Upcoming releases" },
  { label: "Economic Calendar",  path: "/m18-economic-calendar",  color: "#7A84A0",  desc: "Macro event schedule" },
  { label: "Agent Console",      path: "/m18-agent-console",      color: "#9D7FEA",  desc: "Run & monitor agents" },
];

function SeverityBadge({ severity }) {
  const color = severity === "HIGH" ? "#E5473E" : "#E2A52B";
  return (
    <span style={{
      fontFamily: "var(--font-mono)",
      fontSize: 9,
      fontWeight: 700,
      padding: "2px 6px",
      borderRadius: 3,
      background: color + "18",
      border: `1px solid ${color}44`,
      color,
      letterSpacing: "0.06em",
    }}>
      {severity}
    </span>
  );
}

export default function M18Dashboard() {
  const navigate = useNavigate();
  const [metrics,   setMetrics]   = useState(null);
  const [riskDash,  setRiskDash]  = useState(null);
  const [newsStats, setNewsStats] = useState(null);
  const [agents,    setAgents]    = useState([]);

  useEffect(() => {
    fetch("/m18/streaming/metrics").then(r => r.json()).then(setMetrics).catch(() => setMetrics(DEMO_METRICS));
    fetch("/m18/risk/dashboard").then(r => r.json()).then(setRiskDash).catch(() => setRiskDash(DEMO_RISK));
    fetch("/m18/news/stats").then(r => r.json()).then(setNewsStats).catch(() => setNewsStats(DEMO_NEWS));
    fetch("/m18/agents/list").then(r => r.json()).then(setAgents).catch(() => setAgents(DEMO_AGENTS));
  }, []);

  const kpis = [
    { label: "Events Published", value: metrics?.total_published,                           color: "#E2A52B", sub: "Streaming bus" },
    { label: "VaR 95% (1-day)",  value: riskDash ? `${(riskDash.var_95 * 100).toFixed(2)}%` : null, color: "#E5473E", sub: "Historical simulation" },
    { label: "Gross Leverage",   value: riskDash ? `${riskDash.gross_leverage?.toFixed(2)}×` : null,  color: "#E2A52B", sub: "Long + short / NAV" },
    { label: "News Articles",    value: newsStats?.total_articles,                           color: "#E2A52B", sub: "NLP annotated" },
    { label: "Active Agents",    value: agents.length || null,                               color: "#27C784", sub: "AI agents ready" },
    { label: "Risk Alerts",      value: riskDash?.active_alerts?.length,                    color: riskDash?.active_alerts?.length > 0 ? "#E5473E" : "#27C784", sub: "Active flags" },
    { label: "Stream Sequence",  value: metrics?.sequence,                                   color: "#E2A52B", sub: "Event position" },
    { label: "Subscribers",      value: metrics?.subscribers,                                color: "#E2A52B", sub: "Event listeners" },
  ];

  return (
    <div style={S.root}>
      {/* Header */}
      <h1 style={S.h1}>M18 — Real-Time Institutional OS</h1>
      <p style={S.h1Sub}>12 modules · 141 REST endpoints · WebSocket streaming · pure Python</p>

      {/* KPI grid */}
      <div style={S.kpiGrid}>
        {kpis.map((k) => (
          <div key={k.label} style={S.kpiCard}>
            <div className="ql-label" style={{ marginBottom: 6 }}>{k.label}</div>
            <div className="ql-value" style={{ fontSize: 22, fontWeight: 600, color: k.color, lineHeight: 1 }}>
              {k.value ?? "—"}
            </div>
            <div style={S.kpiSub}>{k.sub}</div>
          </div>
        ))}
      </div>

      {/* Active risk alerts */}
      {riskDash?.active_alerts?.length > 0 && (
        <div style={{ ...S.panel, borderColor: "#E5473E33" }}>
          <div style={{ ...S.panelTitle, color: "#E5473E" }}>Active Risk Alerts</div>
          {riskDash.active_alerts.map((a) => (
            <div key={a.alert_id} style={S.alertRow}>
              <span style={{ fontFamily: "var(--font-body)", fontSize: 12, color: "#DDE2EE" }}>{a.message}</span>
              <SeverityBadge severity={a.severity} />
            </div>
          ))}
        </div>
      )}

      {/* Streaming event distribution */}
      {metrics?.by_type && (
        <div style={S.panel}>
          <div style={S.panelTitle}>Streaming Event Distribution</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {Object.entries(metrics.by_type).map(([type, count]) => (
              <div key={type} style={S.eventChip}>
                <span className="ql-label" style={{ color: "#454D66" }}>{type}</span>
                <span className="ql-value" style={{ fontSize: 14, fontWeight: 700, color: "#E2A52B" }}>{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Module grid */}
      <div style={S.panel}>
        <div style={S.panelTitle}>M18 Module Map — 20 modules</div>
        <div style={S.modGrid}>
          {MODULES.map((m) => (
            <button
              key={m.path}
              style={{ ...S.modCard, borderColor: m.color + "28" }}
              onMouseEnter={(e) => e.currentTarget.style.borderColor = m.color + "88"}
              onMouseLeave={(e) => e.currentTarget.style.borderColor = m.color + "28"}
              onClick={() => navigate(m.path)}
            >
              <div style={{ fontFamily: "var(--font-display)", fontSize: 11, fontWeight: 700, color: m.color, marginBottom: 2 }}>
                {m.label}
              </div>
              <div className="ql-value" style={{ fontSize: 9, color: "#454D66" }}>{m.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

const S = {
  root:     { padding: "28px 32px", maxWidth: 1200 },
  h1:       { fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700, color: "#DDE2EE", margin: "0 0 6px" },
  h1Sub:    { fontFamily: "var(--font-mono)", fontSize: 10, color: "#454D66", margin: "0 0 24px", letterSpacing: "0.03em" },
  kpiGrid:  { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 14 },
  kpiCard:  { background: "#131720", border: "1px solid #232A3D", borderRadius: 7, padding: "14px 16px" },
  kpiSub:   { fontFamily: "var(--font-mono)", fontSize: 9, color: "#454D66", marginTop: 4 },
  panel: {
    background: "#131720",
    border: "1px solid #232A3D",
    borderRadius: 7,
    padding: "16px 18px",
    marginBottom: 12,
  },
  panelTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 10,
    fontWeight: 700,
    color: "#567EFF",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    marginBottom: 14,
  },
  alertRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 12px",
    background: "#1A1F2E",
    borderRadius: 5,
    marginBottom: 6,
    gap: 12,
  },
  eventChip: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
    background: "#1A1F2E",
    border: "1px solid #232A3D",
    borderRadius: 5,
    padding: "8px 12px",
    minWidth: 80,
  },
  modGrid: { display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 },
  modCard: {
    background: "#0B0D13",
    border: "1px solid",
    borderRadius: 6,
    padding: "10px 12px",
    textAlign: "left",
    cursor: "pointer",
    transition: "border-color 0.15s",
    width: "100%",
  },
};
