import { useNavigate } from "react-router-dom";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";

// ── Deterministic equity curve (sine-wave noise, no Math.random) ─────────────
function buildEquityCurve() {
  const data = [];
  let nav = 100_000;
  let bench = 100_000;
  const start = new Date("2024-01-02");
  const n = 52; // weekly
  for (let i = 0; i < n; i++) {
    // Portfolio: +27% / year with realistic swings
    const noise = Math.sin(i * 0.71 + 1.2) * 0.018 + Math.sin(i * 0.23 + 0.5) * 0.009;
    nav *= 1 + 0.27 / n + noise;
    // Benchmark (SPY): +23% / year
    const bNoise = Math.sin(i * 0.71 + 0.9) * 0.014 + Math.sin(i * 0.17 + 1.1) * 0.007;
    bench *= 1 + 0.23 / n + bNoise;
    const d = new Date(start);
    d.setDate(d.getDate() + i * 7);
    data.push({
      date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      portfolio: Math.round(nav),
      benchmark: Math.round(bench),
    });
  }
  return data;
}

const EQUITY_DATA = buildEquityCurve();

const ALLOCATION = [
  { name: "AAPL", weight: 0.18, color: "#6366f1" },
  { name: "MSFT", weight: 0.15, color: "#0ea5e9" },
  { name: "GOOGL", weight: 0.12, color: "#10b981" },
  { name: "NVDA", weight: 0.11, color: "#f59e0b" },
  { name: "AMZN", weight: 0.09, color: "#ef4444" },
  { name: "JPM",  weight: 0.08, color: "#8b5cf6" },
  { name: "META", weight: 0.07, color: "#06b6d4" },
  { name: "Other", weight: 0.20, color: "#334155" },
];

const ACTIVITY = [
  { time: "09:31", action: "Regime → BULL", detail: "AAPL · MA crossover confirmed", color: "#10b981" },
  { time: "09:45", action: "Alert fired", detail: "NVDA VaR breach — 2.4% 1-day", color: "#f59e0b" },
  { time: "10:02", action: "Backtest complete", detail: "Momentum · Sharpe 1.84 · +26.3%", color: "#6366f1" },
  { time: "10:17", action: "Correlation update", detail: "AAPL↔MSFT r=0.82, AAPL↔AMZN r=0.61", color: "#0ea5e9" },
  { time: "10:33", action: "Strategy ranked", detail: "Bull Trend #1 · Sharpe 2.12", color: "#10b981" },
  { time: "11:05", action: "Monte Carlo run", detail: "500 paths · VaR 95% = −3.1%", color: "#8b5cf6" },
];

const MODULES = [
  { label: "Quant Research", sub: "M19 · 12 modules", path: "/m19-dashboard", color: "#6366f1" },
  { label: "Real-Time OS", sub: "M18 · 20 modules", path: "/m18-dashboard", color: "#0ea5e9" },
  { label: "Regime Detection", sub: "M20 · BULL/BEAR/VOL", path: "/m20/regime", color: "#10b981" },
  { label: "Strategy Comparison", sub: "M20 · Sharpe ranking", path: "/m20/comparison", color: "#f59e0b" },
  { label: "Correlation Matrix", sub: "M20 · N×N Pearson", path: "/m20/correlation", color: "#ef4444" },
  { label: "Backtest Studio", sub: "M19 · Signal-driven", path: "/m19-backtest", color: "#8b5cf6" },
  { label: "Monte Carlo", sub: "M19 · GBM + Bootstrap", path: "/m19-monte-carlo", color: "#06b6d4" },
  { label: "Risk Dashboard", sub: "M19 · VaR · ES · DD", path: "/m19-risk", color: "#f0883e" },
];

function fmtUSD(v) {
  return "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 0 });
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "10px 14px" }}>
      <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 6 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ fontSize: 13, fontWeight: 600, color: p.color, marginBottom: 2 }}>
          {p.name === "portfolio" ? "Portfolio" : "S&P 500"}: {fmtUSD(p.value)}
        </div>
      ))}
    </div>
  );
};

