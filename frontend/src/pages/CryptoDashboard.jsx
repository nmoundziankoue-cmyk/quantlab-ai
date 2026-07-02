import { useState } from "react";
import { multiAssetApi } from "../api/multiAssetApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };

const CRYPTO_UNIVERSE = [
  { ticker: "BTC", name: "Bitcoin", sector: "layer1", market_cap_usd: 1200000, circulating_supply: 19700000, total_supply: 21000000, is_stablecoin: false, chain: "native", consensus: "pow" },
  { ticker: "ETH", name: "Ethereum", sector: "layer1", market_cap_usd: 420000, circulating_supply: 120000000, total_supply: 120000000, is_stablecoin: false, chain: "native", consensus: "pos" },
  { ticker: "BNB", name: "BNB", sector: "exchange", market_cap_usd: 88000, circulating_supply: 145000000, total_supply: 200000000, is_stablecoin: false, chain: "bnb", consensus: "dpos" },
  { ticker: "SOL", name: "Solana", sector: "layer1", market_cap_usd: 78000, circulating_supply: 440000000, total_supply: 600000000, is_stablecoin: false, chain: "native", consensus: "poh" },
  { ticker: "USDT", name: "Tether", sector: "stablecoin", market_cap_usd: 112000, circulating_supply: 112000000000, total_supply: 112000000000, is_stablecoin: true, chain: "multi", consensus: "n/a" },
  { ticker: "USDC", name: "USD Coin", sector: "stablecoin", market_cap_usd: 34000, circulating_supply: 34000000000, total_supply: 34000000000, is_stablecoin: true, chain: "multi", consensus: "n/a" },
  { ticker: "ADA", name: "Cardano", sector: "layer1", market_cap_usd: 18000, circulating_supply: 35000000000, total_supply: 45000000000, is_stablecoin: false, chain: "native", consensus: "pos" },
  { ticker: "LINK", name: "Chainlink", sector: "oracle", market_cap_usd: 9500, circulating_supply: 600000000, total_supply: 1000000000, is_stablecoin: false, chain: "ethereum", consensus: "pos" },
  { ticker: "UNI", name: "Uniswap", sector: "defi", market_cap_usd: 5800, circulating_supply: 753000000, total_supply: 1000000000, is_stablecoin: false, chain: "ethereum", consensus: "pos" },
  { ticker: "ARB", name: "Arbitrum", sector: "layer2", market_cap_usd: 3200, circulating_supply: 3200000000, total_supply: 10000000000, is_stablecoin: false, chain: "ethereum", consensus: "optimistic" },
];

const SECTOR_COLORS = { layer1: "#58a6ff", layer2: "#3fb950", defi: "#e3b341", stablecoin: "#f0f6fc", exchange: "#f85149", oracle: "#a371f7", nft: "#ffa657", other: "#8b949e" };

