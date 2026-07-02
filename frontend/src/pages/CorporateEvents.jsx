import { useState, useEffect } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const INPUT = {
  background: "#161b22", border: "1px solid #30363d", borderRadius: 6,
  color: "#f0f6fc", padding: "6px 10px", fontSize: 12, fontFamily: "monospace",
};
const BTN = (active) => ({
  padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12,
  background: active ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace",
});

const CORP_TYPES = [
  "earnings","guidance","revenue_beat","eps_beat","dividend","dividend_increase","dividend_cut",
  "stock_split","reverse_split","buyback","share_issuance","ipo","secondary_offering",
  "merger","acquisition","ceo_change","cfo_change","insider_buy","insider_sell","sec_filing",
  "fda_approval","product_launch","partnership","litigation","credit_upgrade","credit_downgrade",
  "bankruptcy","restructuring",
];

const IMP_COLOR = { critical: "#f85149", high: "#e3b341", medium: "#58a6ff", low: "#8b949e" };

const BLANK = {
  ticker: "", company: "", event_type: "earnings", description: "",
  sector: "technology", industry: "software", country: "US",
  confidence: 0.9, source: "internal", importance: "", severity: "", tags: "",
};

export default function CorporateEvents() {
  const [events, setEvents] = useState([]);
  const [form, setForm] = useState(BLANK);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [selected, setSelected] = useState(null);
  const [filterTicker, setFilterTicker] = useState("");
  const [filterType, setFilterType] = useState("");
  const [tab, setTab] = useState("list");

  const load = async () => {
    try {
      const params = {};
      if (filterTicker) params.ticker = filterTicker.toUpperCase();
      if (filterType) params.event_type = filterType;
      const r = await eventsApi.listCorporate({ ...params, limit: 100 });
      setEvents(r.data || []);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterTicker, filterType]);

  const submit = async () => {
    if (!form.ticker || !form.description) return;
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        tags: form.tags ? form.tags.split(",").map((t) => t.trim()) : [],
        importance: form.importance || undefined,
        severity: form.severity || undefined,
      };
      await eventsApi.addCorporate(payload);
      setForm(BLANK);
      setTab("list");
      await load();
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const loadDetail = async (id) => {
    try {
      const r = await eventsApi.getCorporate(id);
      setSelected(r.data);
      setTab("detail");
    } catch {
      setSelected(null);
    }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15</div>
      <h1 style={{ margin: "0 0 20px", fontSize: 22 }}>Corporate Events</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {["list", "add", "detail"].map((t) => (
          <button key={t} style={BTN(tab === t)} onClick={() => setTab(t)}>
            {t === "list" ? "Event List" : t === "add" ? "+ Add Event" : "Detail"}
          </button>
        ))}
      </div>

      {tab === "list" && (
        <>
          <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
            <input style={{ ...INPUT, width: 120 }} placeholder="Filter ticker" value={filterTicker}
              onChange={(e) => setFilterTicker(e.target.value)} />
            <select style={{ ...INPUT, width: 180 }} value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="">All types</option>
              {CORP_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          {loading ? (
            <div style={{ color: "#8b949e" }}>Loading…</div>
          ) : events.length === 0 ? (
            <div style={{ ...CARD, color: "#8b949e" }}>No events found. Use "Add Event" to create one.</div>
          ) : (
            <div style={CARD}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #30363d" }}>
                    {["Date", "Ticker", "Type", "Importance", "Confidence", "Description"].map((h) => (
                      <th key={h} style={{ textAlign: "left", padding: "4px 8px", color: "#8b949e", fontSize: 11 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev) => (
                    <tr key={ev.id} onClick={() => loadDetail(ev.id)}
                      style={{ cursor: "pointer", borderBottom: "1px solid #21262d" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "#161b22")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "")}>
                      <td style={{ padding: "6px 8px", color: "#8b949e" }}>
                        {ev.timestamp ? new Date(ev.timestamp * 1000).toLocaleDateString() : "—"}
                      </td>
                      <td style={{ padding: "6px 8px", fontWeight: 700, color: "#58a6ff" }}>{ev.ticker}</td>
                      <td style={{ padding: "6px 8px", color: "#c9d1d9" }}>{ev.event_type.replace(/_/g, " ")}</td>
                      <td style={{ padding: "6px 8px" }}>
                        <span style={{ color: IMP_COLOR[ev.importance] || "#8b949e", fontSize: 11 }}>{ev.importance}</span>
                      </td>
                      <td style={{ padding: "6px 8px", color: "#3fb950" }}>{(ev.confidence * 100).toFixed(0)}%</td>
                      <td style={{ padding: "6px 8px", color: "#8b949e", maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {ev.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {tab === "add" && (
        <div style={{ ...CARD, maxWidth: 640 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16, color: "#58a6ff" }}>Add Corporate Event</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {[
              ["Ticker", "ticker", "text"], ["Company", "company", "text"],
              ["Sector", "sector", "text"], ["Industry", "industry", "text"],
              ["Country", "country", "text"], ["Source", "source", "text"],
            ].map(([label, key, type]) => (
              <div key={key}>
                <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>{label}</div>
                <input style={{ ...INPUT, width: "100%" }} type={type} value={form[key]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} />
              </div>
            ))}
            <div>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Event Type</div>
              <select style={{ ...INPUT, width: "100%" }} value={form.event_type}
                onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value }))}>
                {CORP_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Confidence</div>
              <input style={{ ...INPUT, width: "100%" }} type="number" step="0.05" min="0" max="1"
                value={form.confidence} onChange={(e) => setForm((f) => ({ ...f, confidence: parseFloat(e.target.value) }))} />
            </div>
            <div style={{ gridColumn: "span 2" }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Description</div>
              <textarea style={{ ...INPUT, width: "100%", height: 80, resize: "vertical" }}
                value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
            </div>
            <div style={{ gridColumn: "span 2" }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Tags (comma separated)</div>
              <input style={{ ...INPUT, width: "100%" }} value={form.tags}
                onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))} />
            </div>
          </div>
          <button style={{ ...BTN(true), marginTop: 16 }} disabled={submitting} onClick={submit}>
            {submitting ? "Adding…" : "Add Event"}
          </button>
        </div>
      )}

      {tab === "detail" && selected && (
        <div style={{ ...CARD, maxWidth: 640 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ fontWeight: 700, fontSize: 16, color: "#58a6ff" }}>{selected.ticker} — {selected.event_type.replace(/_/g, " ").toUpperCase()}</div>
            <span style={{ color: IMP_COLOR[selected.importance] || "#8b949e", fontSize: 12 }}>{selected.importance}</span>
          </div>
          {[
            ["Company", selected.company], ["Sector", selected.sector], ["Industry", selected.industry],
            ["Country", selected.country], ["Source", selected.source],
            ["Confidence", `${(selected.confidence * 100).toFixed(1)}%`],
            ["Severity", selected.severity],
            ["Date", selected.timestamp ? new Date(selected.timestamp * 1000).toLocaleString() : "—"],
          ].map(([k, v]) => (
            <div key={k} style={{ display: "flex", gap: 12, marginBottom: 6, fontSize: 12 }}>
              <span style={{ width: 100, color: "#8b949e", flexShrink: 0 }}>{k}</span>
              <span style={{ color: "#c9d1d9" }}>{v}</span>
            </div>
          ))}
          <div style={{ marginTop: 12, fontSize: 12, color: "#c9d1d9", lineHeight: 1.6 }}>{selected.description}</div>
          {selected.tags?.length > 0 && (
            <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
              {selected.tags.map((t) => (
                <span key={t} style={{ fontSize: 11, color: "#58a6ff", padding: "2px 8px", border: "1px solid #1f6feb", borderRadius: 4 }}>{t}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
