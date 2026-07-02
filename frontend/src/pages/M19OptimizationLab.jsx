import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  tabs: { display: "flex", gap: 0, marginBottom: 16, borderBottom: "1px solid #30363d" },
  tab: (a) => ({ padding: "8px 16px", fontSize: 12, cursor: "pointer", color: a ? "#f0f6fc" : "#8b949e", borderBottom: a ? "2px solid #ffa657" : "none", background: "none", border: "none", fontFamily: "monospace" }),
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#ffa657", marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, cursor: "pointer", fontWeight: 600, marginTop: 8 },
  card: { background: "#161b22", borderRadius: 6, padding: "10px 14px" },
  cardLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase" },
  cardVal: { fontSize: 15, fontWeight: 700, color: "#f0f6fc", marginTop: 2 },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  barWrap: { marginTop: 12 },
  bar: (pct, c) => ({ height: 20, width: `${Math.min(100, pct * 100)}%`, background: c, borderRadius: 3, display: "flex", alignItems: "center", paddingLeft: 6, fontSize: 10, color: "#fff", minWidth: 30 }),
  barRow: { display: "flex", alignItems: "center", gap: 10, marginBottom: 6 },
  barLabel: { fontSize: 11, color: "#8b949e", width: 60, textAlign: "right" },
};

const COLORS = ["#58a6ff", "#3fb950", "#e3b341", "#f0883e", "#a371f7", "#ff7b72"];

const OPT_TYPES = [
  { key: "mean-variance", label: "Mean-Variance" },
  { key: "min-variance", label: "Min Variance" },
  { key: "max-sharpe", label: "Max Sharpe" },
  { key: "risk-parity", label: "Risk Parity" },
];

const PRESET_TICKERS = ["AAPL", "MSFT", "JPM", "AMZN"];
const PRESET_ER = { AAPL: 0.15, MSFT: 0.12, JPM: 0.09, AMZN: 0.14 };
const PRESET_COV = {
  AAPL: { AAPL: 0.040, MSFT: 0.015, JPM: 0.005, AMZN: 0.020 },
  MSFT: { AAPL: 0.015, MSFT: 0.035, JPM: 0.007, AMZN: 0.018 },
  JPM: { AAPL: 0.005, MSFT: 0.007, JPM: 0.025, AMZN: 0.005 },
  AMZN: { AAPL: 0.020, MSFT: 0.018, JPM: 0.005, AMZN: 0.042 },
};

export default function M19OptimizationLab() {
  const [optType, setOptType] = useState("mean-variance");
  const [riskAversion, setRiskAversion] = useState("3.0");
  const [result, setResult] = useState(null);
  const [frontier, setFrontier] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const buildPayload = () => {
    const base = {
      tickers: PRESET_TICKERS,
      covariance_matrix: PRESET_COV,
    };
    if (optType !== "min-variance" && optType !== "risk-parity") {
      base.expected_returns = PRESET_ER;
    }
    if (optType === "mean-variance") base.risk_aversion = parseFloat(riskAversion);
    return base;
  };

  const optimize = async () => {
    setLoading(true); setErr("");
    try {
      const r = await fetch(`/quant/optimize/${optType}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload()),
      });
      const d = await r.json();
      if (!r.ok) { setErr(JSON.stringify(d)); }
      else setResult(d);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const loadFrontier = async () => {
    setLoading(true); setErr("");
    try {
      const r = await fetch("/quant/optimize/frontier", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tickers: PRESET_TICKERS, expected_returns: PRESET_ER, covariance_matrix: PRESET_COV, n_points: 15 }),
      });
      const d = await r.json();
      if (r.ok && d.points) setFrontier(d.points);
      else setErr(JSON.stringify(d));
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const weights = result?.weights || {};
  const tickers = Object.keys(weights);

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Optimization Lab</div>
      <div style={S.sub}>Mean-Variance, Min-Variance, Max-Sharpe, and Risk Parity portfolio construction.</div>

      <div style={S.section}>
        <div style={S.sHdr}>Objective</div>
        <div style={S.tabs}>
          {OPT_TYPES.map(o => (
            <button key={o.key} style={S.tab(optType === o.key)} onClick={() => setOptType(o.key)}>{o.label}</button>
          ))}
        </div>
        {optType === "mean-variance" && (
          <div style={{ ...S.grid2, marginTop: 8 }}>
            <div>
              <label style={S.label}>Risk Aversion (λ)</label>
              <input style={S.input} value={riskAversion} onChange={e => setRiskAversion(e.target.value)} />
            </div>
          </div>
        )}
        <div style={{ fontSize: 11, color: "#8b949e", marginTop: 8 }}>
          Universe: {PRESET_TICKERS.join(", ")} — using preset expected returns and covariance matrix
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <button style={S.btn} onClick={optimize} disabled={loading}>{loading ? "Optimising…" : "Optimise"}</button>
          <button style={{ ...S.btn, background: "#1f6feb" }} onClick={loadFrontier} disabled={loading}>Compute Frontier</button>
        </div>
        {err && <div style={S.err}>{err}</div>}
      </div>

      {result && (
        <div style={S.section}>
          <div style={S.sHdr}>{result.optimization_type} Result</div>
          <div style={S.grid4}>
            {[
              ["Expected Return", `${(result.expected_return * 100).toFixed(2)}%`],
              ["Volatility", `${(result.volatility * 100).toFixed(2)}%`],
              ["Sharpe Ratio", result.sharpe_ratio?.toFixed(3)],
              ["Div. Ratio", result.diversification_ratio?.toFixed(3)],
            ].map(([l, v]) => (
              <div key={l} style={S.card}>
                <div style={S.cardLabel}>{l}</div>
                <div style={S.cardVal}>{v}</div>
              </div>
            ))}
          </div>
          <div style={S.barWrap}>
            <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 8, marginTop: 12 }}>Portfolio Weights</div>
            {tickers.map((t, i) => (
              <div key={t} style={S.barRow}>
                <span style={S.barLabel}>{t}</span>
                <div style={S.bar(weights[t] || 0, COLORS[i % COLORS.length])}>
                  {((weights[t] || 0) * 100).toFixed(1)}%
                </div>
                <span style={{ fontSize: 11, color: "#8b949e" }}>RC: {(result.risk_contributions?.[t] * 100 || 0).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {frontier.length > 0 && (
        <div style={S.section}>
          <div style={S.sHdr}>Efficient Frontier ({frontier.length} points)</div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr>{["Vol", "Ret", "Sharpe", ...PRESET_TICKERS].map(h => (
                  <th key={h} style={{ background: "#161b22", padding: "5px 8px", textAlign: "left", color: "#8b949e" }}>{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {frontier.map((p, i) => (
                  <tr key={i}>
                    <td style={{ padding: "4px 8px", borderBottom: "1px solid #21262d", color: "#f0f6fc" }}>{(p.volatility * 100).toFixed(2)}%</td>
                    <td style={{ padding: "4px 8px", borderBottom: "1px solid #21262d", color: "#f0f6fc" }}>{(p.expected_return * 100).toFixed(2)}%</td>
                    <td style={{ padding: "4px 8px", borderBottom: "1px solid #21262d", color: "#58a6ff" }}>{p.sharpe_ratio?.toFixed(3)}</td>
                    {PRESET_TICKERS.map(t => (
                      <td key={t} style={{ padding: "4px 8px", borderBottom: "1px solid #21262d", color: "#c9d1d9" }}>{((p.weights?.[t] || 0) * 100).toFixed(1)}%</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
