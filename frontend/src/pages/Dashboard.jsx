import { useNavigate } from "react-router-dom";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";

// ── Deterministic equity curve ────────────────────────────────────────────────
function buildEquityCurve() {
  const data = [];
  let nav = 100_000, bench = 100_000;
  const start = new Date("2024-01-02");
  for (let i = 0; i < 52; i++) {
    const n = Math.sin(i * 0.71 + 1.2) * 0.018 + Math.sin(i * 0.23 + 0.5) * 0.009;
    nav   *= 1 + 0.27 / 52 + n;
    const b = Math.sin(i * 0.71 + 0.9) * 0.014 + Math.sin(i * 0.17 + 1.1) * 0.007;
    bench *= 1 + 0.23 / 52 + b;
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
  { name: "AAPL",  weight: 0.18, color: "#567EFF" },
  { name: "MSFT",  weight: 0.15, color: "#9D7FEA" },
  { name: "GOOGL", weight: 0.12, color: "#27C784" },
  { name: "NVDA",  weight: 0.11, color: "#E2A52B" },
  { name: "AMZN",  weight: 0.09, color: "#E5473E" },
  { name: "JPM",   weight: 0.08, color: "#7A84A0" },
  { name: "META",  weight: 0.07, color: "#454D66" },
  { name: "Other", weight: 0.20, color: "#232A3D" },
];

const ACTIVITY = [
  { time: "09:31", action: "Regime → BULL", detail: "AAPL · MA crossover confirmed", color: "#27C784" },
  { time: "09:45", action: "Alert fired", detail: "NVDA VaR breach — 2.4% 1-day", color: "#E2A52B" },
  { time: "10:02", action: "Backtest complete", detail: "Momentum · Sharpe 1.84 · +26.3%", color: "#9D7FEA" },
  { time: "10:17", action: "Correlation update", detail: "AAPL↔MSFT r=0.82, AAPL↔AMZN r=0.61", color: "#567EFF" },
  { time: "10:33", action: "Strategy ranked", detail: "Bull Trend #1 · Sharpe 2.12", color: "#27C784" },
  { time: "11:05", action: "Monte Carlo", detail: "500 paths · VaR 95% = −3.1%", color: "#E5473E" },
];

const MODULES = [
  { label: "Regime Detection",    sub: "M20 · BULL/BEAR/VOL",  path: "/m20/regime",     color: "#E2A52B" },
  { label: "Strategy Comparison", sub: "M20 · Sharpe ranking",  path: "/m20/comparison", color: "#9D7FEA" },
  { label: "Correlation Matrix",  sub: "M20 · N×N Pearson",     path: "/m20/correlation",color: "#27C784" },
  { label: "Backtest Studio",     sub: "M19 · Signal-driven",   path: "/m19-backtest",   color: "#567EFF" },
  { label: "Monte Carlo",         sub: "M19 · GBM + Bootstrap", path: "/m19-monte-carlo",color: "#9D7FEA" },
  { label: "Real-Time OS",        sub: "M18 · 20 modules",      path: "/m18-dashboard",  color: "#567EFF" },
  { label: "Factor Exposure",     sub: "M19 · OLS regression",  path: "/m19-factors",    color: "#E2A52B" },
  { label: "Risk Dashboard",      sub: "M19 · VaR · ES · DD",   path: "/m19-risk",       color: "#E5473E" },
];

const fmtUSD = (v) => "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 0 });

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#0B0D13",
      border: "1px solid #232A3D",
      borderRadius: 6,
      padding: "10px 14px",
      fontFamily: "var(--font-mono)",
    }}>
      <div style={{ fontSize: 10, color: "#7A84A0", marginBottom: 6 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ fontSize: 12, fontWeight: 600, color: p.dataKey === "portfolio" ? "#E2A52B" : "#454D66", marginBottom: 2 }}>
          {p.dataKey === "portfolio" ? "Portfolio" : "S&P 500"}: {fmtUSD(p.value)}
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const last  = EQUITY_DATA[EQUITY_DATA.length - 1];
  const first = EQUITY_DATA[0];
  const pnl     = last.portfolio - first.portfolio;
  const pnlPct  = ((last.portfolio / first.portfolio - 1) * 100).toFixed(1);
  const benchPct = ((last.benchmark / first.benchmark - 1) * 100).toFixed(1);
  const alpha   = (parseFloat(pnlPct) - parseFloat(benchPct)).toFixed(1);

  const kpis = [
    { label: "Portfolio NAV",  value: fmtUSD(last.portfolio), sub: "Global Macro · USD",       color: "#DDE2EE" },
    { label: "P&L YTD",        value: `+${fmtUSD(pnl)}`,     sub: `+${pnlPct}% return`,       color: "#27C784" },
    { label: "vs S&P 500",     value: `+${alpha}%`,           sub: `Benchmark +${benchPct}%`,  color: "#27C784" },
    { label: "Sharpe Ratio",   value: "1.84",                 sub: "Ann. · rf = 5.0%",         color: "#E2A52B" },
    { label: "Max Drawdown",   value: "−4.2%",                sub: "Peak-to-trough",            color: "#E5473E" },
    { label: "Win Rate",       value: "61.5%",                sub: "Profitable weeks",          color: "#E2A52B" },
  ];

  return (
    <div style={S.root}>
      {/* Header */}
      <div style={S.header}>
        <div>
          <h1 style={S.h1}>QuantLab AI</h1>
          <p style={S.h1Sub}>Institutional Quant Research · M0–M20 · Pure Python · 4,660 tests</p>
        </div>
        <div style={S.pills}>
          <span style={{ ...S.pill, color: "#27C784", background: "#27C78412" }}>● LIVE</span>
          <span style={{ ...S.pill, color: "#9D7FEA", background: "#9D7FEA12" }}>4,660 tests</span>
          <span style={{ ...S.pill, color: "#567EFF", background: "#567EFF12" }}>40+ services</span>
        </div>
      </div>

      {/* KPI row */}
      <div style={S.kpiGrid}>
        {kpis.map((k) => (
          <div key={k.label} style={S.kpiCard}>
            <div className="ql-label" style={{ marginBottom: 6 }}>{k.label}</div>
            <div className="ql-value" style={{ fontSize: 24, fontWeight: 600, color: k.color, marginBottom: 2, lineHeight: 1 }}>
              {k.value}
            </div>
            <div style={S.kpiSub}>{k.sub}</div>
          </div>
        ))}
      </div>

      {/* Chart + Allocation */}
      <div style={S.row}>
        <div style={{ ...S.panel, flex: 1 }}>
          <div style={S.panelTitle}>Equity Curve — 2024 YTD</div>
          <ResponsiveContainer width="100%" height={210}>
            <AreaChart data={EQUITY_DATA} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="gNav" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#E2A52B" stopOpacity={0.18} />
                  <stop offset="95%" stopColor="#E2A52B" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gBench" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#232A3D" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="#232A3D" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#232A3D" />
              <XAxis dataKey="date"  tick={{ fill: "#454D66", fontSize: 9 }} tickLine={false} interval={8} />
              <YAxis tick={{ fill: "#454D66", fontSize: 9 }} tickLine={false} axisLine={false}
                     tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} width={44} />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine y={100000} stroke="#232A3D" strokeDasharray="4 2" />
              <Area type="monotone" dataKey="benchmark" stroke="#232A3D" fill="url(#gBench)" strokeWidth={1.5} dot={false} />
              <Area type="monotone" dataKey="portfolio" stroke="#E2A52B" fill="url(#gNav)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", gap: 16, marginTop: 8, fontFamily: "var(--font-mono)", fontSize: 10, color: "#454D66" }}>
            <span><span style={{ color: "#E2A52B" }}>━</span> Portfolio</span>
            <span><span style={{ color: "#232A3D" }}>━</span> S&P 500</span>
          </div>
        </div>

        <div style={{ ...S.panel, width: 208 }}>
          <div style={S.panelTitle}>Allocation</div>
          {ALLOCATION.map((a) => (
            <div key={a.name} style={{ marginBottom: 9 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#DDE2EE" }}>{a.name}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#7A84A0" }}>{(a.weight * 100).toFixed(0)}%</span>
              </div>
              <div style={{ height: 3, background: "#232A3D", borderRadius: 2 }}>
                <div style={{ height: "100%", width: `${a.weight * 100}%`, background: a.color, borderRadius: 2 }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Activity + Modules */}
      <div style={S.row}>
        <div style={{ ...S.panel, flex: 1 }}>
          <div style={S.panelTitle}>Activity Log</div>
          {ACTIVITY.map((a) => (
            <div key={a.time + a.action} style={S.actRow}>
              <span className="ql-value" style={{ fontSize: 10, color: "#454D66", width: 36, flexShrink: 0 }}>{a.time}</span>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: a.color, flexShrink: 0, marginTop: 3 }} />
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#DDE2EE", fontFamily: "var(--font-display)" }}>{a.action}</div>
                <div className="ql-value" style={{ fontSize: 10, color: "#7A84A0" }}>{a.detail}</div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ ...S.panel, flex: 1 }}>
          <div style={S.panelTitle}>Platform Modules</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
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
                <div className="ql-value" style={{ fontSize: 9, color: "#454D66" }}>{m.sub}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const S = {
  root:     { padding: "28px 32px", maxWidth: 1200 },
  header:   { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 },
  h1:       { fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700, color: "#DDE2EE", margin: "0 0 4px", lineHeight: 1.2 },
  h1Sub:    { fontFamily: "var(--font-mono)", fontSize: 10, color: "#454D66", margin: 0, letterSpacing: "0.04em" },
  pills:    { display: "flex", gap: 8, alignItems: "center" },
  pill:     { fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 600, padding: "3px 10px", borderRadius: 4, letterSpacing: "0.04em" },
  kpiGrid:  { display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10, marginBottom: 16 },
  kpiCard:  { background: "#131720", border: "1px solid #232A3D", borderRadius: 7, padding: "14px 16px" },
  kpiSub:   { fontFamily: "var(--font-mono)", fontSize: 9, color: "#454D66", marginTop: 2 },
  row:      { display: "flex", gap: 12, marginBottom: 12 },
  panel:    { background: "#131720", border: "1px solid #232A3D", borderRadius: 7, padding: "16px 18px" },
  panelTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 10,
    fontWeight: 700,
    color: "#567EFF",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    marginBottom: 14,
  },
  actRow:   { display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 10 },
  modCard:  {
    background: "#131720",
    border: "1px solid",
    borderRadius: 6,
    padding: "10px 12px",
    textAlign: "left",
    cursor: "pointer",
    transition: "border-color 0.15s",
    width: "100%",
  },
};
