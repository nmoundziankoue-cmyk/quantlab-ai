import { useState } from "react";
import { multiAssetApi } from "../api/multiAssetApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", fontFamily: "monospace", fontSize: 12, padding: "6px 10px" };

const DEMO_RETURNS = {
  SPY:  [0.012, -0.008, 0.015, 0.003, -0.011, 0.009, 0.007, -0.005, 0.011, 0.004, -0.007, 0.013, 0.002, -0.009, 0.016, 0.001, -0.003, 0.008, 0.014, -0.006],
  QQQ:  [0.018, -0.012, 0.022, 0.005, -0.016, 0.013, 0.011, -0.008, 0.017, 0.006, -0.011, 0.019, 0.003, -0.013, 0.024, 0.002, -0.005, 0.012, 0.021, -0.009],
  TLT:  [-0.005, 0.003, -0.007, -0.001, 0.004, -0.003, -0.002, 0.002, -0.004, -0.001, 0.003, -0.005, -0.001, 0.004, -0.008, -0.001, 0.002, -0.003, -0.006, 0.003],
  GLD:  [0.004, 0.002, 0.001, 0.006, 0.003, -0.001, 0.005, 0.002, 0.003, 0.001, 0.004, 0.002, 0.006, 0.001, 0.003, 0.005, -0.002, 0.004, 0.002, 0.001],
  BTC:  [0.031, -0.022, 0.041, 0.008, -0.028, 0.019, 0.015, -0.011, 0.028, 0.009, -0.018, 0.033, 0.005, -0.021, 0.038, 0.003, -0.008, 0.017, 0.035, -0.014],
};

function colorForCorr(v) {
  if (v >= 0.7) return "#3fb950";
  if (v >= 0.3) return "#58a6ff";
  if (v >= -0.3) return "#f0f6fc";
  if (v >= -0.7) return "#e3b341";
  return "#f85149";
}

function HeatmapCell({ value, isSelf }) {
  const bg = isSelf ? "#21262d" : `${colorForCorr(value)}22`;
  const color = isSelf ? "#8b949e" : colorForCorr(value);
  return (
    <td style={{ background: bg, color, textAlign: "center", padding: "10px 8px", fontSize: 12, fontWeight: isSelf ? 400 : 600, border: "1px solid #21262d", minWidth: 72 }}>
      {isSelf ? "1.00" : value.toFixed(2)}
    </td>
  );
}

export default function CorrelationMatrix() {
  const [matrix, setMatrix] = useState(null);
  const [tickers, setTickers] = useState(null);
  const [method, setMethod] = useState("pearson");
  const [window, setWindow] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const compute = async () => {
    setLoading(true); setError(null);
    try {
      const res = await multiAssetApi.correlationMatrix({
        returns_map: DEMO_RETURNS,
        method,
        window: window ? parseInt(window) : null,
      });
      setMatrix(res.data.matrix);
      setTickers(res.data.tickers);
    } catch (e) {
      setError(e.message);
    } finally { setLoading(false); }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1100 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — CROSS-ASSET ENGINE</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Correlation Matrix</h1>

      <div style={{ ...CARD, marginBottom: 20, display: "flex", gap: 16, alignItems: "flex-end", flexWrap: "wrap" }}>
        <div>
          <div style={LABEL}>Method</div>
          <select value={method} onChange={e => setMethod(e.target.value)} style={{ ...INPUT, appearance: "none", paddingRight: 24 }}>
            <option value="pearson">Pearson</option>
            <option value="rank">Spearman Rank</option>
            <option value="rolling">Rolling</option>
          </select>
        </div>
        <div>
          <div style={LABEL}>Window (optional)</div>
          <input type="number" value={window} onChange={e => setWindow(e.target.value)} placeholder="Full series" style={{ ...INPUT, width: 120 }} />
        </div>
        <button onClick={compute} disabled={loading} style={{ padding: "8px 20px", background: "#ffa65733", border: "1px solid #ffa657", borderRadius: 6, color: "#ffa657", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
          {loading ? "Computing…" : "Compute"}
        </button>
      </div>

      {error && <div style={{ color: "#f85149", marginBottom: 16, fontSize: 12 }}>{error}</div>}

      {!matrix && (
        <div style={CARD}>
          <div style={LABEL}>Demo Universe (click Compute)</div>
          {Object.keys(DEMO_RETURNS).map(t => (
            <div key={t} style={{ display: "flex", gap: 12, padding: "4px 0", fontSize: 12 }}>
              <span style={{ width: 48, fontWeight: 700, color: "#58a6ff" }}>{t}</span>
              <span style={{ color: "#8b949e" }}>{DEMO_RETURNS[t].length} periods</span>
            </div>
          ))}
        </div>
      )}

      {matrix && tickers && (
        <div style={CARD}>
          <div style={{ ...LABEL, marginBottom: 16 }}>Pairwise Correlation — {method.toUpperCase()}</div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", minWidth: 400 }}>
              <thead>
                <tr>
                  <th style={{ padding: "8px 12px", fontSize: 11, color: "#8b949e", textAlign: "left" }}></th>
                  {tickers.map(t => <th key={t} style={{ padding: "8px 10px", fontSize: 12, color: "#58a6ff", textAlign: "center" }}>{t}</th>)}
                </tr>
              </thead>
              <tbody>
                {tickers.map((rt, i) => (
                  <tr key={rt}>
                    <td style={{ padding: "10px 12px", fontSize: 12, fontWeight: 700, color: "#58a6ff" }}>{rt}</td>
                    {matrix[i].map((v, j) => <HeatmapCell key={j} value={v} isSelf={i === j} />)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: "flex", gap: 16, marginTop: 16, flexWrap: "wrap" }}>
            {[["≥ 0.7", "#3fb950", "Strong positive"], ["0.3–0.7", "#58a6ff", "Moderate positive"], ["-0.3–0.3", "#f0f6fc", "Weak / none"], ["-0.7–-0.3", "#e3b341", "Moderate negative"], ["≤ -0.7", "#f85149", "Strong negative"]].map(([range, color, label]) => (
              <div key={range} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
                <div style={{ width: 12, height: 12, background: color, borderRadius: 2 }} />
                <span style={{ color: "#8b949e" }}>{range} <span style={{ color }}>{label}</span></span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
