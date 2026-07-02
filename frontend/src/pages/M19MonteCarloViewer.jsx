import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  tabs: { display: "flex", gap: 0, marginBottom: 16, borderBottom: "1px solid #30363d" },
  tab: (a) => ({ padding: "8px 16px", fontSize: 12, cursor: "pointer", color: a ? "#f0f6fc" : "#8b949e", borderBottom: a ? "2px solid #ff7b72" : "none", background: "none", border: "none", fontFamily: "monospace" }),
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#ff7b72", marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, cursor: "pointer", fontWeight: 600, marginTop: 8 },
  card: { background: "#161b22", borderRadius: 6, padding: "10px 14px" },
  cardLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase" },
  cardVal: { fontSize: 15, fontWeight: 700, color: "#f0f6fc", marginTop: 2 },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  ci: { background: "#161b22", borderRadius: 6, padding: 10, marginBottom: 8 },
};

export default function M19MonteCarloViewer() {
  const [tab, setTab] = useState("gbm");
  const [drift, setDrift] = useState("0.0003");
  const [vol, setVol] = useState("0.015");
  const [paths, setPaths] = useState("500");
  const [steps, setSteps] = useState("252");
  const [retText, setRetText] = useState("-0.01,0.005,0.012,0.003,-0.008,0.015,0.002,-0.005,0.009,0.001,-0.003,0.007,0.004,-0.002,0.006,0.008,-0.001,0.011,-0.004,0.003");
  const [result, setResult] = useState(null);
  const [cis, setCis] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const runGBM = async () => {
    setLoading(true); setErr("");
    try {
      const r = await fetch("/quant/monte-carlo/gbm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mean_daily_return: parseFloat(drift), daily_volatility: parseFloat(vol), num_paths: parseInt(paths), num_steps: parseInt(steps) }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(JSON.stringify(d)); return; }
      setResult(d);
      const ciR = await fetch(`/quant/monte-carlo/${d.simulation_id}/confidence-intervals`);
      if (ciR.ok) setCis(await ciR.json());
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const runBootstrap = async () => {
    setLoading(true); setErr("");
    const rets = retText.split(",").map(v => parseFloat(v.trim())).filter(v => !isNaN(v));
    try {
      const r = await fetch("/quant/monte-carlo/bootstrap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ daily_returns: rets, num_paths: parseInt(paths), num_steps: parseInt(steps) }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(JSON.stringify(d)); return; }
      setResult(d);
      const ciR = await fetch(`/quant/monte-carlo/${d.simulation_id}/confidence-intervals`);
      if (ciR.ok) setCis(await ciR.json());
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const run = tab === "gbm" ? runGBM : runBootstrap;

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Monte Carlo Viewer</div>
      <div style={S.sub}>Project portfolio risk via Geometric Brownian Motion or Bootstrap resampling.</div>

      <div style={S.tabs}>
        {["gbm", "bootstrap"].map(t => (
          <button key={t} style={S.tab(tab === t)} onClick={() => setTab(t)}>{t === "gbm" ? "GBM Log-Normal" : "Bootstrap Resample"}</button>
        ))}
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>{tab === "gbm" ? "GBM Parameters" : "Bootstrap Parameters"}</div>
        {tab === "gbm" ? (
          <div style={S.grid2}>
            <div><label style={S.label}>Daily Drift (mean return)</label><input style={S.input} value={drift} onChange={e => setDrift(e.target.value)} /></div>
            <div><label style={S.label}>Daily Volatility</label><input style={S.input} value={vol} onChange={e => setVol(e.target.value)} /></div>
          </div>
        ) : (
          <div>
            <label style={S.label}>Historical Daily Returns (comma-separated, min 10)</label>
            <input style={S.input} value={retText} onChange={e => setRetText(e.target.value)} />
          </div>
        )}
        <div style={S.grid2}>
          <div><label style={S.label}>Num Paths</label><input style={S.input} value={paths} onChange={e => setPaths(e.target.value)} /></div>
          <div><label style={S.label}>Num Steps</label><input style={S.input} value={steps} onChange={e => setSteps(e.target.value)} /></div>
        </div>
        <button style={S.btn} onClick={run} disabled={loading}>{loading ? "Simulating…" : "Run Simulation"}</button>
        {err && <div style={S.err}>{err}</div>}
      </div>

      {result && (
        <div style={S.section}>
          <div style={S.sHdr}>Risk Metrics ({result.num_paths} paths × {result.num_steps} steps)</div>
          <div style={S.grid4}>
            {[
              ["VaR 95%", `${(result.var_95 * 100).toFixed(2)}%`],
              ["VaR 99%", `${(result.var_99 * 100).toFixed(2)}%`],
              ["CVaR 95%", `${(result.expected_shortfall_95 * 100).toFixed(2)}%`],
              ["Max DD p50", `${(result.max_drawdown_p50 * 100).toFixed(2)}%`],
              ["Max DD p95", `${(result.max_drawdown_p95 * 100).toFixed(2)}%`],
              ["P(Ruin)", `${(result.probability_of_ruin * 100).toFixed(2)}%`],
              ["P(Profit)", `${(result.probability_of_profit * 100).toFixed(2)}%`],
              ["Method", result.method],
            ].map(([label, val]) => (
              <div key={label} style={S.card}>
                <div style={S.cardLabel}>{label}</div>
                <div style={S.cardVal}>{val}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {cis.length > 0 && (
        <div style={S.section}>
          <div style={S.sHdr}>Confidence Intervals</div>
          {cis.map((ci, i) => (
            <div key={i} style={S.ci}>
              <span style={{ color: "#58a6ff", fontWeight: 700 }}>{ci.metric}</span>
              <span style={{ color: "#8b949e", margin: "0 8px" }}>—</span>
              <span style={{ color: "#f0f6fc" }}>p5: {ci.p5?.toFixed(4)} | p50: {ci.p50?.toFixed(4)} | p95: {ci.p95?.toFixed(4)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