export default function Dashboard() {
  const navigate = useNavigate();
  const last = EQUITY_DATA[EQUITY_DATA.length - 1];
  const first = EQUITY_DATA[0];
  const pnl = last.portfolio - first.portfolio;
  const pnlPct = ((last.portfolio / first.portfolio - 1) * 100).toFixed(1);
  const benchPct = ((last.benchmark / first.benchmark - 1) * 100).toFixed(1);
  const alpha = (parseFloat(pnlPct) - parseFloat(benchPct)).toFixed(1);

  const kpis = [
    { label: "Portfolio NAV", value: fmtUSD(last.portfolio), sub: "Global Macro · USD", color: "#f0f6fc" },
    { label: "P&L YTD", value: `+${fmtUSD(pnl)}`, sub: `+${pnlPct}% vs SPY +${benchPct}%`, color: "#3fb950" },
    { label: "Alpha", value: `+${alpha}%`, sub: "vs S&P 500 benchmark", color: "#58a6ff" },
    { label: "Sharpe Ratio", value: "1.84", sub: "Annualised · rf = 5.0%", color: "#f0f6fc" },
    { label: "Max Drawdown", value: "−4.2%", sub: "Peak-to-trough", color: "#ff7b72" },
    { label: "Win Rate", value: "61.5%", sub: "Profitable weeks", color: "#e3b341" },
  ];

  return (
    <div style={S.root}>
      {/* Header */}
      <div style={S.header}>
        <div>
          <h1 style={S.h1}>QuantLab AI</h1>
          <p style={S.sub}>Institutional Quant Research Platform · M0–M20 · Pure Python</p>
        </div>
        <div style={S.pills}>
          <span style={{ ...S.pill, background: "#10b98122", color: "#10b981" }}>● Live</span>
          <span style={{ ...S.pill, background: "#6366f122", color: "#818cf8" }}>4,660 tests passing</span>
          <span style={{ ...S.pill, background: "#0ea5e922", color: "#38bdf8" }}>40+ services</span>
        </div>
      </div>

      {/* KPI Row */}
      <div style={S.kpiGrid}>
        {kpis.map((k) => (
          <div key={k.label} style={S.kpiCard}>
            <div style={S.kpiLabel}>{k.label}</div>
            <div style={{ ...S.kpiVal, color: k.color }}>{k.value}</div>
            <div style={S.kpiSub}>{k.sub}</div>
          </div>
        ))}
      </div>

      {/* Chart + Allocation */}
      <div style={S.mainRow}>
        {/* Equity Curve */}
        <div style={{ ...S.section, flex: 1 }}>
          <div style={S.sHdr}>Portfolio Equity Curve — 2024 YTD</div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={EQUITY_DATA} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="gNav" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gBench" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#334155" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#334155" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
              <XAxis dataKey="date" tick={{ fill: "#8b949e", fontSize: 10 }} tickLine={false} interval={7} />
              <YAxis
                tick={{ fill: "#8b949e", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                width={48}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={100000} stroke="#30363d" strokeDasharray="4 2" />
              <Area type="monotone" dataKey="benchmark" name="benchmark" stroke="#4b5563" fill="url(#gBench)" strokeWidth={1.5} dot={false} />
              <Area type="monotone" dataKey="portfolio" name="portfolio" stroke="#6366f1" fill="url(#gNav)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 11, color: "#8b949e" }}>
            <span><span style={{ color: "#6366f1" }}>━</span> Portfolio</span>
            <span><span style={{ color: "#4b5563" }}>━</span> S&P 500</span>
          </div>
        </div>

        {/* Allocation */}
        <div style={{ ...S.section, width: 220 }}>
          <div style={S.sHdr}>Allocation</div>
          {ALLOCATION.map((a) => (
            <div key={a.name} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 3 }}>
                <span style={{ color: "#c9d1d9" }}>{a.name}</span>
                <span style={{ color: "#8b949e" }}>{(a.weight * 100).toFixed(0)}%</span>
              </div>
              <div style={{ height: 4, background: "#21262d", borderRadius: 2 }}>
                <div style={{ height: "100%", width: `${a.weight * 100}%`, background: a.color, borderRadius: 2 }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Activity + Modules */}
      <div style={S.mainRow}>
        {/* Recent Activity */}
        <div style={{ ...S.section, flex: 1 }}>
          <div style={S.sHdr}>Recent Activity</div>
          {ACTIVITY.map((a) => (
            <div key={a.time + a.action} style={S.actRow}>
              <span style={{ color: "#484f58", fontSize: 11, width: 38, flexShrink: 0 }}>{a.time}</span>
              <span style={{ ...S.actDot, background: a.color }} />
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#f0f6fc" }}>{a.action}</div>
                <div style={{ fontSize: 11, color: "#8b949e" }}>{a.detail}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Module Navigator */}
        <div style={{ ...S.section, flex: 1 }}>
          <div style={S.sHdr}>Platform Modules</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {MODULES.map((m) => (
              <button
                key={m.path}
                style={{ ...S.modCard, borderColor: m.color + "33" }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = m.color)}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = m.color + "33")}
                onClick={() => navigate(m.path)}
              >
                <div style={{ fontSize: 12, fontWeight: 700, color: m.color, marginBottom: 2 }}>{m.label}</div>
                <div style={{ fontSize: 10, color: "#8b949e" }}>{m.sub}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const S = {
  root: { padding: "28px 32px", maxWidth: 1200 },
  header: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 },
  h1: { fontSize: 22, fontWeight: 700, color: "#f0f6fc", margin: "0 0 4px" },
  sub: { fontSize: 12, color: "#8b949e", margin: 0 },
  pills: { display: "flex", gap: 8, alignItems: "center" },
  pill: { fontSize: 11, fontWeight: 600, padding: "3px 10px", borderRadius: 12 },
  kpiGrid: { display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12, marginBottom: 20 },
  kpiCard: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "14px 16px" },
  kpiLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 },
  kpiVal: { fontSize: 18, fontWeight: 700, marginBottom: 2 },
  kpiSub: { fontSize: 10, color: "#484f58" },
  mainRow: { display: "flex", gap: 16, marginBottom: 16 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "18px 20px" },
  sHdr: { fontSize: 12, fontWeight: 700, color: "#58a6ff", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 14 },
  actRow: { display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 12 },
  actDot: { width: 6, height: 6, borderRadius: "50%", marginTop: 4, flexShrink: 0 },
  modCard: {
    background: "#0d1117", border: "1px solid", borderRadius: 8,
    padding: "10px 12px", textAlign: "left", cursor: "pointer",
    transition: "border-color 0.15s", width: "100%",
  },
};
