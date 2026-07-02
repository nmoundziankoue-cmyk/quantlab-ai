import { useState } from "react";
import { multiAssetApi } from "../api/multiAssetApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };

const DEMO_RETURNS = {
  "SPY":  [0.012,-0.008,0.015,0.003,-0.011,0.009,0.007,-0.005,0.011,0.004,-0.007,0.013,0.002,-0.009,0.016,0.001,-0.003,0.008,0.014,-0.006],
  "TLT":  [-0.005,0.003,-0.007,-0.001,0.004,-0.003,-0.002,0.002,-0.004,-0.001,0.003,-0.005,-0.001,0.004,-0.008,-0.001,0.002,-0.003,-0.006,0.003],
  "GLD":  [0.004,0.002,0.001,0.006,0.003,-0.001,0.005,0.002,0.003,0.001,0.004,0.002,0.006,0.001,0.003,0.005,-0.002,0.004,0.002,0.001],
  "BTC":  [0.031,-0.022,0.041,0.008,-0.028,0.019,0.015,-0.011,0.028,0.009,-0.018,0.033,0.005,-0.021,0.038,0.003,-0.008,0.017,0.035,-0.014],
};

export default function CrossAssetExplorer() {
  const [tab, setTab] = useState("lead-lag");
  const [leadLag, setLeadLag] = useState(null);
  const [spillover, setSpillover] = useState(null);
  const [sync, setSync] = useState(null);
  const [depGraph, setDepGraph] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const tickers = Object.keys(DEMO_RETURNS);
      const [ll, sp, sy, dg] = await Promise.all([
        multiAssetApi.leadLag({ returns_a: DEMO_RETURNS.SPY, returns_b: DEMO_RETURNS.BTC, ticker_a: "SPY", ticker_b: "BTC", max_lag: 5 }),
        multiAssetApi.spillover({ returns_map: DEMO_RETURNS, lag: 1 }),
        multiAssetApi.synchronization({ returns_map: DEMO_RETURNS }),
        multiAssetApi.dependencyGraph({ returns_map: DEMO_RETURNS }),
      ]);
      setLeadLag(ll.data);
      setSpillover(sp.data);
      setSync(sy.data);
      setDepGraph(dg.data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1100 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — CROSS-ASSET ANALYTICS</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Cross-Asset Explorer</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20, alignItems: "center" }}>
        {["lead-lag", "spillover", "sync", "graph"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid", borderColor: tab === t ? "#ffa657" : "#21262d", background: tab === t ? "#ffa65722" : "transparent", color: tab === t ? "#ffa657" : "#8b949e", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>{t.toUpperCase()}</button>
        ))}
        <button onClick={load} disabled={loading} style={{ marginLeft: "auto", padding: "6px 16px", background: "#ffa65733", border: "1px solid #ffa657", borderRadius: 6, color: "#ffa657", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
          {loading ? "Analysing…" : "Run Analysis"}
        </button>
      </div>

      {error && <div style={{ color: "#f85149", marginBottom: 12, fontSize: 12 }}>{error}</div>}

      {tab === "lead-lag" && (
        <div style={CARD}>
          <div style={LABEL}>Lead-Lag Analysis — SPY vs BTC</div>
          {leadLag ? (
            <div>
              <div style={{ display: "flex", gap: 24, marginTop: 12, marginBottom: 16 }}>
                <div><div style={LABEL}>Optimal Lag</div><div style={{ fontSize: 18, fontWeight: 700, color: "#ffa657" }}>{leadLag.optimal_lag} periods</div></div>
                <div><div style={LABEL}>Optimal Correlation</div><div style={{ fontSize: 18, fontWeight: 700, color: "#58a6ff" }}>{leadLag.optimal_correlation?.toFixed(4)}</div></div>
                <div><div style={LABEL}>Leader</div><div style={{ fontSize: 18, fontWeight: 700, color: "#3fb950" }}>{leadLag.leader === "a" ? "SPY" : leadLag.leader === "b" ? "BTC" : "Neither"}</div></div>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginTop: 8 }}>
                {Object.entries(leadLag.correlations_by_lag || {}).sort((a, b) => parseInt(a[0]) - parseInt(b[0])).map(([lag, corr]) => {
                  const h = Math.abs(corr) * 80;
                  const isOpt = parseInt(lag) === leadLag.optimal_lag;
                  return (
                    <div key={lag} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                      <div style={{ fontSize: 10, color: isOpt ? "#ffa657" : "#8b949e" }}>{corr.toFixed(2)}</div>
                      <div style={{ width: 32, height: h, background: isOpt ? "#ffa657" : corr >= 0 ? "#58a6ff" : "#f85149", borderRadius: "4px 4px 0 0" }} />
                      <div style={{ fontSize: 10, color: "#8b949e" }}>L{lag}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : <div style={{ fontSize: 12, color: "#8b949e", marginTop: 8 }}>Click "Run Analysis"</div>}
        </div>
      )}

      {tab === "spillover" && spillover && (
        <div style={CARD}>
          <div style={LABEL}>Return Spillover Matrix (Lag {spillover.lag})</div>
          <div style={{ overflowX: "auto", marginTop: 12 }}>
            <table style={{ borderCollapse: "collapse" }}>
              <thead><tr>
                <th style={{ padding: "6px 12px", fontSize: 11, color: "#8b949e" }}></th>
                {spillover.tickers.map(t => <th key={t} style={{ padding: "6px 10px", fontSize: 12, color: "#58a6ff", textAlign: "center" }}>{t}</th>)}
              </tr></thead>
              <tbody>
                {spillover.tickers.map((rt, i) => (
                  <tr key={rt}>
                    <td style={{ padding: "8px 12px", fontWeight: 700, color: "#58a6ff", fontSize: 12 }}>{rt}</td>
                    {spillover.matrix[i].map((v, j) => (
                      <td key={j} style={{ padding: "8px 10px", textAlign: "center", fontSize: 12, color: i === j ? "#21262d" : v > 0.5 ? "#f85149" : v > 0.3 ? "#e3b341" : "#8b949e", background: i === j ? "#161b22" : `rgba(88,166,255,${v * 0.3})`, border: "1px solid #21262d" }}>{i === j ? "—" : v.toFixed(2)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "sync" && (
        <div style={CARD}>
          <div style={LABEL}>Market Synchronization</div>
          {sync ? (
            <div style={{ textAlign: "center", padding: 32 }}>
              <div style={{ fontSize: 48, fontWeight: 700, color: sync.synchronization_score > 0.7 ? "#f85149" : sync.synchronization_score > 0.5 ? "#e3b341" : "#3fb950" }}>{(sync.synchronization_score * 100).toFixed(1)}%</div>
              <div style={{ fontSize: 14, color: "#8b949e", marginTop: 8 }}>Synchronization Score</div>
              <div style={{ fontSize: 12, color: "#8b949e", marginTop: 4 }}>Avg Pairwise Correlation: <span style={{ color: "#58a6ff" }}>{sync.avg_pairwise_correlation?.toFixed(4)}</span></div>
            </div>
          ) : <div style={{ fontSize: 12, color: "#8b949e" }}>Click "Run Analysis"</div>}
        </div>
      )}

      {tab === "graph" && depGraph && (
        <div style={CARD}>
          <div style={LABEL}>Dependency Graph (|ρ| ≥ {depGraph.threshold})</div>
          <div style={{ marginTop: 12 }}>
            <div style={{ marginBottom: 12 }}>
              <span style={{ fontSize: 12, color: "#8b949e" }}>Nodes: <span style={{ color: "#ffa657" }}>{depGraph.n_nodes}</span> | Edges: <span style={{ color: "#ffa657" }}>{depGraph.n_edges}</span></span>
            </div>
            {depGraph.nodes.map(n => (
              <div key={n.ticker} style={{ display: "flex", alignItems: "center", gap: 12, padding: "6px 0", borderBottom: "1px solid #21262d" }}>
                <div style={{ width: 48, fontWeight: 700, color: "#58a6ff", fontSize: 12 }}>{n.ticker}</div>
                <div style={{ flex: 1, height: 6, background: "#161b22", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${(n.degree / (depGraph.n_nodes - 1)) * 100}%`, background: "#58a6ff", borderRadius: 3 }} />
                </div>
                <div style={{ fontSize: 11, color: "#8b949e", width: 80 }}>Degree: {n.degree}</div>
              </div>
            ))}
            <div style={{ marginTop: 16 }}>
              <div style={LABEL}>Edges</div>
              {depGraph.edges.map(e => (
                <div key={`${e.source}-${e.target}`} style={{ fontSize: 11, color: "#8b949e", padding: "3px 0" }}>
                  {e.source} → {e.target}: <span style={{ color: e.weight >= 0 ? "#3fb950" : "#f85149", fontWeight: 700 }}>{e.weight.toFixed(4)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
