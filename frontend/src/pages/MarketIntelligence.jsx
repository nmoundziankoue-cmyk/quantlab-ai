import { useState } from "react";
import { useSectorHeatmap, useMarketBreadth, useMarketRegime, useYieldCurve, useGlobalMacro, useMarketDashboard } from "../hooks/useMarketIntel";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid3: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 16 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20 },
  sectionTitle: { fontSize: 12, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  tabs: { display: "flex", gap: 4, marginBottom: 20, borderBottom: "1px solid #30363d" },
  tab: (a) => ({ padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600, borderBottom: `2px solid ${a ? "#58a6ff" : "transparent"}`, color: a ? "#58a6ff" : "#8b949e", marginBottom: -1 }),
  metricRow: { display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid #21262d" },
  metricLabel: { fontSize: 12, color: "#8b949e" },
  metricVal: { fontSize: 13, fontWeight: 600 },
  badge: (c) => ({ background: c + "22", color: c, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600, display: "inline-block" }),
  periodBtn: (a) => ({ background: a ? "#1f6feb" : "#21262d", border: `1px solid ${a ? "#1f6feb" : "#30363d"}`, borderRadius: 4, padding: "4px 10px", color: "#e6edf3", cursor: "pointer", fontSize: 12, fontWeight: a ? 600 : 400, marginRight: 6 }),
};

function SectorBar({ sector }) {
  const perf = sector.performance;
  const color = perf >= 0 ? "#3fb950" : "#f85149";
  const barW = Math.min(Math.abs(perf) * 6, 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: "1px solid #21262d" }}>
      <div style={{ width: 120, fontSize: 12, color: "#e6edf3", flexShrink: 0 }}>{sector.sector}</div>
      <div style={{ flex: 1, height: 10, background: "#21262d", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${barW}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
      <div style={{ width: 60, textAlign: "right", fontSize: 12, fontWeight: 600, color, flexShrink: 0 }}>
        {perf >= 0 ? "+" : ""}{perf.toFixed(2)}%
      </div>
    </div>
  );
}

function YieldCurveChart({ curve }) {
  if (!curve || !curve.length) return null;
  const yields = curve.map((p) => p.yield);
  const min = Math.min(...yields) - 0.2;
  const max = Math.max(...yields) + 0.2;
  const W = 400, H = 120;
  const pts = curve.map((p, i) => {
    const x = (i / (curve.length - 1)) * (W - 40) + 20;
    const y = H - 20 - ((p.yield - min) / (max - min)) * (H - 40);
    return `${x},${y}`;
  });
  return (
    <svg width={W} height={H} style={{ width: "100%", height: H }}>
      <polyline points={pts.join(" ")} fill="none" stroke="#58a6ff" strokeWidth={2} />
      {curve.map((p, i) => {
        const x = (i / (curve.length - 1)) * (W - 40) + 20;
        const y = H - 20 - ((p.yield - min) / (max - min)) * (H - 40);
        return (
          <g key={p.maturity}>
            <circle cx={x} cy={y} r={4} fill="#58a6ff" />
            <text x={x} y={H - 4} textAnchor="middle" fill="#8b949e" fontSize={9}>{p.maturity}</text>
          </g>
        );
      })}
    </svg>
  );
}

export default function MarketIntelligence() {
  const [tab, setTab] = useState("overview");
  const [period, setPeriod] = useState("1D");

  const { data: heatmap } = useSectorHeatmap(period);
  const { data: breadth } = useMarketBreadth();
  const { data: regime } = useMarketRegime();
  const { data: yieldCurve } = useYieldCurve();
  const { data: macro } = useGlobalMacro();
  const { data: dashboard } = useMarketDashboard();

  const tabs = [
    { k: "overview", l: "Overview" },
    { k: "sectors", l: "Sector Heatmap" },
    { k: "breadth", l: "Market Breadth" },
    { k: "macro", l: "Macro & Rates" },
  ];

  const regimeColor = {
    BULL_TRENDING: "#3fb950", BULL_CONSOLIDATING: "#56d364",
    BEAR_TRENDING: "#f85149", HIGH_VOLATILITY: "#f0883e", NEUTRAL: "#8b949e",
  }[regime?.regime] || "#8b949e";

  return (
    <div style={S.page}>
      <div style={S.title}>Market Intelligence</div>
      <div style={S.tabs}>
        {tabs.map(({ k, l }) => <div key={k} style={S.tab(tab === k)} onClick={() => setTab(k)}>{l}</div>)}
      </div>

      {tab === "overview" && dashboard && (
        <>
          <div style={S.grid3}>
            <div style={S.card}>
              <div style={S.sectionTitle}>Market Regime</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: regimeColor, marginBottom: 8 }}>{regime?.regime_label}</div>
              <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 8 }}>VIX: {regime?.vix?.toFixed(1)}</div>
              <span style={S.badge(regimeColor)}>{regime?.vol_regime}</span>
            </div>
            <div style={S.card}>
              <div style={S.sectionTitle}>Breadth</div>
              {[
                ["A/D Ratio", breadth?.ad_ratio?.toFixed(2)],
                ["% Above 200MA", `${breadth?.pct_above_200ma?.toFixed(1)}%`],
                ["52W Highs", breadth?.new_52w_highs],
                ["52W Lows", breadth?.new_52w_lows],
              ].map(([k, v]) => (
                <div key={k} style={S.metricRow}><span style={S.metricLabel}>{k}</span><span style={S.metricVal}>{v}</span></div>
              ))}
            </div>
            <div style={S.card}>
              <div style={S.sectionTitle}>Macro Snapshot</div>
              {dashboard?.macro_snapshot && Object.entries(dashboard.macro_snapshot).map(([k, v]) => (
                <div key={k} style={S.metricRow}>
                  <span style={S.metricLabel}>{k.replace(/_/g, " ").toUpperCase()}</span>
                  <span style={S.metricVal}>{typeof v === "number" ? v.toFixed(2) : v}</span>
                </div>
              ))}
            </div>
          </div>
          <div style={S.card}>
            <div style={S.sectionTitle}>Yield Curve</div>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: "#8b949e", marginRight: 12 }}>2s10s: {yieldCurve?.spread_2s10s?.toFixed(2)}%</span>
              <span style={S.badge(yieldCurve?.is_inverted ? "#f85149" : "#3fb950")}>{yieldCurve?.curve_shape?.toUpperCase()}</span>
            </div>
            <YieldCurveChart curve={yieldCurve?.curve} />
          </div>
        </>
      )}

      {tab === "sectors" && heatmap && (
        <div style={S.card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={S.sectionTitle}>Sector Performance</div>
            <div>
              {["1D", "1W", "1M", "YTD"].map((p) => (
                <button key={p} style={S.periodBtn(p === period)} onClick={() => setPeriod(p)}>{p}</button>
              ))}
            </div>
          </div>
          {heatmap.sectors?.map((s) => <SectorBar key={s.sector} sector={s} />)}
          <div style={{ marginTop: 12, fontSize: 12, color: "#8b949e" }}>
            Breadth: {((heatmap.market_breadth || 0) * 100).toFixed(0)}% of sectors positive
          </div>
        </div>
      )}

      {tab === "breadth" && breadth && (
        <div style={S.grid2}>
          <div style={S.card}>
            <div style={S.sectionTitle}>Advance / Decline</div>
            {[
              ["Universe", breadth.universe],
              ["Advancing", breadth.advancing],
              ["Declining", breadth.declining],
              ["A/D Ratio", breadth.ad_ratio?.toFixed(3)],
              ["McClellan Osc", breadth.mcclellan_oscillator?.toFixed(2)],
              ["Breadth Thrust", `${breadth.breadth_thrust?.toFixed(1)}%`],
            ].map(([k, v]) => (
              <div key={k} style={S.metricRow}><span style={S.metricLabel}>{k}</span><span style={S.metricVal}>{v}</span></div>
            ))}
          </div>
          <div style={S.card}>
            <div style={S.sectionTitle}>Moving Average Breadth</div>
            {[
              ["% Above 50MA", `${breadth.pct_above_50ma?.toFixed(1)}%`],
              ["% Above 200MA", `${breadth.pct_above_200ma?.toFixed(1)}%`],
              ["52W New Highs", breadth.new_52w_highs],
              ["52W New Lows", breadth.new_52w_lows],
              ["A/D Line", breadth.ad_line?.toLocaleString()],
            ].map(([k, v]) => (
              <div key={k} style={S.metricRow}><span style={S.metricLabel}>{k}</span><span style={S.metricVal}>{v}</span></div>
            ))}
          </div>
        </div>
      )}

      {tab === "macro" && macro && (
        <div style={S.grid2}>
          <div style={S.card}>
            <div style={S.sectionTitle}>US Indicators</div>
            {Object.entries(macro.us || {}).map(([k, v]) => (
              <div key={k} style={S.metricRow}><span style={S.metricLabel}>{k.replace(/_/g, " ").toUpperCase()}</span><span style={S.metricVal}>{v}</span></div>
            ))}
            <div style={{ ...S.sectionTitle, marginTop: 16 }}>Central Banks</div>
            {Object.entries(macro.central_banks || {}).map(([k, v]) => (
              <div key={k} style={S.metricRow}><span style={S.metricLabel}>{k.toUpperCase()}</span><span style={S.metricVal}>{v}%</span></div>
            ))}
          </div>
          <div style={S.card}>
            <div style={S.sectionTitle}>Yield Curve</div>
            <div style={{ marginBottom: 8 }}>
              <span style={S.badge(yieldCurve?.is_inverted ? "#f85149" : "#3fb950")}>{yieldCurve?.curve_shape?.toUpperCase()}</span>
              <span style={{ fontSize: 12, color: "#8b949e", marginLeft: 10 }}>2s10s: {yieldCurve?.spread_2s10s?.toFixed(2)}%</span>
            </div>
            <YieldCurveChart curve={yieldCurve?.curve} />
          </div>
        </div>
      )}
    </div>
  );
}
