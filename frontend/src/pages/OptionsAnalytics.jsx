import { useState } from "react";
import { multiAssetApi } from "../api/multiAssetApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", fontFamily: "monospace", fontSize: 12, padding: "6px 10px", width: "100%" };

const GREEK_COLORS = { delta: "#58a6ff", gamma: "#3fb950", theta: "#f85149", vega: "#e3b341", rho: "#a371f7" };

function GreekGauge({ label, value, color, format }) {
  return (
    <div style={{ textAlign: "center", padding: 12 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{format ? format(value) : value?.toFixed(4) ?? "—"}</div>
      <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>{label}</div>
    </div>
  );
}

export default function OptionsAnalytics() {
  const [params, setParams] = useState({ S: 450, K: 450, T: 0.25, r: 0.05, sigma: 0.25, option_type: "call" });
  const [greeks, setGreeks] = useState(null);
  const [price, setPrice] = useState(null);
  const [iv, setIv] = useState(null);
  const [marketPrice, setMarketPrice] = useState(18.5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("pricer");

  const set = (k, v) => setParams(p => ({ ...p, [k]: parseFloat(v) || (k === "option_type" ? v : 0) }));

  const compute = async () => {
    setLoading(true); setError(null);
    try {
      const [g, p] = await Promise.all([
        multiAssetApi.optionGreeks(params),
        multiAssetApi.optionPrice(params),
      ]);
      setGreeks(g.data);
      setPrice(p.data.price);
      if (marketPrice) {
        const ivRes = await multiAssetApi.impliedVol({ ...params, market_price: parseFloat(marketPrice) });
        setIv(ivRes.data.implied_volatility);
      }
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1000 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — OPTIONS ANALYTICS ENGINE</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Options Analytics</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {["pricer", "greeks", "iv"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: "6px 16px", borderRadius: 6, border: "1px solid", borderColor: tab === t ? "#ffa657" : "#21262d", background: tab === t ? "#ffa65722" : "transparent", color: tab === t ? "#ffa657" : "#8b949e", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>{t.toUpperCase()}</button>
        ))}
      </div>

      <div style={{ ...CARD, marginBottom: 20 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 12 }}>
          {[["Spot (S)", "S"], ["Strike (K)", "K"], ["Expiry Years (T)", "T"], ["Risk-Free (r)", "r"], ["Volatility (σ)", "sigma"], ["Market Price", null]].map(([label, key]) => (
            <div key={label}>
              <div style={LABEL}>{label}</div>
              <input type="number" step="0.01"
                value={key ? params[key] : marketPrice}
                onChange={e => key ? set(key, e.target.value) : setMarketPrice(e.target.value)}
                style={INPUT} />
            </div>
          ))}
          <div>
            <div style={LABEL}>Type</div>
            <select value={params.option_type} onChange={e => setParams(p => ({ ...p, option_type: e.target.value }))} style={{ ...INPUT, appearance: "none" }}>
              <option value="call">Call</option>
              <option value="put">Put</option>
            </select>
          </div>
        </div>
        <button onClick={compute} disabled={loading} style={{ padding: "8px 20px", background: "#e3b34133", border: "1px solid #e3b341", borderRadius: 6, color: "#e3b341", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
          {loading ? "Computing…" : "Compute"}
        </button>
        {error && <div style={{ color: "#f85149", marginTop: 8, fontSize: 11 }}>{error}</div>}
      </div>

      {tab === "pricer" && price != null && (
        <div style={{ ...CARD, textAlign: "center" }}>
          <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>THEORETICAL PRICE</div>
          <div style={{ fontSize: 36, fontWeight: 700, color: "#e3b341" }}>${price.toFixed(4)}</div>
          {iv != null && <div style={{ fontSize: 14, color: "#8b949e", marginTop: 8 }}>Implied Volatility: <span style={{ color: "#ffa657", fontWeight: 700 }}>{(iv * 100).toFixed(2)}%</span></div>}
        </div>
      )}

      {tab === "greeks" && greeks && (
        <div style={CARD}>
          <div style={LABEL}>Black-Scholes Greeks</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", marginTop: 12 }}>
            <GreekGauge label="Delta" value={greeks.delta} color={GREEK_COLORS.delta} />
            <GreekGauge label="Gamma" value={greeks.gamma} color={GREEK_COLORS.gamma} />
            <GreekGauge label="Theta (daily)" value={greeks.theta} color={GREEK_COLORS.theta} format={v => `$${v?.toFixed(4)}`} />
            <GreekGauge label="Vega (1% IV)" value={greeks.vega} color={GREEK_COLORS.vega} format={v => `$${v?.toFixed(4)}`} />
            <GreekGauge label="Rho (1% r)" value={greeks.rho} color={GREEK_COLORS.rho} format={v => `$${v?.toFixed(4)}`} />
          </div>
          <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <div style={LABEL}>Vanna</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#d2a8ff" }}>{greeks.vanna?.toFixed(6)}</div>
              <div style={{ fontSize: 11, color: "#8b949e" }}>∂²V / ∂S∂σ</div>
            </div>
            <div>
              <div style={LABEL}>Charm (daily)</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#79c0ff" }}>{greeks.charm?.toFixed(6)}</div>
              <div style={{ fontSize: 11, color: "#8b949e" }}>∂²V / ∂S∂t</div>
            </div>
          </div>
        </div>
      )}

      {tab === "iv" && (
        <div style={CARD}>
          <div style={LABEL}>Implied Volatility</div>
          {iv != null ? (
            <div style={{ textAlign: "center", padding: 24 }}>
              <div style={{ fontSize: 40, fontWeight: 700, color: "#ffa657" }}>{(iv * 100).toFixed(2)}%</div>
              <div style={{ fontSize: 12, color: "#8b949e", marginTop: 8 }}>Computed via bisection — pure Python, no scipy</div>
            </div>
          ) : <div style={{ fontSize: 12, color: "#8b949e", marginTop: 8 }}>Enter market price and click Compute</div>}
        </div>
      )}
    </div>
  );
}
