import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";

const API = "";
const TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "XOM"];

function QuoteCard({ ticker }) {
  const { data, isLoading } = useQuery({
    queryKey: ["quote", ticker],
    queryFn: () => axios.get(`${API}/market/quote/${ticker}`).then(r => r.data),
    refetchInterval: 30000,
    retry: 1,
  });

  const quote = data?.quote ?? data;
  const change = quote?.change_pct ?? quote?.regularMarketChangePercent ?? 0;
  const isUp = change >= 0;

  return (
    <div style={{ background: "#161b22", border: `1px solid ${isLoading ? "#30363d" : isUp ? "#1a4d2e" : "#4d1f1f"}`, borderRadius: 8, padding: 16, minWidth: 160 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontWeight: 700, color: "#e6edf3", fontSize: 15 }}>{ticker}</span>
        <span style={{ fontSize: 12, color: isUp ? "#3fb950" : "#f85149", background: isUp ? "#1a4d2e" : "#4d1f1f", padding: "2px 8px", borderRadius: 12 }}>
          {isLoading ? "..." : `${isUp ? "+" : ""}${(change ?? 0).toFixed(2)}%`}
        </span>
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: "#e6edf3", marginTop: 8 }}>
        {isLoading ? "—" : `$${(quote?.price ?? quote?.regularMarketPrice ?? 0).toFixed(2)}`}
      </div>
      <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>
        Vol: {isLoading ? "—" : (quote?.volume ?? quote?.regularMarketVolume ?? "N/A")?.toLocaleString?.() ?? "N/A"}
      </div>
    </div>
  );
}

export default function LiveMarkets() {
  const [search, setSearch] = useState("");
  const [added, setAdded] = useState([]);
  const allTickers = [...TICKERS, ...added.filter(t => !TICKERS.includes(t))];

  const handleAdd = (e) => {
    e.preventDefault();
    const t = search.trim().toUpperCase();
    if (t && !allTickers.includes(t)) setAdded(a => [...a, t]);
    setSearch("");
  };

  return (
    <div style={{ padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Live Markets</h1>
          <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Real-time quotes — refreshes every 30s</p>
        </div>
        <form onSubmit={handleAdd} style={{ display: "flex", gap: 8 }}>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Add ticker…"
            style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "8px 12px", fontSize: 13, width: 140 }}
          />
          <button type="submit" style={{ background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "8px 16px", cursor: "pointer", fontSize: 13 }}>
            Add
          </button>
        </form>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
        {allTickers.map(t => <QuoteCard key={t} ticker={t} />)}
      </div>
    </div>
  );
}
