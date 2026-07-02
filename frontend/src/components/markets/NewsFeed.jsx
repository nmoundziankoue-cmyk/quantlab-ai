import { useNews } from "../../hooks/useMarket";
import SentimentGauge from "./SentimentGauge";

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

const SENTIMENT_COLORS = {
  bullish: "#4ade80",
  bearish: "#f87171",
  neutral: "#64748b",
};

export default function NewsFeed({ ticker }) {
  const { data, isLoading, isError } = useNews(ticker);

  if (!ticker) return <div style={styles.empty}>Select a ticker to view news.</div>;
  if (isLoading) return <div style={styles.empty}>Loading news…</div>;
  if (isError || !data) return <div style={styles.empty}>Could not load news.</div>;

  return (
    <div style={styles.root}>
      {/* Sentiment header */}
      <div style={styles.sentimentRow}>
        <SentimentGauge
          score={data.overall_score}
          label={data.overall_label}
          signal={data.signal}
          size={140}
        />
        <div style={styles.sentimentMeta}>
          <div style={styles.sentimentTicker}>{ticker}</div>
          <div style={styles.sentimentSub}>Sentiment from {data.articles.length} recent articles</div>
        </div>
      </div>

      {/* Article list */}
      {data.articles.length === 0 ? (
        <div style={styles.empty}>No recent news available.</div>
      ) : (
        <div style={styles.list}>
          {data.articles.map((a) => (
            <a
              key={a.uuid}
              href={a.link}
              target="_blank"
              rel="noopener noreferrer"
              style={styles.article}
            >
              <div style={styles.articleTop}>
                <span
                  style={{
                    ...styles.sentimentDot,
                    background: SENTIMENT_COLORS[a.sentiment_label] ?? "#64748b",
                  }}
                />
                <span style={styles.publisher}>{a.publisher}</span>
                <span style={styles.pubDate}>{fmtDate(a.published_at)}</span>
              </div>
              <div style={styles.title}>{a.title}</div>
              {a.related_tickers.length > 0 && (
                <div style={styles.tickers}>
                  {a.related_tickers.slice(0, 5).map((t) => (
                    <span key={t} style={styles.tickerBadge}>{t}</span>
                  ))}
                </div>
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  root: {},
  sentimentRow: {
    display: "flex",
    alignItems: "center",
    gap: 24,
    padding: "16px 20px",
    background: "#0d0f14",
    border: "1px solid #1e2230",
    borderRadius: 10,
    marginBottom: 16,
  },
  sentimentMeta: {},
  sentimentTicker: { fontSize: 22, fontWeight: 700, color: "#93c5fd", marginBottom: 4 },
  sentimentSub: { fontSize: 12, color: "#475569" },
  list: { display: "flex", flexDirection: "column", gap: 10 },
  article: {
    display: "block",
    padding: "12px 14px",
    background: "#0d0f14",
    border: "1px solid #1e2230",
    borderRadius: 8,
    textDecoration: "none",
    transition: "border-color 0.12s",
  },
  articleTop: { display: "flex", alignItems: "center", gap: 8, marginBottom: 6 },
  sentimentDot: { width: 8, height: 8, borderRadius: "50%", flexShrink: 0 },
  publisher: { fontSize: 11, color: "#475569", fontWeight: 600 },
  pubDate: { fontSize: 11, color: "#334155", marginLeft: "auto" },
  title: { fontSize: 13, color: "#cbd5e1", lineHeight: 1.4 },
  tickers: { display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" },
  tickerBadge: {
    background: "#111623",
    border: "1px solid #1e2230",
    borderRadius: 4,
    color: "#93c5fd",
    fontSize: 10,
    fontWeight: 600,
    padding: "1px 6px",
  },
  empty: { color: "#475569", fontSize: 13, padding: "24px 0" },
};
