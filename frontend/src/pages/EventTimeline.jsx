import { useState, useEffect } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 12, fontFamily: "monospace" };
const BTN = (a) => ({ padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, background: a ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace" });

const IMP_COLOR = { critical: "#f85149", high: "#e3b341", medium: "#58a6ff", low: "#8b949e" };
const KIND_COLOR = { corporate: "#3fb950", macro: "#e3b341" };

function TimelineEvent({ ev }) {
  const dt = ev.timestamp ? new Date(ev.timestamp * 1000).toLocaleString() : "—";
  const color = IMP_COLOR[ev.importance] || "#8b949e";
  const kind = ev.kind || "corporate";
  return (
    <div style={{ display: "flex", gap: 14, padding: "10px 0", borderBottom: "1px solid #161b22" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 24 }}>
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, flexShrink: 0 }} />
        <div style={{ flex: 1, width: 1, background: "#21262d", marginTop: 4 }} />
      </div>
      <div style={{ flex: 1, paddingBottom: 6 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
          <span style={{ fontSize: 10, color: KIND_COLOR[kind], padding: "1px 6px", border: `1px solid ${KIND_COLOR[kind]}`, borderRadius: 3 }}>{kind}</span>
          <span style={{ fontSize: 11, color: "#8b949e" }}>{dt}</span>
          <span style={{ fontSize: 11, color }}>● {ev.importance}</span>
        </div>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#f0f6fc" }}>
          {ev.ticker ? `${ev.ticker} — ` : ""}{(ev.event_type || "").replace(/_/g," ").toUpperCase()}
        </div>
        <div style={{ fontSize: 12, color: "#8b949e", marginTop: 2 }}>{ev.description?.slice(0, 120)}</div>
      </div>
    </div>
  );
}

function GroupBlock({ group }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "#58a6ff" }}>{group.label}</div>
        <div style={{ fontSize: 11, color: "#8b949e" }}>
          {group.total_count} event{group.total_count !== 1 ? "s" : ""}
          {group.corporate_count > 0 && ` (${group.corporate_count} corp)`}
          {group.macro_count > 0 && ` (${group.macro_count} macro)`}
        </div>
      </div>
      <div style={{ ...CARD, padding: "8px 16px" }}>
        {group.events.map((ev, i) => <TimelineEvent key={ev.id || i} ev={ev} />)}
      </div>
    </div>
  );
}

export default function EventTimeline() {
  const [groups, setGroups] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [grouping, setGrouping] = useState("day");
  const [filterTicker, setFilterTicker] = useState("");
  const [filterSector, setFilterSector] = useState("");
  const [filterImp, setFilterImp] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const payload = { grouping, view: "market" };
      if (filterTicker) payload.tickers = [filterTicker.toUpperCase()];
      if (filterSector) payload.sectors = [filterSector];
      if (filterImp) payload.importance = [filterImp];
      const r = await eventsApi.timeline(payload);
      setGroups(r.data?.groups || []);
      setTotal(r.data?.total_events || 0);
    } catch {
      setGroups([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [grouping, filterTicker, filterSector, filterImp]);

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15</div>
      <h1 style={{ margin: "0 0 20px", fontSize: 22 }}>Event Timeline</h1>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20, alignItems: "center" }}>
        <div style={{ fontSize: 12, color: "#8b949e" }}>Group by:</div>
        {["day","week","month","quarter","year"].map((g) => (
          <button key={g} style={BTN(grouping === g)} onClick={() => setGrouping(g)}>{g}</button>
        ))}
        <input style={{ ...INPUT, width: 120 }} placeholder="Ticker filter" value={filterTicker}
          onChange={(e) => setFilterTicker(e.target.value)} />
        <input style={{ ...INPUT, width: 120 }} placeholder="Sector filter" value={filterSector}
          onChange={(e) => setFilterSector(e.target.value)} />
        <select style={{ ...INPUT, width: 120 }} value={filterImp} onChange={(e) => setFilterImp(e.target.value)}>
          <option value="">All importance</option>
          {["critical","high","medium","low"].map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>

      {loading ? (
        <div style={{ color: "#8b949e" }}>Loading timeline…</div>
      ) : groups.length === 0 ? (
        <div style={{ ...CARD, color: "#8b949e" }}>
          No events found for the selected filters. Add corporate or macro events first.
        </div>
      ) : (
        <>
          <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 16 }}>{total} total events across {groups.length} periods</div>
          {groups.map((g) => <GroupBlock key={g.label} group={g} />)}
        </>
      )}
    </div>
  );
}
