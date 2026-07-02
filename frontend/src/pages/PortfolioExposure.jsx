import { useState } from "react";
import { multiAssetApi } from "../api/multiAssetApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };

const DEMO_PORTFOLIO = [
  { ticker: "AAPL", weight: 0.12, sector: "Information Technology", country: "US", currency: "USD", asset_class: "equity", market_cap_bucket: "large", beta: 1.25, duration: 0, factor_exposures: { momentum: 1.5, growth: 1.2, quality: 0.8 } },
  { ticker: "MSFT", weight: 0.10, sector: "Information Technology", country: "US", currency: "USD", asset_class: "equity", market_cap_bucket: "large", beta: 0.98, duration: 0, factor_exposures: { quality: 1.1, growth: 0.9 } },
  { ticker: "JPM",  weight: 0.08, sector: "Financials", country: "US", currency: "USD", asset_class: "equity", market_cap_bucket: "large", beta: 1.12, duration: 0, factor_exposures: { value: 0.9 } },
  { ticker: "UST10", weight: 0.15, sector: "", country: "US", currency: "USD", asset_class: "bond", market_cap_bucket: "large", beta: 0.0, duration: 8.5, credit_rating: "AAA", factor_exposures: {} },
  { ticker: "HYG",  weight: 0.08, sector: "", country: "US", currency: "USD", asset_class: "bond", market_cap_bucket: "large", beta: 0.3, duration: 4.2, credit_rating: "BB", factor_exposures: {} },
  { ticker: "NESN", weight: 0.06, sector: "Consumer Staples", country: "CH", currency: "CHF", asset_class: "equity", market_cap_bucket: "large", beta: 0.75, duration: 0, factor_exposures: { value: 0.5, dividend_yield: 1.2 } },
  { ticker: "TSM",  weight: 0.07, sector: "Information Technology", country: "TW", currency: "TWD", asset_class: "equity", market_cap_bucket: "large", beta: 1.35, duration: 0, factor_exposures: { growth: 1.4 } },
  { ticker: "BTC",  weight: 0.05, sector: "Digital Assets", country: "", currency: "USD", asset_class: "crypto", market_cap_bucket: "large", beta: 1.8, duration: 0, factor_exposures: { momentum: 2.0 } },
  { ticker: "GLD",  weight: 0.06, sector: "Materials", country: "US", currency: "USD", asset_class: "commodity", market_cap_bucket: "large", beta: 0.1, duration: 0, factor_exposures: {} },
  { ticker: "CASH", weight: 0.23, sector: "", country: "US", currency: "USD", asset_class: "cash", market_cap_bucket: "large", beta: 0.0, duration: 0, factor_exposures: {} },
];

