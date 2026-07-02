import { useState } from "react";
import { multiAssetApi } from "../api/multiAssetApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };

const FACTORS = ["market","size","value","momentum","quality","low_volatility","growth","profitability","investment","dividend_yield"];
const FACTOR_COLORS = { market:"#58a6ff", size:"#3fb950", value:"#e3b341", momentum:"#f85149", quality:"#a371f7", low_volatility:"#ffa657", growth:"#79c0ff", profitability:"#56d364", investment:"#d2a8ff", dividend_yield:"#f9e2af" };

function FactorBar({ label, value, color }) {
  const maxAbs = 2;
  const pct = Math.min(Math.abs(value) / maxAbs, 1) * 100;
  const isNeg = value < 0;
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
        <span style={{ fontSize: 11, color: "#c9d1d9" }}>{label.replace(/_/g, " ").toUpperCase()}</span>
        <span style={{ fontSize: 12, fontWeight: 700, color }}>{value.toFixed(3)}</span>
      </div>
      <div style={{ height: 6, background: "#161b22", borderRadius: 3, overflow: "hidden", position: "relative" }}>
        <div style={{
          position: "absolute", height: "100%", borderRadius: 3,
          width: `${pct / 2}%`,
          background: color,
          left: isNeg ? `${50 - pct / 2}%` : "50%",
        }} />
        <div style={{ position: "absolute", left: "50%", top: 0, width: 1, height: "100%", background: "#30363d" }} />
      </div>
    </div>
  );
}

const DEMO_EXPOSURES = {
  ticker: "NVDA",
  factor_scores: { market: 1.42, size: -1.1, value: -0.85, momentum: 1.9, quality: 0.6, low_volatility: -1.3, growth: 1.7, profitability: 0.9, investment: -0.4, dividend_yield: -0.7 }
};

export default function FactorDashboard() {
  const [exposures, setExposures] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [ticker, setTicker] = useState("NVDA");

  const compute = async () => {
    setLoading(true); setError(null);
    try {
      const res = await multiAssetApi.factorExposures({ ...DEMO_EXPOSURES, ticker });
      setExposures(res.data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 900 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — FACTOR ENGINE</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Factor Dashboard</h1>

      <div style={{ ...CARD, marginBottom: 20, display: "flex", gap: 16, alignItems: "flex-end" }}>
        <div>
          <div style={LABEL}>Ticker</div>
          <input value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", fontFamily: "monospace", fontSize: 12, padding: "6px 10px", width: 100 }} />
        </div>
        <button onClick={compute} disabled={loading} style={{ padding: "8px 20px", background: "#ffa65733", border: "1px solid #ffa657", borderRadius: 6, color: "#ffa657", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
          {loading ? "Loading…" : "Load Exposures"}
        </button>
      </div>

      {error && <div style={{ color: "#f85149", marginBottom: 16, fontSize: 12 }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={CARD}>
          <div style={LABEL}>Factor Exposures — {exposures?.ticker ?? ticker}</div>
          <div style={{ marginTop: 12 }}>
            {FACTORS.map(f => {
              const val = exposures ? (exposures.exposures[f] ?? 0) : (DEMO_EXPOSURES.factor_scores[f] ?? 0);
              return <FactorBar key={f} label={f} value={val} color={FACTOR_COLORS[f]} />;
            })}
          </div>
          {exposures && <div style={{ marginTop: 12, fontSize: 11, color: "#8b949e" }}>Dominant factor: <span style={{ color: "#ffa657", fontWeight: 700 }}>{exposures.dominant_factor?.replace(/_/g, " ").toUpperCase()}</span></div>}
        </div>

        <div style={CARD}>
          <div style={LABEL}>10 Classic Factors</div>
          <div style={{ marginTop: 12 }}>
            {[
              ["Market", "CAPM beta against broad market"],
              ["Size", "SMB — small minus big market cap"],
              ["Value", "HML — high minus low book/market"],
              ["Momentum", "12-1 month return continuation"],
              ["Quality", "ROE, low debt, earnings stability"],
              ["Low Volatility", "Low-beta, low realised vol"],
              ["Growth", "Revenue + earnings growth rate"],
              ["Profitability", "Gross profit / total assets"],
              ["Investment", "CMA — conservative minus aggressive"],
              ["Dividend Yield", "High-yield vs low-yield spread"],
            ].map(([name, desc]) => (
              <div key={name} style={{ display: "flex", gap: 10, padding: "5px 0", borderBottom: "1px solid #21262d" }}>
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: FACTOR_COLORS[name.toLowerCase().replace(/ /g, "_")] || "#58a6ff", marginTop: 2, flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#c9d1d9" }}>{name}</div>
                  <div style={{ fontSize: 11, color: "#8b949e" }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
