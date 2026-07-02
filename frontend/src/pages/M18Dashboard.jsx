import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 22, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 },
  grid3: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 24 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" },
  label: { fontSize: 11, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 },
  val: { fontSize: 20, fontWeight: 700, color: "#f0f6fc" },
  vsub: { fontSize: 11, color: "#8b949e", marginTop: 2 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#58a6ff", marginBottom: 16 },
  badge: (c) => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700 }),
  modGrid: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 },
  mod: (c) => ({ background: "#0d1117", border: `1px solid ${c}33`, borderRadius: 8, padding: "14px 16px", cursor: "pointer", transition: "border-color 0.15s" }),
  modTitle: { fontSize: 12, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  modDesc: { fontSize: 11, color: "#8b949e" },
};

const MODULES = [
  { label: "Streaming Monitor", path: "/m18-streaming", color: "#58a6ff", desc: "Event bus & metrics" },
  { label: "Market Gateway", path: "/m18-gateway", color: "#3fb950", desc: "Multi-venue connector" },
  { label: "Microstructure", path: "/m18-microstructure", color: "#e3b341", desc: "L1/L2/L3 + manipulation" },
  { label: "Feature Engine", path: "/m18-features", color: "#f0883e", desc: "21 technical indicators" },
  { label: "Risk Engine", path: "/m18-risk", color: "#ff7b72", desc: "VaR, ES, leverage, alerts" },
  { label: "Portfolio Intel", path: "/m18-portfolio-intel", color: "#a371f7", desc: "Attribution & frontier" },
  { label: "Alert Center", path: "/m18-alerts", color: "#ffa657", desc: "Configurable alert rules" },
  { label: "Economic Intel", path: "/m18-economic", color: "#79c0ff", desc: "Macro data & cycles" },
  { label: "News Intel", path: "/m18-news", color: "#56d364", desc: "NLP & sentiment" },
  { label: "Earnings Intel", path: "/m18-earnings", color: "#d2a8ff", desc: "Surprise & signals" },
  { label: "AI Agents", path: "/m18-agents", color: "#ff9f43", desc: "10 autonomous agents" },
  { label: "Watchlists", path: "/m18-watchlists", color: "#48dbfb", desc: "Multi-list tracking" },
  { label: "Yield Curve", path: "/m18-yield-curve", color: "#c3e88d", desc: "Tenor spreads" },
  { label: "Stress Tests", path: "/m18-stress-test", color: "#ff6b6b", desc: "Scenario analysis" },
  { label: "Attribution Center", path: "/m18-attribution", color: "#ffcb6b", desc: "Brinson & factor" },
  { label: "Efficient Frontier", path: "/m18-frontier", color: "#82aaff", desc: "Portfolio optimisation" },
  { label: "News Trends", path: "/m18-trends", color: "#89ddff", desc: "Emerging topics" },
  { label: "Earnings Calendar", path: "/m18-earnings-calendar", color: "#f78c6c", desc: "Upcoming releases" },
  { label: "Economic Calendar", path: "/m18-economic-calendar", color: "#b0bec5", desc: "Macro event schedule" },
  { label: "Agent Console", path: "/m18-agent-console", color: "#cf9fff", desc: "Run & monitor agents" },
];

export default function M18Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [riskDash, setRiskDash] = useState(null);
  const [newsStats, setNewsStats] = useState(null);
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    fetch("/m18/streaming/metrics").then(r => r.json()).then(setMetrics).catch(() => {});
    fetch("/m18/risk/dashboard").then(r => r.json()).then(setRiskDash).catch(() => {});
    fetch("/m18/news/stats").then(r => r.json()).then(setNewsStats).catch(() => {});
    fetch("/m18/agents/list").then(r => r.json()).then(setAgents).catch(() => {});
  }, []);

  const kpis = [
    { label: "Events Published", value: metrics?.total_published ?? "—", sub: "Streaming bus" },
    { label: "Portfolio VaR 95%", value: riskDash ? `${(riskDash.var_95 * 100).toFixed(2)}%` : "—", sub: "1-day historical" },
    { label: "Gross Leverage", value: riskDash ? `${riskDash.gross_leverage?.toFixed(2)}x` : "—", sub: "Long + short / NAV" },
    { label: "News Articles", value: newsStats?.total_articles ?? "—", sub: "NLP annotated" },
    { label: "Active Agents", value: agents.filter(a => a.status === "IDLE").length || agents.length || "—", sub: "AI agents ready" },
    { label: "Risk Alerts", value: riskDash?.active_alerts?.length ?? "—", sub: "Active flags" },
    { label: "Sequence #", value: metrics?.sequence ?? "—", sub: "Stream position" },
    { label: "Subscribers", value: metrics?.subscribers ?? "—", sub: "Event listeners" },
  ];

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>M18 — Real-Time Institutional Operating System</div>
      <div style={S.sub}>Institutional-grade real-time OS · 12 modules · 141 REST endpoints · WebSocket ready</div>

      <div style={S.grid4}>
        {kpis.slice(0, 4).map(k => (
          <div key={k.label} style={S.card}>
            <div style={S.label}>{k.label}</div>
            <div style={S.val}>{String(k.value)}</div>
            <div style={S.vsub}>{k.sub}</div>
          </div>
        ))}
      </div>
      <div style={S.grid4}>
        {kpis.slice(4).map(k => (
          <div key={k.label} style={S.card}>
            <div style={S.label}>{k.label}</div>
            <div style={S.val}>{String(k.value)}</div>
            <div style={S.vsub}>{k.sub}</div>
          </div>
        ))}
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>M18 Modules</div>
        <div style={S.modGrid}>
          {MODULES.map(m => (
            <div key={m.path} style={S.mod(m.color)} onClick={() => window.location.hash = m.path}>
              <div style={{ ...S.modTitle, color: m.color }}>{m.label}</div>
              <div style={S.modDesc}>{m.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {riskDash?.active_alerts?.length > 0 && (
        <div style={{ ...S.section, borderColor: "#ff7b7233" }}>
          <div style={{ ...S.sHdr, color: "#ff7b72" }}>Active Risk Alerts</div>
          {riskDash.active_alerts.map(a => (
            <div key={a.alert_id} style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, padding: "8px 12px", background: "#161b22", borderRadius: 6 }}>
              <span style={{ fontSize: 12, color: "#c9d1d9" }}>{a.message}</span>
              <span style={S.badge(a.severity === "HIGH" ? "#ff7b72" : "#e3b341")}>{a.severity}</span>
            </div>
          ))}
        </div>
      )}

      {metrics && (
        <div style={S.section}>
          <div style={S.sHdr}>Streaming Event Distribution</div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {Object.entries(metrics.by_type || {}).map(([type, count]) => (
              <div key={type} style={{ background: "#161b22", borderRadius: 6, padding: "6px 12px" }}>
                <span style={{ fontSize: 11, color: "#8b949e" }}>{type}: </span>
                <span style={{ fontSize: 12, color: "#f0f6fc", fontWeight: 700 }}>{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