function DominanceBar({ label, value, color }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
        <span style={{ fontSize: 12, color: "#c9d1d9" }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 700, color }}>{(value * 100).toFixed(2)}%</span>
      </div>
      <div style={{ height: 8, background: "#161b22", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${value * 100}%`, background: color, borderRadius: 4 }} />
      </div>
    </div>
  );
}

export default function CryptoDashboard() {
  const [dominance, setDominance] = useState(null);
  const [stableRatio, setStableRatio] = useState(null);
  const [cycle, setCycle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("dominance");

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const [d, s, c] = await Promise.all([
        multiAssetApi.cryptoDominance(CRYPTO_UNIVERSE),
        multiAssetApi.stablecoinRatio(CRYPTO_UNIVERSE),
        multiAssetApi.cryptoCycle({ btc_current_price: 61000, btc_ath: 73000, btc_returns_90d: Array(90).fill(0).map((_, i) => (Math.sin(i * 0.1) * 0.01)), altcoin_dominance: 0.35, stablecoin_ratio: 0.08 }),
      ]);
      setDominance(d.data);
      setStableRatio(s.data);
      setCycle(c.data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const SENTIMENT_COLORS = { extreme_fear: "#f85149", fear: "#e3b341", neutral: "#8b949e", greed: "#3fb950", extreme_greed: "#56d364" };
  const PHASE_COLORS = { accumulation: "#58a6ff", markup: "#3fb950", distribution: "#e3b341", markdown: "#f85149" };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1100 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — CRYPTO INTELLIGENCE ENGINE</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Crypto Dashboard</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20, alignItems: "center" }}>
        {["dominance", "stablecoins", "cycle", "universe"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid", borderColor: tab === t ? "#ffa657" : "#21262d", background: tab === t ? "#ffa65722" : "transparent", color: tab === t ? "#ffa657" : "#8b949e", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>{t.toUpperCase()}</button>
        ))}
        <button onClick={load} disabled={loading} style={{ marginLeft: "auto", padding: "6px 16px", background: "#ffa65733", border: "1px solid #ffa657", borderRadius: 6, color: "#ffa657", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
          {loading ? "Loading…" : "Analyse Universe"}
        </button>
      </div>

      {error && <div style={{ color: "#f85149", marginBottom: 12, fontSize: 12 }}>{error}</div>}

      {tab === "dominance" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={CARD}>
            <div style={LABEL}>Market Dominance</div>
            <div style={{ marginTop: 12 }}>
              {dominance ? <>
                <DominanceBar label="Bitcoin (BTC)" value={dominance.btc_dominance} color="#f7931a" />
                <DominanceBar label="Ethereum (ETH)" value={dominance.eth_dominance} color="#627eea" />
                <DominanceBar label="Stablecoins" value={dominance.stablecoin_dominance} color="#26a17b" />
                <DominanceBar label="Altcoins" value={dominance.altcoin_dominance} color="#a371f7" />
                <div style={{ marginTop: 12, fontSize: 12, color: "#8b949e" }}>Total Market Cap: <span style={{ color: "#ffa657", fontWeight: 700 }}>${((dominance.total_market_cap_usd || 0) / 1000).toFixed(0)}B</span></div>
              </> : <div style={{ fontSize: 12, color: "#8b949e" }}>Click "Analyse Universe" to load dominance data</div>}
            </div>
          </div>
          <div style={CARD}>
            <div style={LABEL}>Sector Dominance</div>
            <div style={{ marginTop: 12 }}>
              {dominance?.sector_dominance ? Object.entries(dominance.sector_dominance).sort((a, b) => b[1] - a[1]).map(([sec, val]) => (
                <DominanceBar key={sec} label={sec.toUpperCase()} value={val} color={SECTOR_COLORS[sec] || "#8b949e"} />
              )) : <div style={{ fontSize: 12, color: "#8b949e" }}>Click "Analyse Universe" to load sector data</div>}
            </div>
          </div>
        </div>
      )}

      {tab === "stablecoins" && (
        <div style={CARD}>
          <div style={LABEL}>Stablecoin Market Ratio</div>
          {stableRatio ? (
            <div style={{ textAlign: "center", padding: 24 }}>
              <div style={{ fontSize: 40, fontWeight: 700, color: stableRatio.signal === "risk_off" ? "#f85149" : "#3fb950" }}>{(stableRatio.ratio * 100).toFixed(2)}%</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: stableRatio.signal === "risk_off" ? "#f85149" : "#3fb950", marginTop: 8 }}>{stableRatio.signal.replace("_", " ").toUpperCase()}</div>
              <div style={{ fontSize: 12, color: "#8b949e", marginTop: 8 }}>Threshold: {(stableRatio.threshold * 100).toFixed(0)}% | Stablecoin Cap: ${(stableRatio.stablecoin_market_cap / 1000).toFixed(0)}B</div>
            </div>
          ) : <div style={{ fontSize: 12, color: "#8b949e" }}>Click "Analyse Universe" to load data</div>}
        </div>
      )}

      {tab === "cycle" && (
        <div style={CARD}>
          <div style={LABEL}>Market Cycle Indicator</div>
          {cycle ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginTop: 12 }}>
              <div style={{ textAlign: "center" }}>
                <div style={LABEL}>Cycle Phase</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: PHASE_COLORS[cycle.cycle_phase] }}>{cycle.cycle_phase?.toUpperCase()}</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={LABEL}>Fear & Greed</div>
                <div style={{ fontSize: 28, fontWeight: 700, color: SENTIMENT_COLORS[cycle.sentiment] }}>{cycle.fear_greed_score?.toFixed(0)}</div>
                <div style={{ fontSize: 11, color: "#8b949e" }}>{cycle.sentiment?.replace("_", " ")}</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={LABEL}>BTC Drawdown</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#f85149" }}>-{(cycle.btc_drawdown_from_ath * 100)?.toFixed(1)}%</div>
                <div style={{ fontSize: 11, color: "#8b949e" }}>from ATH</div>
              </div>
            </div>
          ) : <div style={{ fontSize: 12, color: "#8b949e" }}>Click "Analyse Universe" to load cycle data</div>}
        </div>
      )}

      {tab === "universe" && (
        <div style={CARD}>
          <div style={LABEL}>Crypto Universe ({CRYPTO_UNIVERSE.length} assets)</div>
          <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
            <thead><tr>{["Ticker", "Name", "Sector", "Market Cap", "Stablecoin"].map(h => <th key={h} style={{ textAlign: "left", padding: "6px 8px", fontSize: 11, color: "#8b949e", borderBottom: "1px solid #21262d" }}>{h}</th>)}</tr></thead>
            <tbody>
              {CRYPTO_UNIVERSE.map(a => (
                <tr key={a.ticker}>
                  <td style={{ padding: "8px", fontWeight: 700, color: "#ffa657", fontSize: 12 }}>{a.ticker}</td>
                  <td style={{ padding: "8px", fontSize: 12, color: "#c9d1d9" }}>{a.name}</td>
                  <td style={{ padding: "8px" }}><span style={{ fontSize: 11, color: SECTOR_COLORS[a.sector] || "#8b949e", background: `${SECTOR_COLORS[a.sector]}22`, padding: "2px 6px", borderRadius: 4 }}>{a.sector}</span></td>
                  <td style={{ padding: "8px", fontSize: 12, color: "#8b949e" }}>${(a.market_cap_usd / 1000).toFixed(0)}B</td>
                  <td style={{ padding: "8px", fontSize: 11, color: a.is_stablecoin ? "#3fb950" : "#8b949e" }}>{a.is_stablecoin ? "YES" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
