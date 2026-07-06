import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  row: { display: "flex", gap: 12, marginBottom: 16 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, flex: 1 },
  btn: { background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, cursor: "pointer" },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#58a6ff", marginBottom: 12 },
  chart: { position: "relative", height: 220, background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, overflow: "hidden" },
  err: { color: "#ff7b72", fontSize: 12 },
  grid3: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 },
  card: { background: "#161b22", borderRadius: 6, padding: "10px 14px" },
  cardLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase" },
  cardVal: { fontSize: 14, fontWeight: 700, color: "#f0f6fc", marginTop: 2 },
};

function SparkLine({ data, color = "#58a6ff", height = 200 }) {
  if (!data || data.length < 2) return <div style={{ color: "#8b949e", padding: 20, fontSize: 12 }}>No data</div>;
  const vals = data.map(d => d.equity ?? d.value ?? 0);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const W = 800; const H = height;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * W},${H - ((v - min) / range) * (H - 20) - 10}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" />
      <text x="4" y={H - 4} fontSize="10" fill="#8b949e">{min.toFixed(0)}</text>
      <text x="4" y="14" fontSize="10" fill="#8b949e">{max.toFixed(0)}</text>
    </svg>
  );
}

export default function M19EquityCurveViewer() {
  const [btId, setBtId] = useState("");
  const [curve, setCurve] = useState([]);
  const [drawdown, setDrawdown] = useState([]);
  const [monthly, setMonthly] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const load = async () => {
    if (!btId.trim()) return;
    setLoading(true); setErr("");
    try {
      const [ec, dd, mr] = await Promise.all([
        fetch(`/quant/backtest/${btId}/equity-curve`).then(r => r.ok ? r.json() : []),
        fetch(`/quant/backtest/${btId}/drawdown`).then(r => r.ok ? r.json() : []),
        fetch(`/quant/backtest/${btId}/monthly-returns`).then(r => r.ok ? r.json() : null),
      ]);
      setCurve(Array.isArray(ec) ? ec : []);
      setDrawdown(Array.isArray(dd) ? dd : []);
      setMonthly(mr);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const finalEq = curve.length ? curve[curve.length - 1].equity : null;
  const initEq = curve.length ? curve[0].equity : null;
  const totalRet = finalEq && initEq ? ((finalEq - initEq) / initEq * 100).toFixed(2) : "—";
  const maxDD = drawdown.length ? (Math.min(...drawdown.map(d => d.drawdown ?? 0)) * 100).toFixed(2) : "—";

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Equity Curve Viewer</div>
      <div style={S.sub}>Visualise P&L, drawdown, and monthly returns for any completed backtest.</div>

      <div style={S.row}>
        <input style={S.input} placeholder="Backtest ID (UUID)…" value={btId} onChange={e => setBtId(e.target.value)} />
        <button style={S.btn} onClick={load} disabled={loading}>{loading ? "Loading…" : "Load"}</button>
      </div>
      {err && <div style={S.err}>{err}</div>}

      {curve.length > 0 && (
        <>
          <div style={S.grid3}>
            {[
              ["Total Return", `${totalRet}%`],
              ["Max Drawdown", `${maxDD}%`],
              ["Data Points", curve.length],
            ].map(([label, val]) => (
              <div key={label} style={S.card}>
                <div style={S.cardLabel}>{label}</div>
                <div style={S.cardVal}>{val}</div>
              </div>
            ))}
          </div>

          <div style={S.section}>
            <div style={S.sHdr}>Equity Curve</div>
            <div style={S.chart}><SparkLine data={curve} color="#58a6ff" /></div>
          </div>

          <div style={S.section}>
            <div style={S.sHdr}>Drawdown</div>
            <div style={S.chart}><SparkLine data={drawdown.map(d => ({ equity: d.drawdown ?? 0 }))} color="#ff7b72" /></div>
          </div>

          {monthly?.monthly_returns && (
            <div style={S.section}>
              <div style={S.sHdr}>Monthly Returns</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {Object.entries(monthly.monthly_returns).map(([month, ret]) => (
                  <div key={month} style={{ background: ret >= 0 ? "#1b4721" : "#3d1a1a", borderRadius: 4, padding: "4px 8px", fontSize: 11 }}>
                    <span style={{ color: "#8b949e" }}>{month} </span>
                    <span style={{ color: ret >= 0 ? "#3fb950" : "#ff7b72", fontWeight: 700 }}>{(ret * 100).toFixed(2)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
