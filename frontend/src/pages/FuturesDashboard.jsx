import { useState } from "react";
import { multiAssetApi } from "../api/multiAssetApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };

const WTI_CONTRACTS = [
  { ticker: "CL", contract_code: "CLN25", expiry_years: 0.083, price: 78.45, open_interest: 320000, volume: 98000, asset_class: "energy" },
  { ticker: "CL", contract_code: "CLQ25", expiry_years: 0.167, price: 78.90, open_interest: 185000, volume: 42000, asset_class: "energy" },
  { ticker: "CL", contract_code: "CLU25", expiry_years: 0.25,  price: 79.35, open_interest: 98000,  volume: 21000, asset_class: "energy" },
  { ticker: "CL", contract_code: "CLZ25", expiry_years: 0.5,   price: 79.80, open_interest: 75000,  volume: 15000, asset_class: "energy" },
  { ticker: "CL", contract_code: "CLH26", expiry_years: 0.75,  price: 80.20, open_interest: 52000,  volume: 9000,  asset_class: "energy" },
  { ticker: "CL", contract_code: "CLM26", expiry_years: 1.0,   price: 80.55, open_interest: 38000,  volume: 6000,  asset_class: "energy" },
];

function TermStructureSVG({ contracts }) {
  if (!contracts?.length) return null;
  const W = 520, H = 160, padL = 50, padR = 20, padT = 20, padB = 36;
  const prices = contracts.map(c => c.price);
  const minP = Math.min(...prices) * 0.999;
  const maxP = Math.max(...prices) * 1.001;
  const maxT = Math.max(...contracts.map(c => c.expiry_years));
  const sx = t => padL + (t / maxT) * (W - padL - padR);
  const sy = p => H - padB - ((p - minP) / (maxP - minP)) * (H - padT - padB);
  const pts = contracts.map(c => `${sx(c.expiry_years).toFixed(1)},${sy(c.price).toFixed(1)}`).join(" ");
  const slope = prices[prices.length - 1] - prices[0];
  const color = slope > 0 ? "#e3b341" : "#3fb950";
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      <polyline points={pts} stroke={color} strokeWidth={2} fill="none" />
      {contracts.map(c => <circle key={c.contract_code} cx={sx(c.expiry_years)} cy={sy(c.price)} r={4} fill={color} />)}
      {contracts.map(c => <text key={c.contract_code + "l"} x={sx(c.expiry_years)} y={H - 6} textAnchor="middle" fill="#8b949e" fontSize={9}>{c.contract_code.slice(-3)}</text>)}
      <text x={4} y={sy(maxP) + 4} fill="#8b949e" fontSize={9}>${maxP.toFixed(2)}</text>
      <text x={4} y={sy(minP) + 4} fill="#8b949e" fontSize={9}>${minP.toFixed(2)}</text>
    </svg>
  );
}