function BreakdownBars({ data, title, colors }) {
  const entries = Object.entries(data || {}).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const max = entries[0]?.[1] || 1;
  return (
    <div style={CARD}>
      <div style={LABEL}>{title}</div>
      <div style={{ marginTop: 12 }}>
        {entries.map(([k, v], i) => {
          const color = colors?.[k] || ["#58a6ff","#3fb950","#e3b341","#f85149","#a371f7","#ffa657","#79c0ff","#56d364"][i % 8];
          return (
            <div key={k} style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                <span style={{ fontSize: 11, color: "#c9d1d9" }}>{k || "N/A"}</span>
                <span style={{ fontSize: 11, fontWeight: 700, color }}>{(v * 100).toFixed(1)}%</span>
              </div>
              <div style={{ height: 6, background: "#161b22", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${(v / max) * 100}%`, background: color, borderRadius: 3 }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function PortfolioExposure() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("overview");

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const res = await multiAssetApi.portfolioExposure({ holdings: DEMO_PORTFOLIO });
      setReport(res.data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const conc = report?.concentration;
  const risk = report?.risk;

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1200 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — PORTFOLIO EXPOSURE ENGINE</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Portfolio Exposure</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20, alignItems: "center" }}>
        {["overview", "sector", "geography", "risk"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid", borderColor: tab === t ? "#ffa657" : "#21262d", background: tab === t ? "#ffa65722" : "transparent", color: tab === t ? "#ffa657" : "#8b949e", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>{t.toUpperCase()}</button>
        ))}
        <button onClick={load} disabled={loading} style={{ marginLeft: "auto", padding: "6px 16px", background: "#ffa65733", border: "1px solid #ffa657", borderRadius: 6, color: "#ffa657", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
          {loading ? "Analysing…" : "Analyse Portfolio"}
        </button>
      </div>

      {error && <div style={{ color: "#f85149", marginBottom: 12, fontSize: 12 }}>{error}</div>}

      {tab === "overview" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={CARD}>
            <div style={LABEL}>Holdings ({DEMO_PORTFOLIO.length})</div>
            <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
              <thead><tr>{["Ticker", "Weight", "Asset Class", "Country"].map(h => <th key={h} style={{ textAlign: "left", padding: "4px 6px", fontSize: 10, color: "#8b949e", borderBottom: "1px solid #21262d" }}>{h}</th>)}</tr></thead>
              <tbody>
                {DEMO_PORTFOLIO.map(h => (
                  <tr key={h.ticker}>
                    <td style={{ padding: "5px 6px", fontWeight: 700, color: "#58a6ff", fontSize: 11 }}>{h.ticker}</td>
                    <td style={{ padding: "5px 6px", color: "#3fb950", fontSize: 11 }}>{(h.weight * 100).toFixed(1)}%</td>
                    <td style={{ padding: "5px 6px", color: "#8b949e", fontSize: 11 }}>{h.asset_class}</td>
                    <td style={{ padding: "5px 6px", color: "#8b949e", fontSize: 11 }}>{h.country || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={CARD}>
            <div style={LABEL}>Concentration Metrics</div>
            {conc ? (
              <div style={{ marginTop: 8 }}>
                {[["HHI", conc.hhi?.toFixed(4)], ["Effective N", conc.effective_n?.toFixed(1)], ["Top-1 Weight", `${(conc.top1_weight * 100).toFixed(1)}%`], ["Top-5 Weight", `${(conc.top5_weight * 100).toFixed(1)}%`], ["Top-10 Weight", `${(conc.top10_weight * 100).toFixed(1)}%`], ["Gini", conc.gini_coefficient?.toFixed(4)]].map(([k, v]) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #21262d", fontSize: 12 }}>
                    <span style={{ color: "#8b949e" }}>{k}</span>
                    <span style={{ color: "#ffa657", fontWeight: 600 }}>{v}</span>
                  </div>
                ))}
              </div>
            ) : <div style={{ fontSize: 12, color: "#8b949e", marginTop: 8 }}>Click "Analyse Portfolio" to load metrics</div>}
          </div>
        </div>
      )}

      {tab === "sector" && <BreakdownBars data={report?.sector?.breakdown} title="Sector Exposure" />}
      {tab === "geography" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <BreakdownBars data={report?.country?.breakdown} title="Country Exposure" />
          <BreakdownBars data={report?.currency?.breakdown} title="Currency Exposure" />
        </div>
      )}

      {tab === "risk" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={CARD}>
            <div style={LABEL}>Risk Metrics</div>
            {risk ? [["Portfolio Beta", risk.portfolio_beta?.toFixed(3)], ["Portfolio Duration", `${risk.portfolio_duration?.toFixed(2)} yrs`], ["Equity Share", `${(risk.equity_share * 100).toFixed(1)}%`], ["Bond Share", `${(risk.bond_share * 100).toFixed(1)}%`], ["Cash Share", `${(risk.cash_share * 100).toFixed(1)}%`], ["Alt Share", `${(risk.alternative_share * 100).toFixed(1)}%`], ["EM Share", `${(risk.emerging_market_share * 100).toFixed(1)}%`], ["Non-USD", `${(risk.currency_risk_score * 100).toFixed(1)}%`]].map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #21262d", fontSize: 12 }}>
                <span style={{ color: "#8b949e" }}>{k}</span>
                <span style={{ color: "#58a6ff", fontWeight: 600 }}>{v}</span>
              </div>
            )) : <div style={{ fontSize: 12, color: "#8b949e" }}>Click "Analyse Portfolio" to load risk metrics</div>}
          </div>
          <BreakdownBars data={report?.asset_class?.breakdown} title="Asset Class Mix" />
        </div>
      )}
    </div>
  );
}
