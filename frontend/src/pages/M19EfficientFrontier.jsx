import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#d2a8ff", marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, cursor: "pointer", fontWeight: 600, marginTop: 8 },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  plot: { position: "relative", background: "#0a0d12", border: "1px solid #30363d", borderRadius: 8, padding: 12, height: 320, overflow: "hidden" },
  point: (x, y, r, c, isSpecial) => ({
    position: "absolute",
    left: `${x}%`, top: `${y}%`,
    width: isSpecial ? 10 : 6, height: isSpecial ? 10 : 6,
    borderRadius: "50%",
    background: c,
    transform: "translate(-50%, -50%)",
    border: isSpecial ? "2px solid #fff" : "none",
    cursor: "pointer",
  }),
  tooltip: { position: "absolute", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", fontSize: 10, pointerEvents: "none", zIndex: 10, color: "#f0f6fc", whiteSpace: "nowrap" },
  legend: { display: "flex", gap: 12, flexWrap: "wrap", marginTop: 8, fontSize: 11 },
  dot: (c) => ({ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: c, marginRight: 4 }),
};

export default function M19EfficientFrontier() {
  const [nPoints, setNPoints] = useState("20");
  const [frontier, setFrontier] = useState([]);
  const [mvPoint, setMvPoint] = useState(null);
  const [msPoint, setMsPoint] = useState(null);
  const [hovered, setHovered] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const TICKERS = ["AAPL", "MSFT", "JPM", "AMZN"];
  const ER = { AAPL: 0.15, MSFT: 0.12, JPM: 0.09, AMZN: 0.14 };
  const COV = {
    AAPL: { AAPL: 0.040, MSFT: 0.015, JPM: 0.005, AMZN: 0.020 },
    MSFT: { AAPL: 0.015, MSFT: 0.035, JPM: 0.007, AMZN: 0.018 },
    JPM: { AAPL: 0.005, MSFT: 0.007, JPM: 0.025, AMZN: 0.005 },
    AMZN: { AAPL: 0.020, MSFT: 0.018, JPM: 0.005, AMZN: 0.042 },
  };

  const compute = async () => {
    setLoading(true); setErr("");
    try {
      const r = await fetch("/quant/optimize/frontier", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tickers: TICKERS, expected_returns: ER, covariance_matrix: COV, n_points: parseInt(nPoints) }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(JSON.stringify(d)); return; }
      setFrontier(d.points || []);
      setMvPoint(d.min_variance_point);
      setMsPoint(d.max_sharpe_point);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const allPoints = frontier;
  const vols = allPoints.map(p => p.volatility);
  const rets = allPoints.map(p => p.expected_return);
  const minVol = Math.min(...vols, 0.05);
  const maxVol = Math.max(...vols, 0.30);
  const minRet = Math.min(...rets, 0.05);
  const maxRet = Math.max(...rets, 0.20);
  const volRange = maxVol - minVol || 0.01;
  const retRange = maxRet - minRet || 0.01;
  const xPct = (v) => ((v - minVol) / volRange) * 90 + 5;
  const yPct = (r) => 95 - ((r - minRet) / retRange) * 90;

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Efficient Frontier</div>
      <div style={S.sub}>Visualise the risk-return tradeoff across optimal portfolio combinations.</div>

      <div style={S.section}>
        <div style={S.sHdr}>Parameters (AAPL · MSFT · JPM · AMZN)</div>
        <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <label style={S.label}>Number of Frontier Points</label>
            <input style={S.input} value={nPoints} onChange={e => setNPoints(e.target.value)} type="number" min="3" max="50" />
          </div>
          <button style={S.btn} onClick={compute} disabled={loading}>{loading ? "Computing…" : "Compute Frontier"}</button>
        </div>
        {err && <div style={S.err}>{err}</div>}
      </div>

      {frontier.length > 0 && (
        <div style={S.section}>
          <div style={S.sHdr}>Risk-Return Plot</div>
          <div style={S.plot}
            onMouseMove={e => { const rect = e.currentTarget.getBoundingClientRect(); setMousePos({ x: e.clientX - rect.left + 10, y: e.clientY - rect.top + 10 }); }}
            onMouseLeave={() => setHovered(null)}>
            {/* Axis labels */}
            <div style={{ position: "absolute", bottom: 2, left: "50%", transform: "translateX(-50%)", fontSize: 10, color: "#8b949e" }}>Volatility →</div>
            <div style={{ position: "absolute", left: 2, top: "40%", fontSize: 10, color: "#8b949e", writingMode: "vertical-rl", transform: "rotate(180deg)" }}>Return →</div>
            {/* Frontier points */}
            {frontier.map((p, i) => {
              const isMV = mvPoint && Math.abs(p.volatility - mvPoint.volatility) < 0.001;
              const isMS = msPoint && Math.abs(p.volatility - msPoint.volatility) < 0.001;
              return (
                <div key={i}
                  style={S.point(xPct(p.volatility), yPct(p.expected_return), 6, isMV ? "#3fb950" : isMS ? "#ffa657" : "#58a6ff", isMV || isMS)}
                  onMouseEnter={() => setHovered(p)}
                  onMouseLeave={() => setHovered(null)} />
              );
            })}
            {hovered && (
              <div style={{ ...S.tooltip, left: mousePos.x, top: mousePos.y }}>
                Ret: {(hovered.expected_return * 100).toFixed(2)}% | Vol: {(hovered.volatility * 100).toFixed(2)}% | Sharpe: {hovered.sharpe_ratio?.toFixed(3)}
              </div>
            )}
          </div>
          <div style={S.legend}>
            <div><span style={S.dot("#58a6ff")} />Frontier point</div>
            <div><span style={S.dot("#3fb950")} />Min Variance</div>
            <div><span style={S.dot("#ffa657")} />Max Sharpe</div>
          </div>
          <div style={{ marginTop: 8, fontSize: 11, color: "#8b949e" }}>
            {mvPoint && `Min-Vol: ${(mvPoint.volatility * 100).toFixed(2)}% vol, ${(mvPoint.expected_return * 100).toFixed(2)}% ret`}
            {msPoint && ` | Max-Sharpe: ${msPoint.sharpe_ratio?.toFixed(3)} Sharpe`}
          </div>
        </div>
      )}
    </div>
  );
}
