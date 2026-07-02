import { useState } from "react";
import { useNewsFeed, useBreakingNews, useDailySummary, useNewsClusters, useNewsImpact } from "../hooks/useNewsIntelligence";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  title: { fontSize: 22, fontWeight: 700 },
  tabs: { display: "flex", gap: 4, marginBottom: 20, borderBottom: "1px solid #30363d", paddingBottom: 0 },
  tab: (active) => ({ padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600, borderBottom: `2px solid ${active ? "#58a6ff" : "transparent"}`, color: active ? "#58a6ff" : "#8b949e", marginBottom: -1 }),
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  newsItem: { padding: "14px 0", borderBottom: "1px solid #21262d", cursor: "pointer" },
  headline: { fontSize: 14, fontWeight: 600, marginBottom: 4 },
  meta: { fontSize: 12, color: "#8b949e" },
  badge: (color) => ({ background: color + "22", color, borderRadius: 12, padding: "2px 10px", fontSize: 11, fontWeight: 600, marginRight: 6 }),
  stat: { textAlign: "center" },
  statNum: (color) => ({ fontSize: 28, fontWeight: 700, color }),
  statLabel: { fontSize: 11, color: "#8b949e", marginTop: 2 },
};

const urgencyColor = { BREAKING: "#f85149", HIGH: "#f0883e", MEDIUM: "#f0883e", LOW: "#8b949e" };
const sentimentColor = { BULLISH: "#3fb950", BEARISH: "#f85149", NEUTRAL: "#8b949e" };

function NewsItem({ item }) {
  const urg = item.urgency_label || "LOW";
  const sent = item.sentiment_label || "NEUTRAL";
  return (
    <div style={S.newsItem}>
      <div style={S.headline}>{item.headline}</div>
      <div style={S.meta}>
        <span style={S.badge(urgencyColor[urg])}>{urg}</span>
        <span style={S.badge(sentimentColor[sent])}>{sent}</span>
        <span style={{ marginRight: 12 }}>{item.source}</span>
        <span>{item.event_type}</span>
      </div>
    </div>
  );
}

export default function NewsTerminal() {
  const [activeTab, setActiveTab] = useState("feed");
  const { data: feed = [] } = useNewsFeed({ page_size: 30 });
  const { data: breaking = [] } = useBreakingNews({ limit: 20 });
  const { data: summary } = useDailySummary();
  const { data: clusters = [] } = useNewsClusters();
  const { data: impact = [] } = useNewsImpact({ limit: 20 });

  const tabs = ["feed", "breaking", "impact", "clusters", "summary"];

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div style={S.title}>News Intelligence Terminal</div>
        <div style={{ fontSize: 12, color: "#3fb950" }}>● Live</div>
      </div>

      <div style={S.tabs}>
        {tabs.map((t) => (
          <div key={t} style={S.tab(activeTab === t)} onClick={() => setActiveTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
            {t === "breaking" && breaking.length > 0 && <span style={{ marginLeft: 6, background: "#f85149", borderRadius: 10, padding: "1px 6px", fontSize: 10, color: "#fff" }}>{breaking.length}</span>}
          </div>
        ))}
      </div>

      {activeTab === "feed" && (
        <div style={S.card}>
          <div style={{ fontSize: 13, color: "#8b949e", marginBottom: 12 }}>{feed.length} events</div>
          {feed.length === 0 && <div style={{ color: "#8b949e" }}>No news events. Ingest events from the Alternative Data terminal.</div>}
          {feed.map((item, i) => <NewsItem key={i} item={item} />)}
        </div>
      )}

      {activeTab === "breaking" && (
        <div style={S.card}>
          {breaking.length === 0 && <div style={{ color: "#8b949e" }}>No breaking news at this time.</div>}
          {breaking.map((item, i) => <NewsItem key={i} item={item} />)}
        </div>
      )}

      {activeTab === "impact" && (
        <div style={S.card}>
          {impact.length === 0 && <div style={{ color: "#8b949e" }}>No high-impact events.</div>}
          {impact.map((item, i) => <NewsItem key={i} item={item} />)}
        </div>
      )}

      {activeTab === "clusters" && (
        <div style={S.card}>
          {clusters.length === 0 && <div style={{ color: "#8b949e" }}>No clusters yet.</div>}
          {clusters.map((c, i) => (
            <div key={i} style={{ padding: "10px 0", borderBottom: "1px solid #21262d" }}>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{c.cluster || c.cluster_label}</div>
              <div style={{ fontSize: 12, color: "#8b949e" }}>{c.event_count} events · Top: {(c.top_tickers || []).slice(0, 3).join(", ")}</div>
            </div>
          ))}
        </div>
      )}

      {activeTab === "summary" && summary && (
        <div style={S.card}>
          <div style={{ display: "flex", gap: 32, marginBottom: 20 }}>
            <div style={S.stat}><div style={S.statNum("#e6edf3")}>{summary.total_events}</div><div style={S.statLabel}>Total Events</div></div>
            <div style={S.stat}><div style={S.statNum("#f85149")}>{summary.breaking_count}</div><div style={S.statLabel}>Breaking</div></div>
            <div style={S.stat}><div style={S.statNum("#3fb950")}>{summary.bullish_count}</div><div style={S.statLabel}>Bullish</div></div>
            <div style={S.stat}><div style={S.statNum("#f85149")}>{summary.bearish_count}</div><div style={S.statLabel}>Bearish</div></div>
          </div>
          {summary.top_tickers?.length > 0 && (
            <div>
              <div style={{ fontSize: 13, color: "#8b949e", marginBottom: 6 }}>Top Mentioned Tickers</div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {summary.top_tickers.map((t) => (
                  <span key={t} style={{ background: "#1c2128", border: "1px solid #30363d", borderRadius: 4, padding: "4px 10px", fontSize: 13, fontWeight: 600 }}>{t}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
