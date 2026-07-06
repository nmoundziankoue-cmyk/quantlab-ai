import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 22, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  grid: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" },
  label: { fontSize: 11, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 },
  val: { fontSize: 20, fontWeight: 700, color: "#f0f6fc" },
  sub: { fontSize: 11, color: "#8b949e", marginTop: 2 },
  row: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#58a6ff", marginBottom: 16 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { fontSize: 11, color: "#8b949e", textAlign: "left", borderBottom: "1px solid #21262d", padding: "4px 8px" },
  td: { fontSize: 12, color: "#c9d1d9", padding: "6px 8px", borderBottom: "1px solid #161b22" },
  badge: (c) => ({ display:"inline-block", fontSize:10, padding:"1px 6px", borderRadius:4, background: c+"22", color:c, fontWeight:700 }),
  link: { color: "#58a6ff", cursor: "pointer", textDecoration: "underline" },
};

const MODULES = [
  { label: "Order Management", path: "/m17-oms", color: "#58a6ff", desc: "Submit, amend, cancel orders" },
  { label: "Order Ticket", path: "/m17-order-ticket", color: "#3fb950", desc: "Quick order entry" },
  { label: "Trade Blotter", path: "/m17-blotter", color: "#e3b341", desc: "Real-time blotter" },
  { label: "Positions", path: "/m17-positions", color: "#f0883e", desc: "Long/short positions" },
  { label: "Portfolio Accounting", path: "/m17-accounting", color: "#a371f7", desc: "Cash, P&L, NAV" },
  { label: "Risk Limits", path: "/m17-risk", color: "#ff7b72", desc: "Pre-trade checks" },
  { label: "Paper Trading", path: "/m17-paper-trading", color: "#ffa657", desc: "Simulated execution" },
  { label: "Trade Analytics", path: "/m17-analytics", color: "#79c0ff", desc: "Win rate, Sharpe, Kelly" },
  { label: "TCA / Execution Cost", path: "/m17-tca", color: "#56d364", desc: "Spread, slippage, IS" },
  { label: "Performance Attribution", path: "/m17-attribution", color: "#d2a8ff", desc: "Brinson, factor, currency" },
  { label: "Broker Dashboard", path: "/m17-brokers", color: "#ff9f43", desc: "Broker registry & routing" },
  { label: "Execution Monitor", path: "/m17-execution", color: "#48dbfb", desc: "Live execution quality" },
];

export default function M17TradingDashboard() {
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/trading/paper/account")
      .then(r => r.json())
      .then(setAccount)
      .catch(() => setError("Paper trading engine offline — connect a backend to enable simulation"));
  }, []);

  const metrics = account ? [
    { label: "Cash", value: `$${account.cash?.toLocaleString("en-US", {minimumFractionDigits:2}) ?? "—"}`, sub: "Available" },
    { label: "Equity", value: `$${account.equity?.toLocaleString("en-US", {minimumFractionDigits:2}) ?? "—"}`, sub: "Paper NAV" },
    { label: "Unrealised P&L", value: `$${account.unrealised_pnl?.toFixed(2) ?? "—"}`, sub: "Open positions" },
    { label: "Trades Executed", value: account.trade_count ?? "—", sub: "Paper fills" },
  ] : [
    { label: "Cash", value: "—", sub: "" },
    { label: "Equity", value: "—", sub: "" },
    { label: "Unrealised P&L", value: "—", sub: "" },
    { label: "Trades", value: "—", sub: "" },
  ];

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>M17 — Institutional Trading & Portfolio Management</div>

      <div style={S.grid}>
        {metrics.map(m => (
          <div key={m.label} style={S.card}>
            <div style={S.label}>{m.label}</div>
            <div style={S.val}>{m.value}</div>
            <div style={S.sub}>{m.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
        {MODULES.map(m => (
          <div key={m.path} style={{ ...S.card, borderLeft: `3px solid ${m.color}`, cursor: "pointer" }}
               onClick={() => navigate(m.path)}>
            <div style={{ fontSize: 13, fontWeight: 700, color: m.color, marginBottom: 4 }}>{m.label}</div>
            <div style={{ fontSize: 11, color: "#8b949e" }}>{m.desc}</div>
          </div>
        ))}
      </div>

      {error && <div style={{ marginTop: 16, color: "#484f58", fontSize: 11, fontStyle: "italic" }}>{error}</div>}
    </div>
  );
}
