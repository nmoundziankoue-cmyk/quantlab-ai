import { useState } from "react";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };

const MARKET_DATA = [
  { ticker: "AAPL",  name: "Apple",          sector: "Technology",    ret: 1.42,  mcap: 2800 },
  { ticker: "MSFT",  name: "Microsoft",       sector: "Technology",    ret: 0.87,  mcap: 2600 },
  { ticker: "NVDA",  name: "NVIDIA",          sector: "Technology",    ret: 3.21,  mcap: 1800 },
  { ticker: "AMZN",  name: "Amazon",          sector: "Consumer",      ret: -0.34, mcap: 1700 },
  { ticker: "GOOGL", name: "Alphabet",        sector: "Technology",    ret: 0.55,  mcap: 1600 },
  { ticker: "META",  name: "Meta",            sector: "Technology",    ret: 2.10,  mcap: 1200 },
  { ticker: "TSLA",  name: "Tesla",           sector: "Consumer",      ret: -2.45, mcap: 800  },
  { ticker: "JPM",   name: "JPMorgan",        sector: "Financials",    ret: 0.32,  mcap: 550  },
  { ticker: "V",     name: "Visa",            sector: "Financials",    ret: 0.18,  mcap: 520  },
  { ticker: "JNJ",   name: "J&J",             sector: "Healthcare",    ret: -0.21, mcap: 430  },
  { ticker: "WMT",   name: "Walmart",         sector: "Consumer",      ret: 0.45,  mcap: 420  },
  { ticker: "XOM",   name: "ExxonMobil",      sector: "Energy",        ret: 1.12,  mcap: 410  },
  { ticker: "UNH",   name: "UnitedHealth",    sector: "Healthcare",    ret: 0.67,  mcap: 400  },
  { ticker: "MA",    name: "Mastercard",      sector: "Financials",    ret: 0.23,  mcap: 390  },
  { ticker: "PG",    name: "Procter & Gamble",sector: "Staples",       ret: -0.08, mcap: 370  },
  { ticker: "CVX",   name: "Chevron",         sector: "Energy",        ret: 0.88,  mcap: 290  },
  { ticker: "ABBV",  name: "AbbVie",          sector: "Healthcare",    ret: -0.43, mcap: 280  },
  { ticker: "HD",    name: "Home Depot",      sector: "Consumer",      ret: 0.11,  mcap: 270  },
  { ticker: "PFE",   name: "Pfizer",          sector: "Healthcare",    ret: -1.21, mcap: 150  },
  { ticker: "BAC",   name: "Bank of America", sector: "Financials",    ret: 0.42,  mcap: 280  },
];

const SECTOR_COLORS = {
  Technology: "#58a6ff", Consumer: "#e3b341", Financials: "#3fb950",
  Healthcare: "#a371f7", Energy: "#ffa657", Staples: "#79c0ff",
};

function colorForRet(ret) {
  if (ret > 2) return "#56d364";
  if (ret > 0.5) return "#3fb950";
  if (ret > 0) return "#3fb95066";
  if (ret > -0.5) return "#f8514966";
  if (ret > -2) return "#f85149";
  return "#ff7b72";
}

export default function MarketMap() {
  const [groupBy, setGroupBy] = useState("sector");
  const [sizeBy, setSizeBy] = useState("mcap");
  const [hoveredTicker, setHoveredTicker] = useState(null);

  const grouped = {};
  MARKET_DATA.forEach(d => {
    const key = groupBy === "sector" ? d.sector : "All";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(d);
  });

  const totalMcap = MARKET_DATA.reduce((s, d) => s + d.mcap, 0);

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1200 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — MARKET MAP</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Market Map</h1>

      <div style={{ display: "flex", gap: 16, marginBottom: 20, alignItems: "center" }}>
        <div>
          <div style={LABEL}>Group By</div>
          <select value={groupBy} onChange={e => setGroupBy(e.target.value)} style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", fontFamily: "monospace", fontSize: 12, padding: "6px 10px", appearance: "none" }}>
            <option value="sector">Sector</option>
            <option value="none">All</option>
          </select>
        </div>
        <div>
          <div style={LABEL}>Size By</div>
          <select value={sizeBy} onChange={e => setSizeBy(e.target.value)} style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", fontFamily: "monospace", fontSize: 12, padding: "6px 10px", appearance: "none" }}>
            <option value="mcap">Market Cap</option>
            <option value="equal">Equal</option>
          </select>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 16, alignItems: "center" }}>
          {[["Strong Gain > 2%", "#56d364"], ["Gain", "#3fb950"], ["Flat", "#8b949e"], ["Loss", "#f85149"], ["Strong Loss", "#ff7b72"]].map(([label, color]) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11 }}>
              <div style={{ width: 12, height: 12, background: color, borderRadius: 2 }} />
              <span style={{ color: "#8b949e" }}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        {Object.entries(grouped).map(([sector, stocks]) => {
          const sectorRet = stocks.reduce((s, d) => s + d.ret * d.mcap, 0) / stocks.reduce((s, d) => s + d.mcap, 0);
          return (
            <div key={sector} style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: SECTOR_COLORS[sector] || "#8b949e" }} />
                <span style={{ fontSize: 12, fontWeight: 700, color: SECTOR_COLORS[sector] || "#8b949e" }}>{sector}</span>
                <span style={{ fontSize: 11, color: sectorRet >= 0 ? "#3fb950" : "#f85149", marginLeft: 4 }}>{sectorRet >= 0 ? "+" : ""}{sectorRet.toFixed(2)}%</span>
              </div>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {stocks.map(d => {
                  const size = sizeBy === "equal" ? 80 : Math.max(60, Math.min(160, (d.mcap / 800) * 120));
                  const color = colorForRet(d.ret);
                  const isHovered = hoveredTicker === d.ticker;
                  return (
                    <div key={d.ticker}
                      onMouseEnter={() => setHoveredTicker(d.ticker)}
                      onMouseLeave={() => setHoveredTicker(null)}
                      style={{ width: size, height: size * 0.7, background: color, border: isHovered ? "2px solid #fff" : "1px solid #161b22", borderRadius: 6, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "all 0.1s", position: "relative" }}>
                      <div style={{ fontSize: Math.min(13, size / 5), fontWeight: 700, color: "#0d1117" }}>{d.ticker}</div>
                      <div style={{ fontSize: Math.min(11, size / 6), color: "#0d111799", marginTop: 2 }}>{d.ret >= 0 ? "+" : ""}{d.ret.toFixed(2)}%</div>
                      {isHovered && (
                        <div style={{ position: "absolute", bottom: "110%", left: "50%", transform: "translateX(-50%)", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", whiteSpace: "nowrap", zIndex: 100, pointerEvents: "none" }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: "#f0f6fc" }}>{d.ticker} — {d.name}</div>
                          <div style={{ fontSize: 11, color: "#8b949e" }}>Market Cap: ${d.mcap}B</div>
                          <div style={{ fontSize: 11, color: color }}>Return: {d.ret >= 0 ? "+" : ""}{d.ret.toFixed(2)}%</div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
