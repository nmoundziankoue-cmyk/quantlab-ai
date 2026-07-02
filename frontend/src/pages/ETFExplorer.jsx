import { useState } from "react";
import { multiAssetApi } from "../api/multiAssetApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };

const SPY_ETF = {
  ticker: "SPY", name: "SPDR S&P 500 ETF Trust", expense_ratio: 0.0009, aum_usd: 450000,
  benchmark: "S&P 500", inception_date: "1993-01-22", issuer: "State Street",
  holdings: [
    { ticker: "AAPL", name: "Apple Inc.", weight: 0.072, sector: "Information Technology", country: "US", market_cap_bucket: "large", asset_type: "equity" },
    { ticker: "MSFT", name: "Microsoft Corp.", weight: 0.068, sector: "Information Technology", country: "US", market_cap_bucket: "large", asset_type: "equity" },
    { ticker: "AMZN", name: "Amazon.com Inc.", weight: 0.038, sector: "Consumer Discretionary", country: "US", market_cap_bucket: "large", asset_type: "equity" },
    { ticker: "NVDA", name: "NVIDIA Corp.", weight: 0.035, sector: "Information Technology", country: "US", market_cap_bucket: "large", asset_type: "equity" },
    { ticker: "GOOGL", name: "Alphabet Inc.", weight: 0.021, sector: "Communication Services", country: "US", market_cap_bucket: "large", asset_type: "equity" },
    { ticker: "JPM", name: "JPMorgan Chase", weight: 0.013, sector: "Financials", country: "US", market_cap_bucket: "large", asset_type: "equity" },
    { ticker: "XOM", name: "Exxon Mobil", weight: 0.012, sector: "Energy", country: "US", market_cap_bucket: "large", asset_type: "equity" },
    { ticker: "UNH", name: "UnitedHealth Group", weight: 0.011, sector: "Health Care", country: "US", market_cap_bucket: "large", asset_type: "equity" },
  ],
};

const SECTOR_COLORS = { "Information Technology": "#58a6ff", "Consumer Discretionary": "#e3b341", "Communication Services": "#3fb950", Financials: "#f85149", Energy: "#ffa657", "Health Care": "#a371f7", Others: "#8b949e" };

function PieChart({ data, title }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  let cumAngle = -Math.PI / 2;
  const cx = 80, cy = 80, r = 60;
  const paths = Object.entries(data).map(([key, val]) => {
    const angle = (val / total) * 2 * Math.PI;
    const x1 = cx + r * Math.cos(cumAngle);
    const y1 = cy + r * Math.sin(cumAngle);
    cumAngle += angle;
    const x2 = cx + r * Math.cos(cumAngle);
    const y2 = cy + r * Math.sin(cumAngle);
    const large = angle > Math.PI ? 1 : 0;
    const color = SECTOR_COLORS[key] || "#8b949e";
    return { key, path: `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`, color, pct: (val / total * 100).toFixed(1) };
  });
  return (
    <div>
      <div style={LABEL}>{title}</div>
      <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
        <svg width={160} height={160} viewBox="0 0 160 160">
          {paths.map(({ key, path, color }) => <path key={key} d={path} fill={color} stroke="#0d1117" strokeWidth={2} />)}
        </svg>
        <div>
          {paths.map(({ key, color, pct }) => (
            <div key={key} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
              <div style={{ width: 10, height: 10, background: color, borderRadius: 2, flexShrink: 0 }} />
              <span style={{ fontSize: 11, color: "#c9d1d9" }}>{key}: <b style={{ color }}>{pct}%</b></span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function ETFExplorer() {
  const [tab, setTab] = useState("summary");
  const [summary, setSummary] = useState(null);
  const [sectorExp, setSectorExp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const [s, se] = await Promise.all([
        multiAssetApi.etfSummary(SPY_ETF),
        multiAssetApi.etfSectorExposure(SPY_ETF),
      ]);
      setSummary(s.data);
      setSectorExp(se.data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1100 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — ETF INTELLIGENCE</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>ETF Explorer</h1>

      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        {["summary", "holdings", "exposure"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: "6px 16px", borderRadius: 6, border: "1px solid", borderColor: tab === t ? "#ffa657" : "#21262d", background: tab === t ? "#ffa65722" : "transparent", color: tab === t ? "#ffa657" : "#8b949e", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>{t.toUpperCase()}</button>
        ))}
        <button onClick={load} disabled={loading} style={{ marginLeft: "auto", padding: "6px 16px", background: "#ffa65733", border: "1px solid #ffa657", borderRadius: 6, color: "#ffa657", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
          {loading ? "Loading…" : "Analyse SPY"}
        </button>
      </div>

      {error && <div style={{ color: "#f85149", marginBottom: 16, fontSize: 12 }}>{error}</div>}

      {tab === "summary" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={CARD}>
            <div style={LABEL}>Fund Basics</div>
            {[["Ticker", SPY_ETF.ticker], ["Name", SPY_ETF.name], ["AUM", `$${(SPY_ETF.aum_usd / 1000).toFixed(0)}B`], ["Expense Ratio", `${(SPY_ETF.expense_ratio * 100).toFixed(2)}%`], ["Benchmark", SPY_ETF.benchmark], ["Issuer", SPY_ETF.issuer], ["Inception", SPY_ETF.inception_date]].map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #21262d", fontSize: 12 }}>
                <span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: "#f0f6fc", fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>
          <div style={CARD}>
            <div style={LABEL}>Computed Metrics</div>
            {summary ? [["Holdings", summary.n_holdings], ["HHI", summary.hhi?.toFixed(4)], ["Effective N", summary.effective_n?.toFixed(1)], ["Top Sector", summary.top_sector], ["Sector Concentration", `${(summary.sector_concentration * 100)?.toFixed(1)}%`]].map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #21262d", fontSize: 12 }}>
                <span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: "#ffa657", fontWeight: 600 }}>{v ?? "—"}</span>
              </div>
            )) : <div style={{ fontSize: 12, color: "#8b949e", marginTop: 8 }}>Click "Analyse SPY" to load metrics</div>}
          </div>
        </div>
      )}

      {tab === "holdings" && (
        <div style={CARD}>
          <div style={LABEL}>Top Holdings</div>
          <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
            <thead><tr>{["Ticker", "Name", "Weight", "Sector"].map(h => <th key={h} style={{ textAlign: "left", padding: "6px 8px", fontSize: 11, color: "#8b949e", borderBottom: "1px solid #21262d" }}>{h}</th>)}</tr></thead>
            <tbody>
              {SPY_ETF.holdings.map(h => (
                <tr key={h.ticker}>
                  <td style={{ padding: "8px", fontWeight: 700, color: "#58a6ff", fontSize: 12 }}>{h.ticker}</td>
                  <td style={{ padding: "8px", fontSize: 12, color: "#c9d1d9" }}>{h.name}</td>
                  <td style={{ padding: "8px", fontSize: 12, color: "#3fb950" }}>{(h.weight * 100).toFixed(2)}%</td>
                  <td style={{ padding: "8px", fontSize: 11, color: "#8b949e" }}>{h.sector}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "exposure" && sectorExp && (
        <PieChart data={sectorExp.sectors || {}} title="Sector Exposure" />
      )}
      {tab === "exposure" && !sectorExp && (
        <div style={CARD}><div style={{ fontSize: 12, color: "#8b949e" }}>Click "Analyse SPY" to load sector exposure chart</div></div>
      )}
    </div>
  );
}
