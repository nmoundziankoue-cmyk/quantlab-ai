import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

const KPIS = [
  { label: "Services",   numValue: 6,   sub: "Quant engines" },
  { label: "Endpoints",  numValue: 111, sub: "REST API routes" },
  { label: "Tests",      numValue: 422, sub: "All passing" },
  { label: "Optimisers", numValue: 5,   sub: "MV/MinVar/Sharpe/RP/FC" },
  { label: "MC Methods", numValue: 2,   sub: "Bootstrap + GBM" },
  { label: "Factors",    numValue: 7,   sub: "Mkt/Size/Val/Mom/Qual/LV/Custom" },
];

const MODULES = [
  { label: "Backtest Studio",    path: "/m19-backtest",          color: "#58a6ff", desc: "Signal-driven backtesting" },
  { label: "Equity Curve",       path: "/m19-equity-curve",      color: "#3fb950", desc: "P&L visualisation" },
  { label: "Execution Sim",      path: "/m19-execution",         color: "#e3b341", desc: "Order fill simulation" },
  { label: "Walk-Forward",       path: "/m19-walk-forward",      color: "#f0883e", desc: "OOS validation" },
  { label: "Monte Carlo",        path: "/m19-monte-carlo",       color: "#ff7b72", desc: "Risk projection" },
  { label: "Factor Models",      path: "/m19-factor-exposure",   color: "#a371f7", desc: "Multi-factor regression" },
  { label: "Optimization Lab",   path: "/m19-optimization",      color: "#ffa657", desc: "MV, Sharpe, Risk Parity" },
  { label: "Strategy Compare",   path: "/m19-strategy-compare",  color: "#79c0ff", desc: "Cross-strategy analysis" },
  { label: "Factor Exposure",    path: "/m19-factor-exposure",   color: "#56d364", desc: "Betas & attribution" },
  { label: "Efficient Frontier", path: "/m19-frontier",          color: "#d2a8ff", desc: "Portfolio frontier" },
  { label: "Scenario Engine",    path: "/m19-scenarios",         color: "#ff9f43", desc: "Stress & scenario tests" },
  { label: "Risk Dashboard",     path: "/m19-risk",              color: "#48dbfb", desc: "VaR, drawdown, shortfall" },
];

// ── Count-up hook ─────────────────────────────────────────────────────────────
function useCountUp(to, duration = 1400) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let raf;
    let start;
    const step = (ts) => {
      if (!start) start = ts;
      const t = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setV(eased * to);
      if (t < 1) raf = requestAnimationFrame(step);
      else setV(to);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [to, duration]);
  return v;
}

// ── Animated KPI cell ─────────────────────────────────────────────────────────
function KpiCell({ label, numValue, sub, delay }) {
  const animated = useCountUp(numValue, 1200);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const id = setTimeout(() => setVisible(true), delay * 1000);
    return () => clearTimeout(id);
  }, [delay]);

  return (
    <div style={{
      ...S.card,
      opacity: visible ? 1 : 0,
      transform: `translateY(${visible ? 0 : 6}px)`,
      transition: "opacity 0.35s ease-out, transform 0.35s ease-out",
    }}>
      <div style={S.label}>{label}</div>
      <div style={S.val}>{Math.round(animated)}</div>
      <div style={S.vsub}>{sub}</div>
    </div>
  );
}

export default function M19Dashboard() {
  const navigate = useNavigate();
  const [caps, setCaps] = useState(null);

  useEffect(() => {
    fetch("/quant/capabilities").then(r => r.json()).then(setCaps).catch(() => {});
  }, []);

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>M19 — Quant Research Engine</div>
      <div style={S.sub}>Backtesting · Execution Simulation · Walk-Forward · Monte Carlo · Factor Models · Portfolio Optimisation</div>

      {/* KPI row — count-up on mount */}
      <div style={S.grid6}>
        {KPIS.map((k, i) => (
          <KpiCell key={k.label} {...k} delay={i * 0.07} />
        ))}
      </div>

      {/* Engine Capabilities */}
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

      {/* Modules — spring hover */}
      <div style={S.section}>
        <div style={S.sHdr}>Modules</div>
        <div style={S.modGrid}>
          {MODULES.map((m) => (
            <motion.div
              key={m.path}
              style={S.mod(m.color)}
              whileHover={{ scale: 1.03, y: -2 }}
              transition={{ type: "spring", stiffness: 480, damping: 26 }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = m.color + "77";
                e.currentTarget.style.boxShadow = `0 6px 20px ${m.color}18`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = m.color + "33";
                e.currentTarget.style.boxShadow = "none";
              }}
              onClick={() => navigate(m.path)}
            >
              <div style={S.modTitle}>{m.label}</div>
              <div style={S.modDesc}>{m.desc}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

const S = {
  wrap:    { padding: 24, fontFamily: "monospace" },
  hdr:     { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub:     { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  grid3:   { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 24 },
  grid6:   { display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 14, marginBottom: 24 },
  card:    { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" },
  label:   { fontSize: 11, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 },
  val:     { fontSize: 20, fontWeight: 700, color: "#f0f6fc" },
  vsub:    { fontSize: 11, color: "#8b949e", marginTop: 2 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr:    { fontSize: 14, fontWeight: 700, color: "#58a6ff", marginBottom: 16 },
  modGrid: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 },
  mod: (c) => ({
    background: "#0d1117",
    border: `1px solid ${c}33`,
    borderRadius: 8,
    padding: "14px 16px",
    cursor: "pointer",
    transition: "border-color 0.15s, box-shadow 0.2s",
  }),
  modTitle: { fontSize: 12, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  modDesc:  { fontSize: 11, color: "#8b949e" },
};
