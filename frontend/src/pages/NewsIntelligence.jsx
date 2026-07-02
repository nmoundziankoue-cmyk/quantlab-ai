import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8001";
const card = { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 };
const SENTIMENT_COLORS = { positive: "#3fb950", negative: "#f85149", neutral: "#8b949e", bullish: "#3fb950", bearish: "#f85149" };

function SentimentBadge({ sentiment }) {
  const s = (sentiment ?? "neutral").toLowerCase();
  const color = SENTIMENT_COLORS[s] ?? "#8b949e";
  return (
    <span style={{ background: color + "22", color, padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600 }}>
      {s}
    </span>
  );
}

export default function NewsIntelligence() {
  const [ticker, setTicker] = useState("AAPL");
  const [query, setQuery] = useState("AAPL");

  const { data: newsData, refetch } = useQuery({
    queryKey: ["news-items", query],
    queryFn: () => axios.get(`${API}/news/intelligence?ticker=${query}&limit=20`).then(r => r.data)
      .catch(() => ({ items: [], sentiment_summary: null })),
    enabled: false,
  });

  const { data: marketIntel } = useQuery({
    queryKey: ["market-intel"],
    queryFn: () => axios.get(`${API}/market-intelligence/signals`).then(r => r.data)
      .catch(() => ({ signals: [] })),
    refetchInterval: 60000,
  });

  return (
    <div style={{ padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>News Intelligence</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Sentiment analysis and market signal detection</p>
      </div>

      {/* Search */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <input value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())}
          style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "10px 14px", fontSize: 14, width: 140 }}
          placeholder="Ticker"
        />
        <button onClick={() => { setQuery(ticker); setTimeout(refetch, 0); }}
          style={{ background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", cursor: "pointer", fontSize: 13, fontWeight: 600 }}>
          Search News
        </button>
      </div>

      {/* Sentiment summary */}
      {newsData?.sentiment_summary && (
        <div style={{ ...card, display: "flex", gap: 20 }}>
          <div>
            <div style={{ fontSize: 11, color: "#8b949e" }}>Overall Sentiment</div>
            <SentimentBadge sentiment={newsData.sentiment_summary.overall} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: "#8b949e" }}>Score</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "#e6edf3" }}>{newsData.sentiment_summary.score?.toFixed(2)}</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "#8b949e" }}>Articles</div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>{newsData.sentiment_summary.article_count}</div>
          </div>
        </div>
      )}

      {/* News items */}
      {newsData?.items?.length > 0 && (
        <div style={card}>
          <div style={{ fontWeight: 600, marginBottom: 14 }}>Recent News</div>
          {newsData.items.map((item, i) => (
            <div key={i} style={{ padding: "12px 0", borderBottom: "1px solid #21262d" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#e6edf3" }}>{item.title}</div>
                <SentimentBadge sentiment={item.sentiment} />
              </div>
              <div style={{ fontSize: 12, color: "#8b949e" }}>{item.source} · {item.published_at}</div>
            </div>
          ))}
        </div>
      )}

      {/* Market signals */}
      <div style={card}>
        <div style={{ fontWeight: 600, marginBottom: 14 }}>Market Intelligence Signals</div>
        {(marketIntel?.signals ?? []).length === 0 && (
          <div style={{ color: "#8b949e", fontSize: 13 }}>No signals available. Connect market intelligence data sources to enable.</div>
        )}
        {(marketIntel?.signals ?? []).map((s, i) => (
          <div key={i} style={{ padding: "10px 0", borderBottom: "1px solid #21262d", fontSize: 13 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontWeight: 600 }}>{s.ticker ?? "—"}</span>
              <SentimentBadge sentiment={s.signal} />
              <span style={{ color: "#8b949e" }}>{s.confidence ? `${(s.confidence * 100).toFixed(0)}%` : ""}</span>
            </div>
          </div>
        ))}

        {/* Static example signals when API unavailable */}
        {(marketIntel?.signals ?? []).length === 0 && (
          <div style={{ marginTop: 12 }}>
            {[
              { ticker: "NVDA", signal: "bullish", theme: "AI infrastructure spending surge", confidence: "87%" },
              { ticker: "AAPL", signal: "neutral", theme: "iPhone cycle uncertainty vs services growth", confidence: "72%" },
              { ticker: "XOM", signal: "bearish", theme: "Oil demand concerns as EV adoption accelerates", confidence: "65%" },
            ].map((s, i) => (
              <div key={i} style={{ padding: "10px 0", borderBottom: "1px solid #21262d", fontSize: 13 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontWeight: 700, color: "#58a6ff" }}>{s.ticker}</span>
                  <SentimentBadge sentiment={s.signal} />
                  <span style={{ color: "#8b949e" }}>{s.confidence}</span>
                </div>
                <div style={{ color: "#8b949e", fontSize: 12 }}>{s.theme}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
