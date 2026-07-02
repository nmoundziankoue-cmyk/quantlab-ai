import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  grid3: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginBottom: 20 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "14px 18px" },
  label: { fontSize: 11, color: "#8b949e", textTransform: "uppercase", marginBottom: 4 },
  val: { fontSize: 18, fontWeight: 700, color: "#f0f6fc" },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#56d364", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  ta: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6, minHeight: 60, resize: "vertical" },
  btn: (c="#56d364") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6 }),
  sentiment: (s) => {
    const c = { VERY_POSITIVE: "#3fb950", POSITIVE: "#56d364", NEUTRAL: "#8b949e", NEGATIVE: "#f0883e", VERY_NEGATIVE: "#ff7b72" }[s] || "#8b949e";
    return { display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700 };
  },
  article: { background: "#161b22", borderRadius: 6, padding: "10px 14px", marginBottom: 8 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
};

export default function M18NewsIntel() {
  const [stats, setStats] = useState(null);
  const [latest, setLatest] = useState([]);
  const [trends, setTrends] = useState([]);
  const [sentiment, setSentiment] = useState(null);
  const [signal, setSignal] = useState(null);
  const [form, setForm] = useState({ headline: "Apple reports record quarterly revenue, beats estimates by 8%", body: "Apple Inc. reported quarterly revenue of $119.6B, surpassing analyst consensus by 8%. EPS of $2.18 beat expectations. CEO Tim Cook raised guidance citing strong iPhone 16 demand.", source: "Reuters" });
  const [tickerInput, setTickerInput] = useState("AAPL");

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const refresh = () => {
    fetch("/m18/news/stats").then(r => r.json()).then(setStats).catch(() => {});
    fetch("/m18/news/articles/latest?limit=10").then(r => r.json()).then(setLatest).catch(() => {});
  };
  useEffect(() => { refresh(); }, []);

  const ingest = async () => {
    await post("/m18/news/articles", form);
    refresh();
  };

  const detectTrends = async () => {
    const r = await post("/m18/news/trends", { window_hours: 4, min_articles: 1 });
    if (r.ok) setTrends(await r.json());
  };

  const getTickerSentiment = async () => {
    const r = await fetch(`/m18/news/sentiment/${tickerInput.toUpperCase()}`);
    if (r.ok) setSentiment(await r.json());
  };

  const getSignal = async () => {
    const r = await fetch(`/m18/news/signal/${tickerInput.toUpperCase()}`);
    if (r.ok) setSignal(await r.json());
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>News Intelligence</div>

      <div style={S.grid3}>
        {[
          { label: "Total Articles", val: stats?.total_articles ?? "—" },
          { label: "Categories", val: Object.keys(stats?.by_category ?? {}).length || "—" },
          { label: "Sentiment Mix", val: stats ? `${stats.by_sentiment?.POSITIVE ?? 0}P / ${stats.by_sentiment?.NEGATIVE ?? 0}N` : "—" },
        ].map(k => <div key={k.label} style={S.card}><div style={S.label}>{k.label}</div><div style={S.val}>{k.val}</div></div>)}
      </div>

      <div style={S.row2}>
        <div style={S.section}>
          <div style={S.sHdr}>Ingest Article</div>
          <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>Headline</div>
          <input style={S.input} value={form.headline} onChange={e => setForm(p => ({ ...p, headline: e.target.value }))} />
          <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>Body</div>
          <textarea style={S.ta} value={form.body} onChange={e => setForm(p => ({ ...p, body: e.target.value }))} />
          <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>Source</div>
          <input style={S.input} value={form.source} onChange={e => setForm(p => ({ ...p, source: e.target.value }))} />
          <button style={S.btn()} onClick={ingest}>Ingest Article</button>
        </div>

        <div style={S.section}>
          <div style={S.sHdr}>Ticker Analysis</div>
          <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
            <input style={{ ...S.input, width: 120, marginBottom: 0 }} value={tickerInput} onChange={e => setTickerInput(e.target.value.toUpperCase())} placeholder="Ticker" />
            <button style={S.btn()} onClick={getTickerSentiment}>Sentiment</button>
            <button style={S.btn("#58a6ff")} onClick={getSignal}>Signal</button>
          </div>
          {sentiment && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: "#c9d1d9", marginBottom: 6 }}>Sentiment for <b style={{ color: "#56d364" }}>{sentiment.ticker}</b></div>
              {[["Articles", sentiment.article_count], ["Avg Score", sentiment.avg_sentiment_score?.toFixed(4)], ["Positive", sentiment.positive_count], ["Negative", sentiment.negative_count], ["Trend", sentiment.trend]].map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, padding: "2px 0" }}>
                  <span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: "#f0f6fc" }}>{v}</span>
                </div>
              ))}
              <span style={{ ...S.sentiment(sentiment.sentiment_label), marginTop: 6 }}>{sentiment.sentiment_label}</span>
            </div>
          )}
          {signal && (
            <div style={{ background: "#161b22", borderRadius: 6, padding: 10 }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Trading Signal</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: signal.direction === "BUY" ? "#3fb950" : signal.direction === "SELL" ? "#ff7b72" : "#8b949e" }}>{signal.direction}</div>
              <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>Confidence: {(signal.confidence * 100).toFixed(1)}%</div>
            </div>
          )}
          <button style={S.btn("#e3b341")} onClick={detectTrends}>Detect Trends</button>
          {trends.length > 0 && (
            <div style={{ marginTop: 10 }}>
              {trends.map(t => (
                <div key={t.trend_id} style={{ background: "#161b22", borderRadius: 6, padding: "8px 10px", marginBottom: 6 }}>
                  <div style={{ fontSize: 12, color: "#e3b341" }}>{t.topic} <span style={{ color: "#8b949e" }}>({t.article_count} articles, {t.velocity.toFixed(1)}/h)</span></div>
                  <div style={{ fontSize: 11, color: "#8b949e" }}>Top: {t.top_tickers.join(", ") || "—"}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Latest Articles</div>
        {latest.length === 0 ? <div style={{ color: "#8b949e", fontSize: 12 }}>No articles ingested yet.</div> : (
          latest.map(a => (
            <div key={a.article_id} style={S.article}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 12, color: "#f0f6fc", fontWeight: 600 }}>{a.headline}</span>
                <span style={S.sentiment(a.sentiment)}>{a.sentiment}</span>
              </div>
              <div style={{ fontSize: 11, color: "#8b949e" }}>{a.source} · {a.category} · tickers: {a.tickers_mentioned?.join(", ") || "—"} · signal: <span style={{ color: a.market_signal === "BUY" || a.market_signal === "STRONG_BUY" ? "#3fb950" : "#ff7b72" }}>{a.market_signal}</span></div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
