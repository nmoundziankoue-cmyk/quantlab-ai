import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#48dbfb", marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, cursor: "pointer", fontWeight: 600, marginTop: 8 },
  card: { background: "#161b22", borderRadius: 6, padding: "10px 14px" },
  cardLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase" },
  cardVal: (ok) => ({ fontSize: 16, fontWeight: 700, color: ok === null ? "#f0f6fc" : ok ? "#3fb950" : "#ff7b72", marginTop: 2 }),
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  gauge: (pct, c) => ({ height: 8, background: "#21262d", borderRadius: 4, overflow: "hidden", marginTop: 4 }),
  fill: (pct, c) => ({ height: "100%", width: `${Math.min(100, pct * 100)}%`, background: c, borderRadius: 4 }),
  shortfall: { background: "#161b22", borderRadius: 6, padding: 12, marginTop: 12 },
};

export default function M19RiskDashboard() {
  const [drift, setDrift] = useState("0.0002");
  const [vol, setVol] = useState("0.012");
  const [paths, setPaths] = useState("1000");
  const [steps, setSteps] = useState("252");
  const [ticker, setTicker] = useState("AAPL");
  const [orderQty, setOrderQty] = useState("5000");
  const [midPrice, setMidPrice] = useState("150");
  const [decisionPrice, setDecisionPrice] = useState("149");
  const [adv, setAdv] = useState("1000000");
  const [mcResult, setMcResult] = useState(null);
  const [shortfall, setShortfall] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const loadRisk = async () => {
    setLoading(true); setErr("");
    try {
      const r = await fetch("/quant/monte-carlo/gbm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mean_daily_return: parseFloat(drift), daily_volatility: parseFloat(vol), num_paths: parseInt(paths), num_steps: parseInt(steps) }),
      });
      if (r.ok) setMcResult(await r.json());

      const sr = await fetch("/quant/execution/implementation-shortfall", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker, order_quantity: parseFloat(orderQty),
          decision_price: parseFloat(decisionPrice), current_mid: parseFloat(midPrice),
          average_daily_volume: parseFloat(adv),
        }),
      });
      if (sr.ok) setShortfall(await sr.json());
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const mc = mcResult;

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Risk Dashboard</div>
      <div style={S.sub}>Portfolio VaR, Expected Shortfall, drawdown projections, and implementation shortfall.</div>

      <div style={S.section}>
        <div style={S.sHdr}>Parameters</div>
        <div style={S.grid2}>
          <div><label style={S.label}>Daily Drift</label><input style={S.input} value={drift} onChange={e => setDrift(e.target.value)} /></div>
          <div><label style={S.label}>Daily Volatility</label><input style={S.input} value={vol} onChange={e => setVol(e.target.value)} /></div>
          <div><label style={S.label}>MC Paths</label><input style={S.input} value={paths} onChange={e => setPaths(e.target.value)} /></div>
          <div><label style={S.label}>Horizon (steps)</label><input style={S.input} value={steps} onChange={e => setSteps(e.target.value)} /></div>
        </div>
        <div style={{ ...S.sHdr, fontSize: 12, marginTop: 8, marginBottom: 8 }}>Implementation Shortfall</div>
        <div style={S.grid2}>
          <div><label style={S.label}>Ticker</label><input style={S.input} value={ticker} onChange={e => setTicker(e.target.value)} /></div>
          <div><label style={S.label}>Order Qty</label><input style={S.input} value={orderQty} onChange={e => setOrderQty(e.target.value)} /></div>
          <div><label style={S.label}>Decision Price</label><input style={S.input} value={decisionPrice} onChange={e => setDecisionPrice(e.target.value)} /></div>
          <div><label style={S.label}>Current Mid</label><input style={S.input} value={midPrice} onChange={e => setMidPrice(e.target.value)} /></div>
        </div>
        <button style={S.btn} onClick={loadRisk} disabled={loading}>{loading ? "Computing…" : "Compute Risk"}</button>
        {err && <div style={S.err}>{err}</div>}
      </div>

      {mc && (
        <div style={S.section}>
          <div style={S.sHdr}>Portfolio Risk Metrics ({mc.num_paths} paths × {mc.num_steps}d)</div>
          <div style={S.grid4}>
            {[
              { label: "VaR 95%", val: `${(mc.var_95 * 100).toFixed(2)}%`, ok: mc.var_95 < 0.05 },
              { label: "VaR 99%", val: `${(mc.var_99 * 100).toFixed(2)}%`, ok: mc.var_99 < 0.10 },
              { label: "CVaR 95%", val: `${(mc.expected_shortfall_95 * 100).toFixed(2)}%`, ok: mc.expected_shortfall_95 < 0.07 },
              { label: "Max DD p50", val: `${(mc.max_drawdown_p50 * 100).toFixed(2)}%`, ok: mc.max_drawdown_p50 < 0.15 },
              { label: "Max DD p95", val: `${(mc.max_drawdown_p95 * 100).toFixed(2)}%`, ok: mc.max_drawdown_p95 < 0.30 },
              { label: "P(Ruin)", val: `${(mc.probability_of_ruin * 100).toFixed(2)}%`, ok: mc.probability_of_ruin < 0.01 },
              { label: "P(Profit)", val: `${(mc.probability_of_profit * 100).toFixed(2)}%`, ok: mc.probability_of_profit > 0.6 },
              { label: "Method", val: mc.method, ok: null },
            ].map(({ label, val, ok }) => (
              <div key={label} style={S.card}>
                <div style={S.cardLabel}>{label}</div>
                <div style={S.cardVal(ok)}>{val}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 6 }}>Drawdown Severity</div>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 2 }}>p50: {(mc.max_drawdown_p50 * 100).toFixed(2)}%</div>
            <div style={S.gauge(mc.max_drawdown_p50)}><div style={S.fill(mc.max_drawdown_p50, "#e3b341")} /></div>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 2, marginTop: 4 }}>p95: {(mc.max_drawdown_p95 * 100).toFixed(2)}%</div>
            <div style={S.gauge(mc.max_drawdown_p95)}><div style={S.fill(mc.max_drawdown_p95, "#ff7b72")} /></div>
          </div>
        </div>
      )}

      {shortfall && (
        <div style={S.section}>
          <div style={S.sHdr}>Implementation Shortfall</div>
          <div style={S.grid4}>
            {[
              ["Shortfall (bps)", shortfall.shortfall_bps?.toFixed(2)],
              ["Delay Cost (bps)", shortfall.delay_cost_bps?.toFixed(2)],
              ["Market Impact (bps)", shortfall.market_impact_bps?.toFixed(2)],
            ].map(([l, v]) => (
              <div key={l} style={S.card}>
                <div style={S.cardLabel}>{l}</div>
                <div style={{ ...S.cardVal(null), fontSize: 14 }}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
