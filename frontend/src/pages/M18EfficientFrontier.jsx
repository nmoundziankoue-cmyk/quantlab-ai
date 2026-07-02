import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#e3b341", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c = "#e3b341") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  kv: { display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #21262d33", fontSize: 12 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
};

const DEFAULT_HOLDINGS = [
  { ticker: "AAPL", weight: 0.20, expected_return: 0.18, volatility: 0.25 },
  { ticker: "MSFT", weight: 0.18, expected_return: 0.16, volatility: 0.22 },
  { ticker: "GOOGL", weight: 0.15, expected_return: 0.15, volatility: 0.28 },
  { ticker: "JPM", weight: 0.12, expected_return: 0.10, volatility: 0.20 },
  { ticker: "XOM", weight: 0.10, expected_return: 0.08, volatility: 0.18 },
];

export default function M18EfficientFrontier() {
  const [holdings, setHoldings] = useState(DEFAULT_HOLDINGS);
  const [frontier, setFrontier] = useState([]);
  const [optimal, setOptimal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [riskFreeRate, setRiskFreeRate] = useState("0.053");
  const [numPoints, setNumPoints] = useState("20");
  const [newHolding, setNewHolding] = useState({ ticker: "", weight: "", expected_return: "", volatility: "" });

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const compute = async () => {
    setLoading(true);
    const r = await post("/m18/portfolio/efficient-frontier", {
      holdings: holdings.map(h => ({ ticker: h.ticker, weight: h.weight, expected_annual_return: h.expected_return, annual_volatility: h.volatility })),
      risk_free_rate: parseFloat(riskFreeRate),
      num_points: parseInt(numPoints),
    });
    if (r.ok) {
      const data = await r.json();
      setFrontier(data.frontier || []);
      setOptimal(data.optimal_portfolio || null);
    }
    setLoading(false);
  };

  const addHolding = () => {
    if (!newHolding.ticker) return;
    setHoldings(p => [...p, { ticker: newHolding.ticker.toUpperCase(), weight: parseFloat(newHolding.weight) || 0.1, expected_return: parseFloat(newHolding.expected_return) || 0.1, volatility: parseFloat(newHolding.volatility) || 0.2 }]);
    setNewHolding({ ticker: "", weight: "", expected_return: "", volatility: "" });
  };

  const maxSharpe = frontier.length > 0 ? Math.max(...frontier.map(p => p.sharpe_ratio || 0)) : null;

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Efficient Frontier Optimizer</div>

      <div style={S.row2}>
        <div>
          <div style={S.section}>
            <div style={S.sHdr}>Portfolio Assets</div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, marginBottom: 10 }}>
              <thead><tr>{["Ticker","Weight","E[Return]","Volatility",""].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
              <tbody>
                {holdings.map((h, i) => (
                  <tr key={i}>
                    <td style={{ ...S.td, color: "#58a6ff" }}>{h.ticker}</td>
                    <td style={S.td}>{(h.weight * 100).toFixed(1)}%</td>
                    <td style={{ ...S.td, color: "#3fb950" }}>{(h.expected_return * 100).toFixed(1)}%</td>
                    <td style={{ ...S.td, color: "#f0883e" }}>{(h.volatility * 100).toFixed(1)}%</td>
                    <td style={S.td}><button onClick={() => setHoldings(p => p.filter((_, j) => j !== i))} style={{ background: "none", border: "none", color: "#ff7b72", cursor: "pointer", fontSize: 11 }}>✕</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr) auto", gap: 6 }}>
              {["ticker","weight","expected_return","volatility"].map(f => (
                <input key={f} style={{ ...S.input, marginBottom: 0 }} value={newHolding[f]} onChange={e => setNewHolding(p => ({ ...p, [f]: e.target.value }))} placeholder={f} />
              ))}
              <button style={S.btn("#56d364")} onClick={addHolding}>+</button>
            </div>
          </div>

          <div style={S.section}>
            <div style={S.sHdr}>Parameters</div>
            {[["riskFreeRate", "Risk-Free Rate (e.g. 0.053)"], ["numPoints", "Frontier Points (e.g. 20)"]].map(([f, l]) => (
              <div key={f}>
                <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{l}</div>
                {f === "riskFreeRate" ? <input style={S.input} value={riskFreeRate} onChange={e => setRiskFreeRate(e.target.value)} /> : <input style={S.input} value={numPoints} onChange={e => setNumPoints(e.target.value)} />}
              </div>
            ))}
            <button style={S.btn()} onClick={compute} disabled={loading}>{loading ? "Computing…" : "Compute Efficient Frontier"}</button>
          </div>
        </div>

        <div>
          {optimal && (
            <div style={{ ...S.section, marginBottom: 14 }}>
              <div style={S.sHdr}>Optimal Portfolio (Max Sharpe)</div>
              {[
                ["Expected Return", `${(optimal.expected_return * 100).toFixed(2)}%`, "#3fb950"],
                ["Volatility", `${(optimal.volatility * 100).toFixed(2)}%`, "#f0883e"],
                ["Sharpe Ratio", optimal.sharpe_ratio?.toFixed(3), "#e3b341"],
                ["Risk-Free Rate", `${(parseFloat(riskFreeRate) * 100).toFixed(2)}%`, "#8b949e"],
              ].map(([k, v, c]) => (
                <div key={k} style={S.kv}><span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: c, fontWeight: 700 }}>{v}</span></div>
              ))}
              {optimal.weights && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11, color: "#e3b341", marginBottom: 6 }}>Optimal Weights</div>
                  {Object.entries(optimal.weights).map(([tk, w]) => (
                    <div key={tk} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ width: 60, fontSize: 11, color: "#58a6ff" }}>{tk}</span>
                      <div style={{ width: `${(w * 200)}px`, height: 8, background: "#e3b341", borderRadius: 2 }} />
                      <span style={{ fontSize: 11, color: "#f0f6fc" }}>{(w * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {frontier.length > 0 && (
            <div style={S.section}>
              <div style={S.sHdr}>Frontier Points ({frontier.length})</div>
              <div style={{ position: "relative", height: 200, background: "#161b22", borderRadius: 8, marginBottom: 12, overflow: "hidden" }}>
                <svg width="100%" height="100%" viewBox="0 0 400 200">
                  {frontier.map((p, i) => {
                    const maxVol = Math.max(...frontier.map(f => f.volatility));
                    const minRet = Math.min(...frontier.map(f => f.expected_return));
                    const maxRet = Math.max(...frontier.map(f => f.expected_return));
                    const x = (p.volatility / maxVol) * 380 + 10;
                    const y = 190 - ((p.expected_return - minRet) / (maxRet - minRet || 1)) * 170;
                    const isOptimal = maxSharpe && Math.abs(p.sharpe_ratio - maxSharpe) < 0.001;
                    return <circle key={i} cx={x} cy={y} r={isOptimal ? 6 : 3} fill={isOptimal ? "#e3b341" : "#58a6ff44"} stroke={isOptimal ? "#e3b341" : "#58a6ff"} strokeWidth={1} />;
                  })}
                </svg>
                <div style={{ position: "absolute", bottom: 4, right: 8, fontSize: 9, color: "#8b949e" }}>X: Volatility → Y: Return ↑ · Gold = Max Sharpe</div>
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                <thead><tr>{["E[Return]","Volatility","Sharpe"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
                <tbody>
                  {frontier.slice(0, 12).map((p, i) => (
                    <tr key={i} style={{ background: maxSharpe && Math.abs(p.sharpe_ratio - maxSharpe) < 0.001 ? "#e3b34122" : "transparent" }}>
                      <td style={{ ...S.td, color: "#3fb950" }}>{(p.expected_return * 100).toFixed(2)}%</td>
                      <td style={{ ...S.td, color: "#f0883e" }}>{(p.volatility * 100).toFixed(2)}%</td>
                      <td style={{ ...S.td, color: "#e3b341", fontWeight: maxSharpe && Math.abs(p.sharpe_ratio - maxSharpe) < 0.001 ? 700 : 400 }}>{p.sharpe_ratio?.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
