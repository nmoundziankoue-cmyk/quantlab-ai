import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#d2a8ff", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c = "#d2a8ff") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
  badge: (c) => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", c, fontWeight: 700, color: c }),
  timeOfDayColor: { PRE_MARKET: "#79c0ff", AFTER_HOURS: "#e3b341", DURING_MARKET: "#3fb950", UNKNOWN: "#8b949e" },
};

export default function M18EarningsCalendar() {
  const [upcoming, setUpcoming] = useState([]);
  const [form, setForm] = useState({ ticker: "META", fiscal_quarter: "Q1 2026", expected_date: "2026-07-25", time_of_day: "AFTER_HOURS", consensus_eps: "5.18", consensus_revenue: "42000", num_estimates: "28" });
  const [estimateForm, setEstimateForm] = useState({ ticker: "META", fiscal_quarter: "Q1 2026", analyst: "Goldman Sachs", eps_estimate: "5.25", revenue_estimate: "42500", rating: "BUY" });
  const [limit, setLimit] = useState("30");
  const [filterTicker, setFilterTicker] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const refresh = () => {
    setLoading(true);
    fetch(`/m18/earnings/calendar/upcoming?limit=${limit}`)
      .then(r => r.json())
      .then(d => { setUpcoming(Array.isArray(d) ? d : []); setLoading(false); setError(null); })
      .catch(() => { setError("Unable to connect to the backend"); setLoading(false); });
  };
  useEffect(() => { refresh(); }, [limit]);

  const addCalendar = async () => {
    await post("/m18/earnings/calendar", {
      ...form,
      consensus_eps: parseFloat(form.consensus_eps),
      consensus_revenue: parseFloat(form.consensus_revenue),
      num_estimates: parseInt(form.num_estimates),
    });
    refresh();
  };

  const addEstimate = async () => {
    await post("/m18/earnings/estimates", {
      ...estimateForm,
      eps_estimate: parseFloat(estimateForm.eps_estimate),
      revenue_estimate: parseFloat(estimateForm.revenue_estimate),
    });
  };

  const filtered = filterTicker ? upcoming.filter(e => e.ticker?.toUpperCase().includes(filterTicker.toUpperCase())) : upcoming;

  const groupByDate = filtered.reduce((acc, e) => {
    const date = e.expected_date?.slice(0, 10) || "Unknown";
    if (!acc[date]) acc[date] = [];
    acc[date].push(e);
    return acc;
  }, {});

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 300, color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
      Loading…
    </div>
  );

  if (error && upcoming.length === 0) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, gap: 12 }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--negative)", letterSpacing: "0.1em" }}>ERROR</div>
      <div style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-3)" }}>Unable to connect to the backend</div>
      <button onClick={refresh} style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)", background: "var(--accent)22", border: "1px solid var(--accent)55", borderRadius: 6, padding: "6px 16px", cursor: "pointer" }}>Retry</button>
    </div>
  );

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Earnings Calendar</div>

      <div style={S.row2}>
        <div style={S.section}>
          <div style={S.sHdr}>Add Calendar Entry</div>
          {[["ticker","Ticker"],["fiscal_quarter","Fiscal Quarter"],["expected_date","Expected Date (YYYY-MM-DD)"],["time_of_day","Time of Day"],["consensus_eps","Consensus EPS"],["consensus_revenue","Consensus Revenue ($M)"],["num_estimates","# Estimates"]].map(([f, l]) => (
            <div key={f}>
              <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{l}</div>
              {f === "time_of_day" ? (
                <select style={{ ...S.input, marginBottom: 6 }} value={form[f]} onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))}>
                  {["PRE_MARKET","DURING_MARKET","AFTER_HOURS","UNKNOWN"].map(o => <option key={o}>{o}</option>)}
                </select>
              ) : (
                <input style={S.input} value={form[f]} onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))} />
              )}
            </div>
          ))}
          <button style={S.btn()} onClick={addCalendar}>Add Entry</button>
        </div>

        <div style={S.section}>
          <div style={S.sHdr}>Add Analyst Estimate</div>
          {[["ticker","Ticker"],["fiscal_quarter","Fiscal Quarter"],["analyst","Analyst / Firm"],["eps_estimate","EPS Estimate"],["revenue_estimate","Revenue Estimate ($M)"],["rating","Rating (BUY/HOLD/SELL)"]].map(([f, l]) => (
            <div key={f}>
              <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{l}</div>
              <input style={S.input} value={estimateForm[f]} onChange={e => setEstimateForm(p => ({ ...p, [f]: e.target.value }))} />
            </div>
          ))}
          <button style={S.btn("#56d364")} onClick={addEstimate}>Add Estimate</button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "center" }}>
        <input style={{ ...S.input, width: 160, marginBottom: 0 }} value={filterTicker} onChange={e => setFilterTicker(e.target.value)} placeholder="Filter ticker…" />
        <select style={{ ...S.input, width: 100, marginBottom: 0 }} value={limit} onChange={e => setLimit(e.target.value)}>
          {["15","30","50","100"].map(n => <option key={n}>{n}</option>)}
        </select>
        <button style={S.btn()} onClick={refresh}>Refresh</button>
        <span style={{ fontSize: 11, color: "#8b949e" }}>{upcoming.length} upcoming earnings events</span>
      </div>

      {Object.keys(groupByDate).length === 0 ? (
        <div style={{ ...S.section, color: "#8b949e", fontSize: 12 }}>No earnings events scheduled. Add calendar entries above.</div>
      ) : (
        Object.entries(groupByDate).sort().map(([date, events]) => (
          <div key={date} style={S.section}>
            <div style={S.sHdr}>{date} — {events.length} event{events.length !== 1 ? "s" : ""}</div>
            <table style={S.table}>
              <thead><tr>{["Ticker","Quarter","Time","Consensus EPS","Consensus Rev ($M)","# Estimates"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
              <tbody>
                {events.map(e => (
                  <tr key={e.entry_id}>
                    <td style={{ ...S.td, color: "#58a6ff", fontWeight: 700 }}>{e.ticker}</td>
                    <td style={{ ...S.td, color: "#d2a8ff" }}>{e.fiscal_quarter}</td>
                    <td style={S.td}>
                      <span style={{ ...S.badge(S.timeOfDayColor[e.time_of_day] || "#8b949e"), color: S.timeOfDayColor[e.time_of_day] || "#8b949e" }}>
                        {e.time_of_day}
                      </span>
                    </td>
                    <td style={{ ...S.td, color: "#3fb950" }}>${e.consensus_eps?.toFixed(2)}</td>
                    <td style={S.td}>${e.consensus_revenue?.toLocaleString()}</td>
                    <td style={{ ...S.td, color: "#8b949e" }}>{e.num_estimates}</td>
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
