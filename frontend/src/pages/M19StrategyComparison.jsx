import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#79c0ff", marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, cursor: "pointer", fontWeight: 600 },
  btnSmall: { background: "#238636", color: "#fff", border: "none", borderRadius: 4, padding: "4px 10px", fontSize: 11, cursor: "pointer" },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { background: "#161b22", padding: "7px 10px", textAlign: "left", color: "#8b949e" },
  td: { padding: "6px 10px", borderBottom: "1px solid #21262d", color: "#f0f6fc" },
  tag: (c) => ({ display: "inline-block", fontSize: 10, padding: "2px 6px", borderRadius: 4, background: c + "22", color: c }),
  idBox: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: 6, fontSize: 11, color: "#8b949e", marginBottom: 4 },
};

const METRICS = ["total_return", "annualized_return", "sharpe_ratio", "sortino_ratio", "max_drawdown", "volatility", "win_rate", "num_trades"];

const COLORS = ["#58a6ff", "#3fb950", "#e3b341", "#f0883e", "#ff7b72", "#a371f7"];

const DEFAULT_PRICE_PRESETS = {
  "Bull Run": [100, 102, 104, 107, 106, 109, 112, 115, 113, 118, 120, 124, 128, 125, 130],
  "Bear Market": [100, 98, 95, 92, 94, 90, 88, 85, 87, 83, 80, 78, 82, 79, 76],
  "Sideways": [100, 101, 99, 102, 100, 103, 101, 100, 102, 101, 99, 101, 102, 100, 101],
};

export default function M19StrategyComparison() {
  const [strategies, setStrategies] = useState([
    { name: "Bull Momentum", preset: "Bull Run", id: null, metrics: null },
    { name: "Bear Defense", preset: "Bear Market", id: null, metrics: null },
  ]);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const runStrategy = async (idx) => {
    const s = strategies[idx];
    const prices = DEFAULT_PRICE_PRESETS[s.preset] || DEFAULT_PRICE_PRESETS["Sideways"];
    const bars = prices.map((p, i) => ({
      date: `2024-01-${String(i + 1).padStart(2, "0")}`,
      open: p, high: p * 1.01, low: p * 0.99, close: p, volume: 10000,
    }));
    const r = await fetch("/quant/backtest/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        strategy_name: s.name,
        signals: [{ date: bars[0].date, ticker: "ASSET", signal_type: "LONG" }],
        price_data: { ASSET: bars },
        position_size_pct: 0.95,
      }),
    });
    const d = await r.json();
    const updated = [...strategies];
    updated[idx] = { ...s, id: d.backtest_id, metrics: d.metrics };
    setStrategies(updated);
    return d.backtest_id;
  };

  const runAll = async () => {
    setLoading(true); setErr("");
    try {
      const ids = await Promise.all(strategies.map((_, i) => runStrategy(i)));
      const r = await fetch("/quant/backtest/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backtest_ids: ids }),
      });
      if (r.ok) setComparison(await r.json());
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const addStrategy = () => {
    if (strategies.length >= 6) return;
    setStrategies(prev => [...prev, { name: `Strategy ${prev.length + 1}`, preset: "Sideways", id: null, metrics: null }]);
  };

  const best = (metric) => {
    if (!comparison) return null;
    const vals = strategies.map((s, i) => ({ i, v: comparison[s.id]?.[metric] ?? null })).filter(x => x.v !== null);
    if (!vals.length) return null;
    const isLower = ["max_drawdown", "volatility"].includes(metric);
    return isLower ? vals.reduce((a, b) => a.v < b.v ? a : b).i : vals.reduce((a, b) => a.v > b.v ? a : b).i;
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Strategy Comparison</div>
      <div style={S.sub}>Run multiple strategies simultaneously and compare risk-adjusted performance metrics.</div>

      <div style={S.section}>
        <div style={S.sHdr}>Strategy Setup</div>
        {strategies.map((s, i) => (
          <div key={i} style={{ display: "flex", gap: 10, marginBottom: 8, alignItems: "center" }}>
            <input style={{ ...S.input, maxWidth: 180 }} value={s.name} onChange={e => { const u = [...strategies]; u[i].name = e.target.value; setStrategies(u); }} />
            <select style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 12 }}
              value={s.preset} onChange={e => { const u = [...strategies]; u[i].preset = e.target.value; setStrategies(u); }}>
              {Object.keys(DEFAULT_PRICE_PRESETS).map(p => <option key={p}>{p}</option>)}
            </select>
            {s.id && <span style={S.tag("#3fb950")}>Done</span>}
          </div>
        ))}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button style={S.btn} onClick={runAll} disabled={loading}>{loading ? "Running all…" : "Run All & Compare"}</button>
          <button style={{ ...S.btn, background: "#30363d" }} onClick={addStrategy} disabled={strategies.length >= 6}>+ Add Strategy</button>
        </div>
        {err && <div style={S.err}>{err}</div>}
      </div>

      {strategies.some(s => s.metrics) && (
        <div style={S.section}>
          <div style={S.sHdr}>Performance Comparison</div>
          <table style={S.table}>
            <thead>
              <tr>
                <th style={S.th}>Metric</th>
                {strategies.map((s, i) => <th key={i} style={{ ...S.th, color: COLORS[i] }}>{s.name}</th>)}
              </tr>
            </thead>
            <tbody>
              {METRICS.map(m => {
                const bestIdx = best(m);
                return (
                  <tr key={m}>
                    <td style={{ ...S.td, color: "#8b949e" }}>{m.replace(/_/g, " ")}</td>
                    {strategies.map((s, i) => {
                      const v = s.metrics?.[m];
                      const display = v !== undefined && v !== null
                        ? (m.includes("return") || m.includes("drawdown") || m === "volatility" || m === "win_rate"
                          ? `${(v * 100).toFixed(2)}%` : v.toFixed(3))
                        : "—";
                      return (
                        <td key={i} style={{ ...S.td, fontWeight: bestIdx === i ? 700 : 400, color: bestIdx === i ? COLORS[i] : "#c9d1d9" }}>
                          {display}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
