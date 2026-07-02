import { useProjects, usePinnedItems, useRecentActivity } from "../hooks/useResearchWorkspace";
import { useDailySummary } from "../hooks/useNewsIntelligence";
import { useAltDataEvents } from "../hooks/useAlternativeData";
import { useAgents } from "../hooks/useAgents";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 24, fontWeight: 700, marginBottom: 4, color: "#e6edf3" },
  subtitle: { fontSize: 14, color: "#8b949e", marginBottom: 24 },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16, marginBottom: 24 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20 },
  cardTitle: { fontSize: 13, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  bigNum: { fontSize: 36, fontWeight: 700, color: "#58a6ff" },
  bigLabel: { fontSize: 12, color: "#8b949e", marginTop: 4 },
  row: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #21262d" },
  tag: { background: "#1c2128", border: "1px solid #30363d", borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#8b949e" },
  badge: (color) => ({ background: color + "22", color, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600 }),
};

function StatCard({ label, value, sub, color = "#58a6ff" }) {
  return (
    <div style={S.card}>
      <div style={S.cardTitle}>{label}</div>
      <div style={{ ...S.bigNum, color }}>{value ?? "—"}</div>
      {sub && <div style={S.bigLabel}>{sub}</div>}
    </div>
  );
}

export default function ResearchDashboard() {
  const { data: projects = [] } = useProjects();
  const { data: pinned = [] } = usePinnedItems();
  const { data: activity = [] } = useRecentActivity(10);
  const { data: summary } = useDailySummary();
  const { data: events = [] } = useAltDataEvents({ limit: 5 });
  const { data: agents = [] } = useAgents();

  const activeProjects = projects.filter((p) => p.status === "ACTIVE").length;
  const totalEvents = summary?.total_events ?? 0;
  const breakingCount = summary?.breaking_count ?? 0;

  return (
    <div style={S.page}>
      <div style={S.title}>Research Intelligence Dashboard</div>
      <div style={S.subtitle}>M6 AI Research Copilot & Alternative Data Terminal</div>

      <div style={S.grid}>
        <StatCard label="Active Projects" value={activeProjects} sub={`${projects.length} total`} />
        <StatCard label="Pinned Items" value={pinned.length} sub="bookmarks & tickers" color="#3fb950" />
        <StatCard label="Today's Events" value={totalEvents} sub={`${breakingCount} breaking`} color="#f0883e" />
        <StatCard label="AI Agents Available" value={agents.length} sub="specialized analysts" color="#a5d6ff" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={S.card}>
          <div style={S.cardTitle}>Recent Activity</div>
          {activity.length === 0 && <div style={{ color: "#8b949e", fontSize: 13 }}>No recent activity</div>}
          {activity.slice(0, 8).map((a, i) => (
            <div key={i} style={S.row}>
              <span style={{ fontSize: 13, flex: 1 }}>{a.description}</span>
              <span style={S.tag}>{a.entity_type}</span>
            </div>
          ))}
        </div>

        <div style={S.card}>
          <div style={S.cardTitle}>Market Intelligence Feed</div>
          {events.length === 0 && <div style={{ color: "#8b949e", fontSize: 13 }}>No events yet — ingest data from the Alternative Data terminal</div>}
          {events.slice(0, 6).map((e, i) => (
            <div key={i} style={S.row}>
              <span style={{ fontSize: 13, flex: 1 }}>{e.headline}</span>
              <span style={S.badge(e.sentiment_score > 0.2 ? "#3fb950" : e.sentiment_score < -0.2 ? "#f85149" : "#8b949e")}>
                {e.event_type}
              </span>
            </div>
          ))}
        </div>
      </div>

      {summary && (
        <div style={{ ...S.card, marginTop: 16 }}>
          <div style={S.cardTitle}>Daily News Summary</div>
          <div style={{ display: "flex", gap: 32 }}>
            <div><div style={{ fontSize: 22, fontWeight: 700, color: "#3fb950" }}>{summary.bullish_count}</div><div style={{ fontSize: 11, color: "#8b949e" }}>Bullish</div></div>
            <div><div style={{ fontSize: 22, fontWeight: 700, color: "#f85149" }}>{summary.bearish_count}</div><div style={{ fontSize: 11, color: "#8b949e" }}>Bearish</div></div>
            <div><div style={{ fontSize: 22, fontWeight: 700, color: "#f0883e" }}>{summary.breaking_count}</div><div style={{ fontSize: 11, color: "#8b949e" }}>Breaking</div></div>
            <div><div style={{ fontSize: 22, fontWeight: 700, color: "#8b949e" }}>{summary.avg_sentiment != null ? (summary.avg_sentiment * 100).toFixed(0) + "%" : "—"}</div><div style={{ fontSize: 11, color: "#8b949e" }}>Avg Sentiment</div></div>
          </div>
        </div>
      )}
    </div>
  );
}