export default function FuturesDashboard() {
  const [termStructure, setTermStructure] = useState(null);
  const [rollYields, setRollYields] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("term-structure");

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const [ts, ry] = await Promise.all([
        multiAssetApi.termStructure({ contracts: WTI_CONTRACTS }),
        multiAssetApi.rollYield({ near: WTI_CONTRACTS[0], far: WTI_CONTRACTS[1] }),
      ]);
      setTermStructure(ts.data);
      setRollYields(ry.data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const structure = termStructure?.structure;

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1100 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — FUTURES ANALYTICS ENGINE</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Futures Dashboard</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20, alignItems: "center" }}>
        {["term-structure", "roll-yield", "oi"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid", borderColor: tab === t ? "#ffa657" : "#21262d", background: tab === t ? "#ffa65722" : "transparent", color: tab === t ? "#ffa657" : "#8b949e", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>{t.toUpperCase()}</button>
        ))}
        <button onClick={load} disabled={loading} style={{ marginLeft: "auto", padding: "6px 16px", background: "#ffa65733", border: "1px solid #ffa657", borderRadius: 6, color: "#ffa657", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
          {loading ? "Loading…" : "Analyse WTI Crude"}
        </button>
      </div>

      {error && <div style={{ color: "#f85149", marginBottom: 12, fontSize: 12 }}>{error}</div>}

      {tab === "term-structure" && (
        <div>
          <div style={{ ...CARD, marginBottom: 16 }}>
            <div style={{ display: "flex", gap: 24, alignItems: "center", marginBottom: 16 }}>
              <div>
                <div style={LABEL}>Market Structure</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: structure === "contango" ? "#e3b341" : structure === "backwardation" ? "#3fb950" : "#8b949e" }}>
                  {structure?.toUpperCase() ?? "—"}
                </div>
              </div>
              <div>
                <div style={LABEL}>Slope (%/yr)</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#ffa657" }}>{termStructure?.slope_percent?.toFixed(3) ?? "—"}%</div>
              </div>
              <div>
                <div style={LABEL}>Front / Back</div>
                <div style={{ fontSize: 14, color: "#c9d1d9" }}>${termStructure?.front_price?.toFixed(2) ?? "—"} → ${termStructure?.back_price?.toFixed(2) ?? "—"}</div>
              </div>
            </div>
            <TermStructureSVG contracts={WTI_CONTRACTS} />
          </div>
          <div style={CARD}>
            <div style={LABEL}>WTI Contracts</div>
            <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
              <thead><tr>{["Contract", "Expiry", "Price", "Open Interest", "Volume"].map(h => <th key={h} style={{ textAlign: "left", padding: "6px 8px", fontSize: 11, color: "#8b949e", borderBottom: "1px solid #21262d" }}>{h}</th>)}</tr></thead>
              <tbody>
                {WTI_CONTRACTS.map(c => (
                  <tr key={c.contract_code}>
                    <td style={{ padding: "8px", fontWeight: 700, color: "#ffa657", fontSize: 12 }}>{c.contract_code}</td>
                    <td style={{ padding: "8px", fontSize: 12, color: "#8b949e" }}>{(c.expiry_years * 12).toFixed(0)}M</td>
                    <td style={{ padding: "8px", fontSize: 12, color: "#f0f6fc" }}>${c.price.toFixed(2)}</td>
                    <td style={{ padding: "8px", fontSize: 12, color: "#8b949e" }}>{c.open_interest.toLocaleString()}</td>
                    <td style={{ padding: "8px", fontSize: 12, color: "#8b949e" }}>{c.volume.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "roll-yield" && (
        <div style={CARD}>
          <div style={LABEL}>Roll Yield (CLN25 → CLQ25)</div>
          {rollYields ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginTop: 12 }}>
              {[["Near Price", `$${rollYields.near_price?.toFixed(2)}`], ["Far Price", `$${rollYields.far_price?.toFixed(2)}`], ["Roll Yield (ann.)", `${(rollYields.roll_yield_annualised * 100)?.toFixed(3)}%`], ["Time Between", `${(rollYields.time_between * 30).toFixed(1)} days`], ["Structure", rollYields.structure?.toUpperCase()]].map(([k, v]) => (
                <div key={k} style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "#8b949e" }}>{k}</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: rollYields.structure === "backwardation" ? "#3fb950" : "#e3b341", marginTop: 4 }}>{v}</div>
                </div>
              ))}
            </div>
          ) : <div style={{ fontSize: 12, color: "#8b949e", marginTop: 8 }}>Click "Analyse WTI Crude" to load roll yield data</div>}
        </div>
      )}

      {tab === "oi" && (
        <div style={CARD}>
          <div style={LABEL}>Open Interest Distribution</div>
          <div style={{ marginTop: 12 }}>
            {WTI_CONTRACTS.map(c => {
              const total = WTI_CONTRACTS.reduce((s, x) => s + x.open_interest, 0);
              const pct = (c.open_interest / total) * 100;
              return (
                <div key={c.contract_code} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                  <div style={{ width: 56, fontSize: 11, fontWeight: 700, color: "#ffa657" }}>{c.contract_code.slice(-3)}</div>
                  <div style={{ flex: 1, height: 16, background: "#161b22", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${pct}%`, background: "#ffa657", borderRadius: 4 }} />
                  </div>
                  <div style={{ width: 80, fontSize: 11, color: "#8b949e", textAlign: "right" }}>{c.open_interest.toLocaleString()} ({pct.toFixed(1)}%)</div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
