import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#ffa657", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c = "#ffa657") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  trendCard: (sentiment) => {
    const c = { VERY_POSITIVE: "#3fb950", POSITIVE: "#56d364", NEUTRAL: "#8b949e", NEGATIVE: "#f0883e", VERY_NEGATIVE: "#ff7b72" }[sentiment] || "#8b949e";
    return { background: "#161b22", border: `1px solid ${c}33`, borderRadius: 8, padding: "12px 16px", marginBottom: 10 };
  },
  velBar: (vel, maxVel) => ({ display: "inline-block", width: `${Math.min((vel / (maxVel || 1)) * 120, 120)}px`, height: 6, background: "#ffa657", borderRadius: 3, verticalAlign: "middle", marginLeft: 8 }),
  badge: (c) => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700, marginRight: 4 }),
};

const SENTIMENT_COLOR = { VERY_POSITIVE: "#3fb950", POSITIVE: "#56d364", NEUTRAL: "#8b949e", NEGATIVE: "#f0883e", VERY_NEGATIVE: "#ff7b72" };

export default function M18TrendDetector() {
  const [trends, setTrends] = useState([]);
  const [stats, setStats] = useState(null);
  const [windowHours, setWindowHours] = useState("4");
  const [minArticles, setMinArticles] = useState("2");
  const [loading, setLoading] = useState(false);
  const [tickerFilter, setTickerFilter] = useState("");

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  useEffect(() => {
    fetch("/m18/news/stats").then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  const detect = async () => {
    setLoading(true);
    const r = await post("/m18/news/trends", {
      window_hours: parseFloat(windowHours),
      min_articles: parseInt(minArticles),
    });
    if (r.ok) setTrends(await r.json());
    setLoading(false);
  };

  const filtered = tickerFilter
    ? trends.filter(t => t.top_tickers?.some(tk => tk.toUpperCase().includes(tickerFilter.toUpperCase())))
    : trends;

  const maxVelocity = filtered.length > 0 ? Math.max(...filtered.map(t => t.velocity || 0)) : 1;

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>News Trend Detector</div>

      {stats && (
        <div style={{ display: "flex", gap: 14, marginBottom: 16 }}>
          {[
            ["Total Articles", stats.total_articles ?? "—"],
            ["Categories", Object.keys(stats.by_category ?? {}).length || "—"],
            ["Positive", stats.by_sentiment?.POSITIVE ?? 0],
            ["Negative", stats.by_sentiment?.NEGATIVE ?? 0],
          ].map(([l, v]) => (
            <div key={l} style={{ background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "10px 16px" }}>
              <div style={{ fontSize: 10, color: "#8b949e" }}>{l}</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#f0f6fc" }}>{v}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>Window (hours)</div>
          <input style={{ ...S.input, width: 100, marginBottom: 0 }} value={windowHours} onChange={e => setWindowHours(e.target.value)} />
        </div>
        <div>
          <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>Min Articles</div>
          <input style={{ ...S.input, width: 80, marginBottom: 0 }} value={minArticles} onChange={e => setMinArticles(e.target.value)} />
        </div>
        <div style={{ paddingTop: 14 }}>
          <button style={S.btn()} onClick={detect} disabled={loading}>{loading ? "Scanning…" : "Detect Trends"}</button>
        </div>
      </div>

      {trends.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <input style={{ ...S.input, width: 200 }} value={tickerFilter} onChange={e => setTickerFilter(e.target.value)} placeholder="Filter by ticker…" />
        </div>
      )}

      {filtered.length === 0 && trends.length === 0 && (
        <div style={{ ...S.section, color: "#8b949e", fontSize: 12 }}>
          No trends detected. Ingest articles via the News Intelligence page first, then run detection here.
        </div>
      )}

      {filtered.length === 0 && trends.length > 0 && tickerFilter && (
        <div style={{ ...S.section, color: "#8b949e", fontSize: 12 }}>No trends matching ticker filter "{tickerFilter}".</div>
      )}

      {filtered.map(trend => (
        <div key={trend.trend_id} style={S.trendCard(trend.dominant_sentiment)}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
            <div>
              <span style={{ fontSize: 14, fontWeight: 700, color: "#f0f6fc" }}>{trend.topic}</span>
              <span style={{ fontSize: 11, color: "#8b949e", marginLeft: 10 }}>{trend.category}</span>
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <span style={S.badge(SENTIMENT_COLOR[trend.dominant_sentiment] || "#8b949e")}>{trend.dominant_sentiment}</span>
              <span style={S.badge("#58a6ff")}>{trend.article_count} articles</span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 11, color: "#8b949e" }}>Velocity:</span>
            <div style={S.velBar(trend.velocity, maxVelocity)} />
            <span style={{ fontSize: 11, color: "#ffa657", marginLeft: 8 }}>{trend.velocity?.toFixed(1)} articles/h</span>
          </div>

          <div style={{ display: "flex", gap: 12, fontSize: 11 }}>
            <div>
              <span style={{ color: "#8b949e" }}>Top Tickers: </span>
              {trend.top_tickers?.length > 0
                ? trend.top_tickers.map(tk => <span key={tk} style={{ color: "#58a6ff", marginRight: 4 }}>{tk}</span>)
                : <span style={{ color: "#8b949e" }}>—</span>}
            </div>
            <div>
              <span style={{ color: "#8b949e" }}>Avg Sentiment: </span>
              <span style={{ color: (trend.avg_sentiment_score ?? 0) >= 0 ? "#3fb950" : "#ff7b72" }}>
                {trend.avg_sentiment_score?.toFixed(3)}
              </span>
            </div>
          </div>

          {trend.keywords?.length > 0 && (
            <div style={{ marginTop: 8 }}>
              {trend.keywords.slice(0, 8).map(kw => (
                <span key={kw} style={{ fontSize: 10, background: "#21262d", color: "#8b949e", borderRadius: 3, padding: "1px 6px", marginRight: 4 }}>{kw}</span>
              ))}
            </div>
          )}
        </div>
      ))}

      {filtered.length > 0 && (
        <div style={S.section}>
          <div style={S.sHdr}>Trend Summary</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10 }}>
            {[
              ["Total Trends", filtered.length],
              ["Bullish Trends", filtered.filter(t => ["POSITIVE","VERY_POSITIVE"].includes(t.dominant_sentiment)).length],
              ["Bearish Trends", filtered.filter(t => ["NEGATIVE","VERY_NEGATIVE"].includes(t.dominant_sentiment)).length],
              ["Avg Velocity", `${(filtered.reduce((s, t) => s + (t.velocity || 0), 0) / filtered.length).toFixed(1)}/h`],
              ["Total Coverage", `${filtered.reduce((s, t) => s + (t.article_count || 0), 0)} articles`],
              ["Hottest Topic", filtered.sort((a, b) => (b.velocity || 0) - (a.velocity || 0))[0]?.topic || "—"],
            ].map(([k, v]) => (
              <div key={k} style={{ background: "#161b22", borderRadius: 6, padding: "8px 12px" }}>
                <div style={{ fontSize: 10, color: "#8b949e" }}>{k}</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#f0f6fc" }}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
