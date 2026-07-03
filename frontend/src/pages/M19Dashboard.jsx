import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 22, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  grid3: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 24 },
  grid6: { display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 14, marginBottom: 24 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" },
  label: { fontSize: 11, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 },
  val: { fontSize: 20, fontWeight: 700, color: "#f0f6fc" },
  vsub: { fontSize: 11, color: "#8b949e", marginTop: 2 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#58a6ff", marginBottom: 16 },
  modGrid: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 },
  mod: (c) => ({ background: "#0d1117", border: `1px solid ${c}33`, borderRadius: 8, padding: "14px 16px", cursor: "pointer" }),
  modTitle: { fontSize: 12, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  modDesc: { fontSize: 11, color: "#8b949e" },
};

const MODULES = [
  { label: "Backtest Studio", path: "/m19-backtest", color: "#58a6ff", desc: "Signal-driven backtesting" },
  { label: "Equity Curve", path: "/m19-equity-curve", color: "#3fb950", desc: "P&L visualisation" },
  { label: "Execution Sim", path: "/m19-execution", color: "#e3b341", desc: "Order fill simulation" },
  { label: "Walk-Forward", path: "/m19-walk-forward", color: "#f0883e", desc: "OOS validation" },
  { label: "Monte Carlo", path: "/m19-monte-carlo", color: "#ff7b72", desc: "Risk projection" },
  { label: "Factor Models", path: "/m19-factor-models", color: "#a371f7", desc: "Multi-factor regression" },
  { label: "Optimization Lab", path: "/m19-optimization", color: "#ffa657", desc: "MV, Sharpe, Risk Parity" },
  { label: "Strategy Compare", path: "/m19-strategy-compare", color: "#79c0ff", desc: "Cross-strategy analysis" },
  { label: "Factor Exposure", path: "/m19-factor-exposure", color: "#56d364", desc: "Betas & attribution" },
  { label: "Efficient Frontier", path: "/m19-frontier", color: "#d2a8ff", desc: "Portfolio frontier" },
  { label: "Scenario Engine", path: "/m19-scenarios", color: "#ff9f43", desc: "Stress & scenario tests" },
  { label: "Risk Dashboard", path: "/m19-risk", color: "#48dbfb", desc: "VaR, drawdown, shortfall" },
];

export default function M19Dashboard() {
  const navigate = useNavigate();
  const [caps, setCaps] = useState(null);

  useEffect(() => {
    fetch("/quant/capabilities").then(r => r.json()).then(setCaps).catch(() => {});
  }, []);

  const kpis = [
    { label: "Services", value: "6", sub: "Quant engines" },
    { label: "Endpoints", value: "111", sub: "REST API routes" },
    { label: "Tests", value: "422", sub: "All passing" },
    { label: "Optimisers", value: "5", sub: "MV/MinVar/Sharpe/RP/FC" },
    { label: "MC Methods", value: "2", sub: "Bootstrap + GBM" },
    { label: "Factors", value: "7", sub: "Mkt/Size/Val/Mom/Qual/LV/Custom" },
  ];

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>M19 — Quant Research Engine</div>
      <div style={S.sub}>Backtesting · Execution Simulation · Walk-Forward · Monte Carlo · Factor Models · Portfolio Optimisation</div>

      <div style={S.grid6}>
        {kpis.map(k => (
          <div key={k.label} style={S.card}>
            <div style={S.label}>{k.label}</div>
            <div style={S.val}>{k.value}</div>
            <div style={S.vsub}>{k.sub}</div>
          </div>
        ))}
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Engine Capabilities</div>
        <div style={S.grid3}>
          {caps && Object.entries(caps).map(([k, v]) => (
            <div key={k} style={S.card}>
              <div style={S.label}>{k}</div>
              <div style={{ fontSize: 12, color: "#f0f6fc" }}>{JSON.stringify(v, null, 1).slice(0, 120)}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Modules</div>
        <div style={S.modGrid}>
          {MODULES.map(m => (
            <div key={m.path} style={S.mod(m.color)} onClick={() => navigate(m.path)}>
              <div style={S.modTitle}>{m.label}</div>
              <div style={S.modDesc}>{m.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
