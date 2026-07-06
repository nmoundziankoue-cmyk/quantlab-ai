import { useState, useEffect } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD_STYLE = {
  background: "#0d1117",
  border: "1px solid #21262d",
  borderRadius: 8,
  padding: "16px 20px",
};

const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };
const VALUE = { fontSize: 24, fontWeight: 700, color: "#f0f6fc" };

function StatCard({ label, value, sub, color = "#58a6ff" }) {
  return (
    <div style={{ ...CARD_STYLE, flex: 1, minWidth: 140 }}>
      <div style={LABEL}>{label}</div>
      <div style={{ ...VALUE, color }}>{value ?? "—"}</div>
      {sub && <div style={{ fontSize: 11, color: "#8b949e", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function EventRow({ ev }) {
  const IMP_COLOR = { critical: "#f85149", high: "#e3b341", medium: "#58a6ff", low: "#8b949e" };
  const color = IMP_COLOR[ev.importance] || "#8b949e";
  const date = ev.timestamp ? new Date(ev.timestamp * 1000).toLocaleDateString() : "—";
  return (
    <div style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid #21262d", alignItems: "center" }}>
      <div style={{ width: 64, fontSize: 11, color: "#8b949e" }}>{date}</div>
      <div style={{ width: 64, fontWeight: 700, color: "#f0f6fc", fontSize: 13 }}>{ev.ticker || ev.country}</div>
      <div style={{ flex: 1, fontSize: 12, color: "#c9d1d9" }}>{(ev.event_type || "").replace(/_/g, " ").toUpperCase()}</div>
      <div style={{ fontSize: 11, color, padding: "2px 8px", border: `1px solid ${color}`, borderRadius: 4 }}>{ev.importance}</div>
    </div>
  );
}

export default function EventDashboard() {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [macro, setMacro] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [s, corp, mac] = await Promise.all([
          eventsApi.statistics(),
          eventsApi.listCorporate({ limit: 8 }),
          eventsApi.listMacro({ limit: 5 }),
        ]);
        setStats(s.data);
        setRecent(corp.data || []);
        setMacro(mac.data || []);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <div style={{ color: "#8b949e", padding: 32 }}>Loading event dashboard…</div>;
  if (error) return (
    <div style={{ padding: 32, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 14, color: "#8b949e", marginBottom: 8 }}>Event Dashboard</div>
      <div style={{ fontSize: 13, color: "#8b949e" }}>Backend not reachable — event data unavailable.</div>
    </div>
  );

  const corp = stats?.corporate || {};
  const mac = stats?.macro || {};

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ marginBottom: 4, fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em" }}>M15 — EVENT INTELLIGENCE PLATFORM</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Event Dashboard</h1>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 24 }}>
        <StatCard label="Total Events" value={stats?.total_events ?? 0} color="#58a6ff" />
        <StatCard label="Corporate" value={corp.total ?? 0} sub={`${corp.unique_tickers ?? 0} tickers`} color="#3fb950" />
        <StatCard label="Macro" value={mac.total ?? 0} sub={`${Object.keys(mac.by_country || {}).length} countries`} color="#e3b341" />
        <StatCard label="Critical" value={(corp.by_importance?.critical ?? 0) + (mac.by_importance?.critical ?? 0)} color="#f85149" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={CARD_STYLE}>
          <div style={{ ...LABEL, marginBottom: 12 }}>Recent Corporate Events</div>
          {recent.length === 0 ? (
            <div style={{ color: "#8b949e", fontSize: 12 }}>No events yet. Add some via the Corporate Events page.</div>
          ) : (
            recent.map((ev) => <EventRow key={ev.id} ev={ev} />)
          )}
        </div>

        <div style={CARD_STYLE}>
          <div style={{ ...LABEL, marginBottom: 12 }}>Recent Macro Events</div>
          {macro.length === 0 ? (
            <div style={{ color: "#8b949e", fontSize: 12 }}>No macro events yet. Add some via the Macro Events page.</div>
          ) : (
            macro.map((ev) => <EventRow key={ev.id} ev={ev} />)
          )}
        </div>
      </div>

      {corp.by_type && Object.keys(corp.by_type).length > 0 && (
        <div style={{ ...CARD_STYLE, marginTop: 16 }}>
          <div style={{ ...LABEL, marginBottom: 12 }}>Event Type Distribution</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {Object.entries(corp.by_type)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 12)
              .map(([k, v]) => (
                <div key={k} style={{ fontSize: 11, color: "#c9d1d9", padding: "3px 10px", background: "#161b22", border: "1px solid #30363d", borderRadius: 4 }}>
                  {k.replace(/_/g, " ")} <span style={{ color: "#58a6ff" }}>{v}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
