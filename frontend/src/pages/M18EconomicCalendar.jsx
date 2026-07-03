import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#79c0ff", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c = "#79c0ff") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
  impBadge: (imp) => {
    const c = { HIGH: "#ff7b72", MEDIUM: "#e3b341", LOW: "#3fb950" }[imp] || "#8b949e";
    return { display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700 };
  },
};

const IMPORTANCE_LEVELS = ["HIGH", "MEDIUM", "LOW"];
const EVENT_TYPES = ["GDP", "INFLATION", "UNEMPLOYMENT", "INTEREST_RATE", "PMI", "RETAIL_SALES", "TRADE_BALANCE", "CONSUMER_CONFIDENCE", "HOUSING_STARTS", "OTHER"];

export default function M18EconomicCalendar() {
  const [events, setEvents] = useState([]);
  const [form, setForm] = useState({
    event_name: "US Non-Farm Payrolls",
    country: "US",
    event_type: "UNEMPLOYMENT",
    scheduled_datetime: "2026-07-05T12:30:00",
    importance: "HIGH",
    forecast: "185000",
    previous: "177000",
    unit: "K jobs",
  });
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [filterCountry, setFilterCountry] = useState("");
  const [filterImportance, setFilterImportance] = useState("");
  const [limit, setLimit] = useState("30");

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const refresh = () => {
    fetch(`/m18/economic/calendar/upcoming?limit=${limit}`)
      .then(r => r.json())
      .then(d => { setEvents(Array.isArray(d) ? d : []); setInitialLoading(false); setFetchError(null); })
      .catch(() => { setFetchError("Unable to connect to the backend"); setInitialLoading(false); });
  };
  useEffect(() => { refresh(); }, [limit]);

  const addEvent = async () => {
    setLoading(true);
    await post("/m18/economic/calendar", {
      ...form,
      forecast: form.forecast ? parseFloat(form.forecast) : null,
      previous: form.previous ? parseFloat(form.previous) : null,
    });
    refresh();
    setLoading(false);
  };

  const filtered = events
    .filter(e => !filterCountry || e.country?.toUpperCase().includes(filterCountry.toUpperCase()))
    .filter(e => !filterImportance || e.importance === filterImportance);

  const groupByDate = filtered.reduce((acc, e) => {
    const date = e.scheduled_datetime?.slice(0, 10) || "Unknown";
    if (!acc[date]) acc[date] = [];
    acc[date].push(e);
    return acc;
  }, {});

  const highCount = filtered.filter(e => e.importance === "HIGH").length;

  if (initialLoading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 300, color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
      Loading…
    </div>
  );

  if (fetchError && events.length === 0) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, gap: 12 }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--negative)", letterSpacing: "0.1em" }}>ERROR</div>
      <div style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-3)" }}>Unable to connect to the backend</div>
      <button onClick={refresh} style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)", background: "var(--accent)22", border: "1px solid var(--accent)55", borderRadius: 6, padding: "6px 16px", cursor: "pointer" }}>Retry</button>
    </div>
  );

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Economic Calendar</div>

      <div style={{ display: "flex", gap: 14, marginBottom: 16 }}>
        {[["Upcoming Events", events.length], ["High Impact", highCount], ["Countries", new Set(events.map(e => e.country)).size]].map(([l, v]) => (
          <div key={l} style={{ background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "10px 16px" }}>
            <div style={{ fontSize: 10, color: "#8b949e" }}>{l}</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#f0f6fc" }}>{v}</div>
          </div>
        ))}
      </div>

      <div style={S.row2}>
        <div style={S.section}>
          <div style={S.sHdr}>Add Economic Event</div>
          {[
            ["event_name", "Event Name", null],
            ["country", "Country", null],
            ["event_type", "Event Type", EVENT_TYPES],
            ["scheduled_datetime", "Scheduled (YYYY-MM-DDTHH:MM:SS)", null],
            ["importance", "Importance", IMPORTANCE_LEVELS],
            ["forecast", "Forecast", null],
            ["previous", "Previous", null],
            ["unit", "Unit", null],
          ].map(([f, l, options]) => (
            <div key={f}>
              <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{l}</div>
              {options ? (
                <select style={{ ...S.input, marginBottom: 6 }} value={form[f]} onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))}>
                  {options.map(o => <option key={o}>{o}</option>)}
                </select>
              ) : (
                <input style={S.input} value={form[f]} onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))} />
              )}
            </div>
          ))}
          <button style={S.btn()} onClick={addEvent} disabled={loading}>{loading ? "Adding…" : "Add Event"}</button>
        </div>

        <div>
          <div style={S.section}>
            <div style={S.sHdr}>Filters</div>
            <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>Country</div>
            <input style={S.input} value={filterCountry} onChange={e => setFilterCountry(e.target.value.toUpperCase())} placeholder="US, GB, EU…" />
            <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>Importance</div>
            <select style={S.input} value={filterImportance} onChange={e => setFilterImportance(e.target.value)}>
              <option value="">All</option>
              {IMPORTANCE_LEVELS.map(i => <option key={i}>{i}</option>)}
            </select>
            <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>Limit</div>
            <select style={S.input} value={limit} onChange={e => setLimit(e.target.value)}>
              {["15","30","50","100"].map(n => <option key={n}>{n}</option>)}
            </select>
            <button style={S.btn()} onClick={refresh}>Refresh</button>

            <div style={{ marginTop: 14 }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 8 }}>Impact Distribution</div>
              {IMPORTANCE_LEVELS.map(imp => {
                const count = filtered.filter(e => e.importance === imp).length;
                const pct = filtered.length > 0 ? (count / filtered.length) * 100 : 0;
                const c = { HIGH: "#ff7b72", MEDIUM: "#e3b341", LOW: "#3fb950" }[imp];
                return (
                  <div key={imp} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <span style={{ width: 60, fontSize: 11, color: c }}>{imp}</span>
                    <div style={{ width: `${pct}%`, maxWidth: 150, height: 8, background: c, borderRadius: 2 }} />
                    <span style={{ fontSize: 11, color: "#8b949e" }}>{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {Object.keys(groupByDate).length === 0 ? (
        <div style={{ ...S.section, color: "#8b949e", fontSize: 12 }}>No events scheduled. Add economic events above.</div>
      ) : (
        Object.entries(groupByDate).sort().map(([date, evts]) => (
          <div key={date} style={S.section}>
            <div style={S.sHdr}>{date} — {evts.length} event{evts.length !== 1 ? "s" : ""}</div>
            <table style={S.table}>
              <thead>
                <tr>{["Time (UTC)","Event","Country","Type","Forecast","Previous","Unit","Impact"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {evts.sort((a, b) => (a.scheduled_datetime || "").localeCompare(b.scheduled_datetime || "")).map(e => (
                  <tr key={e.event_id} style={{ background: e.importance === "HIGH" ? "#ff7b7211" : "transparent" }}>
                    <td style={{ ...S.td, color: "#8b949e" }}>{e.scheduled_datetime?.slice(11, 16)}</td>
                    <td style={{ ...S.td, color: "#f0f6fc", fontWeight: 600 }}>{e.event_name}</td>
                    <td style={{ ...S.td, color: "#79c0ff" }}>{e.country}</td>
                    <td style={S.td}>{e.event_type}</td>
                    <td style={{ ...S.td, color: "#3fb950" }}>{e.forecast != null ? `${e.forecast} ${e.unit || ""}` : "—"}</td>
                    <td style={{ ...S.td, color: "#8b949e" }}>{e.previous != null ? `${e.previous} ${e.unit || ""}` : "—"}</td>
                    <td style={S.td}>{e.unit}</td>
                    <td style={S.td}><span style={S.impBadge(e.importance)}>{e.importance}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  );
}
