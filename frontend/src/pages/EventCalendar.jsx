import { useState, useEffect } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 12, fontFamily: "monospace" };
const BTN = (a) => ({ padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, background: a ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace" });

const IMP_COLOR = { critical: "#f85149", high: "#e3b341", medium: "#58a6ff", low: "#8b949e" };
const VIEWS = ["agenda","day","week","month","heatmap","upcoming","past"];

function HeatmapCell({ item }) {
  const max = 10;
  const intensity = Math.min(1, item.count / max);
  const bg = `rgba(31, 111, 235, ${0.1 + intensity * 0.8})`;
  return (
    <div title={`${item.label}: ${item.count} events`}
      style={{ background: bg, border: "1px solid #21262d", borderRadius: 4, padding: "8px 6px", textAlign: "center", minWidth: 52 }}>
      <div style={{ fontSize: 10, color: "#8b949e" }}>{item.label}</div>
      <div style={{ fontSize: 14, fontWeight: 700, color: "#f0f6fc" }}>{item.count}</div>
    </div>
  );
}

function AgendaEntry({ entry }) {
  const color = IMP_COLOR[entry.importance] || "#8b949e";
  return (
    <div style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid #161b22", alignItems: "flex-start" }}>
      <div style={{ width: 80, flexShrink: 0 }}>
        <div style={{ fontSize: 11, color: "#8b949e" }}>{entry.date_label}</div>
        <div style={{ fontSize: 10, color: "#8b949e" }}>{entry.time_label}</div>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#f0f6fc" }}>{entry.title}</div>
        <div style={{ fontSize: 11, color: "#8b949e", marginTop: 2 }}>{entry.description?.slice(0, 100)}</div>
      </div>
      <span style={{ fontSize: 11, color, padding: "2px 8px", border: `1px solid ${color}`, borderRadius: 4, flexShrink: 0 }}>{entry.importance}</span>
    </div>
  );
}

function DayBlock({ day }) {
  if (!day) return null;
  return (
    <div style={{ ...CARD, marginBottom: 12 }}>
      <div style={{ fontWeight: 700, color: "#58a6ff", marginBottom: 10, fontSize: 13 }}>
        {day.date} — {day.total_count} events
        <span style={{ fontSize: 11, color: "#8b949e", marginLeft: 10 }}>({day.corporate_count} corp, {day.macro_count} macro)</span>
      </div>
      {(day.entries || []).map((e, i) => <AgendaEntry key={e.entry_id || i} entry={e} />)}
    </div>
  );
}

export default function EventCalendar() {
  const [view, setView] = useState("agenda");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filterImp, setFilterImp] = useState("");
  const [limit, setLimit] = useState(30);

  const load = async () => {
    setLoading(true);
    try {
      const payload = {
        view,
        limit,
        importance: filterImp ? [filterImp] : undefined,
        since: Math.floor(Date.now() / 1000) - 86400 * 90,
        until: Math.floor(Date.now() / 1000) + 86400 * 30,
        grouping: "day",
      };
      const r = await eventsApi.calendar(payload);
      setData(r.data);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [view, filterImp, limit]);

  const renderContent = () => {
    if (loading) return <div style={{ color: "#8b949e" }}>Loading…</div>;
    if (!data) return <div style={{ ...CARD, color: "#8b949e" }}>No data.</div>;

    if (view === "agenda" || view === "upcoming" || view === "past") {
      const entries = data.entries || [];
      return entries.length === 0 ? (
        <div style={{ ...CARD, color: "#8b949e" }}>No events. Add corporate or macro events first.</div>
      ) : (
        <div style={CARD}>{entries.map((e, i) => <AgendaEntry key={e.entry_id || i} entry={e} />)}</div>
      );
    }

    if (view === "day") return <DayBlock day={data} />;

    if (view === "week") {
      const days = data.days || [];
      return <>{days.map((d, i) => <DayBlock key={i} day={d} />)}</>;
    }

    if (view === "month") {
      const weeks = data.weeks || [];
      return weeks.map((w, i) => (
        <div key={i} style={{ ...CARD, marginBottom: 12 }}>
          <div style={{ fontWeight: 700, color: "#58a6ff", marginBottom: 10, fontSize: 12 }}>{w.week_label}</div>
          {(w.entries || []).map((e, j) => <AgendaEntry key={e.entry_id || j} entry={e} />)}
        </div>
      ));
    }

    if (view === "heatmap") {
      const items = data.data || [];
      return (
        <div>
          <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 12 }}>Event density heatmap — darker = more events</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {items.map((item, i) => <HeatmapCell key={i} item={item} />)}
          </div>
          {items.length === 0 && <div style={{ ...CARD, color: "#8b949e" }}>No heatmap data.</div>}
        </div>
      );
    }

    return <pre style={{ fontSize: 11, color: "#8b949e" }}>{JSON.stringify(data, null, 2).slice(0, 2000)}</pre>;
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15</div>
      <h1 style={{ margin: "0 0 20px", fontSize: 22 }}>Event Calendar</h1>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20, alignItems: "center" }}>
        {VIEWS.map((v) => <button key={v} style={BTN(view === v)} onClick={() => setView(v)}>{v}</button>)}
        <select style={{ ...INPUT, width: 120 }} value={filterImp} onChange={(e) => setFilterImp(e.target.value)}>
          <option value="">All importance</option>
          {["critical","high","medium","low"].map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        <select style={{ ...INPUT, width: 80 }} value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
          {[20,50,100].map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </div>

      {renderContent()}
    </div>
  );
}
