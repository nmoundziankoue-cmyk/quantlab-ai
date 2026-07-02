import { useState } from "react";
import { multiAssetApi } from "../api/multiAssetApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", fontFamily: "monospace", fontSize: 12, padding: "6px 10px", width: "100%" };

const YIELD_CURVE_DATA = [
  { maturity_years: 0.25, yield_rate: 0.052, label: "3M" },
  { maturity_years: 0.5,  yield_rate: 0.051, label: "6M" },
  { maturity_years: 1.0,  yield_rate: 0.050, label: "1Y" },
  { maturity_years: 2.0,  yield_rate: 0.048, label: "2Y" },
  { maturity_years: 5.0,  yield_rate: 0.045, label: "5Y" },
  { maturity_years: 10.0, yield_rate: 0.043, label: "10Y" },
  { maturity_years: 30.0, yield_rate: 0.044, label: "30Y" },
];

function YieldCurveSVG({ points }) {
  if (!points?.length) return null;
  const W = 420, H = 140, pad = 36;
  const maxT = Math.max(...points.map(p => p.maturity_years));
  const minY = Math.min(...points.map(p => p.yield_rate)) * 0.98;
  const maxY = Math.max(...points.map(p => p.yield_rate)) * 1.02;
  const sx = t => pad + (t / maxT) * (W - 2 * pad);
  const sy = y => H - pad - ((y - minY) / (maxY - minY)) * (H - 2 * pad);
  const d = points.map((p, i) => `${i === 0 ? "M" : "L"} ${sx(p.maturity_years).toFixed(1)} ${sy(p.yield_rate).toFixed(1)}`).join(" ");
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      <path d={d} stroke="#3fb950" strokeWidth={2} fill="none" />
      {points.map(p => <circle key={p.label} cx={sx(p.maturity_years)} cy={sy(p.yield_rate)} r={3} fill="#3fb950" />)}
      {points.map(p => <text key={p.label + "l"} x={sx(p.maturity_years)} y={H - 6} textAnchor="middle" fill="#8b949e" fontSize={9}>{p.label}</text>)}
      <text x={pad - 4} y={sy(maxY) + 4} textAnchor="end" fill="#8b949e" fontSize={9}>{(maxY * 100).toFixed(1)}%</text>
      <text x={pad - 4} y={sy(minY) + 4} textAnchor="end" fill="#8b949e" fontSize={9}>{(minY * 100).toFixed(1)}%</text>
    </svg>
  );
}

export default function BondAnalytics() {
  const [bond, setBond] = useState({ isin: "US912828T554", ticker: "UST10Y", face_value: 1000, coupon_rate: 0.0425, coupon_frequency: 2, maturity_years: 10, bond_type: "government", credit_rating: "AAA", callable: false });
  const [marketPrice, setMarketPrice] = useState(985);
  const [rfRate, setRfRate] = useState(0.0);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyze = async () => {
    setLoading(true); setError(null);
    try {
      const res = await multiAssetApi.bondAnalyze({ bond, market_price: parseFloat(marketPrice), risk_free_rate: parseFloat(rfRate), accrual_fraction: 0 });
      setResult(res.data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1100 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — BOND ANALYTICS ENGINE</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Bond Analytics</h1>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div style={CARD}>
          <div style={LABEL}>Bond Specification</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 8 }}>
            {[["ISIN", "isin", "text"], ["Coupon Rate", "coupon_rate", "number"], ["Face Value", "face_value", "number"], ["Maturity (years)", "maturity_years", "number"], ["Coupon Freq/Year", "coupon_frequency", "number"], ["Credit Rating", "credit_rating", "text"]].map(([label, key, type]) => (
              <div key={key}>
                <div style={{ ...LABEL, marginBottom: 2 }}>{label}</div>
                <input type={type} value={bond[key]} onChange={e => setBond(b => ({ ...b, [key]: type === "number" ? parseFloat(e.target.value) || 0 : e.target.value }))} style={INPUT} />
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={LABEL}>Market Price</div>
              <input type="number" value={marketPrice} onChange={e => setMarketPrice(e.target.value)} style={INPUT} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={LABEL}>Risk-Free Rate</div>
              <input type="number" step="0.001" value={rfRate} onChange={e => setRfRate(e.target.value)} style={INPUT} />
            </div>
          </div>
          <button onClick={analyze} disabled={loading} style={{ marginTop: 12, padding: "8px 20px", background: "#3fb95033", border: "1px solid #3fb950", borderRadius: 6, color: "#3fb950", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
            {loading ? "Analysing…" : "Analyse Bond"}
          </button>
          {error && <div style={{ color: "#f85149", marginTop: 8, fontSize: 11 }}>{error}</div>}
        </div>

        <div style={CARD}>
          {result ? (
            <>
              <div style={LABEL}>Analytics Results</div>
              {[["YTM", `${(result.ytm * 100).toFixed(3)}%`], ["Macaulay Duration", `${result.duration?.toFixed(3)} yrs`], ["Modified Duration", `${result.modified_duration?.toFixed(3)}`], ["Convexity", `${result.convexity?.toFixed(3)}`], ["DV01", `$${result.dv01?.toFixed(4)}`], ["Spread", `${(result.spread * 100).toFixed(3)}%`], ["Dirty Price", `${result.dirty_price?.toFixed(3)}`], ["Yield Bucket", result.yield_bucket], ["Credit Bucket", result.credit_bucket], ["Maturity Bucket", result.maturity_bucket]].map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #21262d", fontSize: 12 }}>
                  <span style={{ color: "#8b949e" }}>{k}</span>
                  <span style={{ color: "#3fb950", fontWeight: 600 }}>{v}</span>
                </div>
              ))}
            </>
          ) : <div style={{ fontSize: 12, color: "#8b949e" }}>Click "Analyse Bond" to view results</div>}
        </div>
      </div>

      <div style={CARD}>
        <div style={LABEL}>US Treasury Yield Curve</div>
        <YieldCurveSVG points={YIELD_CURVE_DATA} />
        <div style={{ display: "flex", gap: 16, marginTop: 8, flexWrap: "wrap" }}>
          {YIELD_CURVE_DATA.map(p => (
            <div key={p.label} style={{ fontSize: 11 }}>
              <span style={{ color: "#8b949e" }}>{p.label}: </span>
              <span style={{ color: "#3fb950", fontWeight: 700 }}>{(p.yield_rate * 100).toFixed(2)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
