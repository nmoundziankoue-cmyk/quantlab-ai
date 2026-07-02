import { useState, useEffect } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 12, fontFamily: "monospace" };
const BTN = (a) => ({ padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, background: a ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace" });

const MACRO_TYPES = [
  "cpi","ppi","gdp","retail_sales","pmi","nfp","fomc","ecb","boc","boj",
  "fed_minutes","interest_rate_decision","inflation","unemployment",
  "housing_starts","consumer_confidence","industrial_production","trade_balance","oil_inventories",
];

const IMP_COLOR = { critical: "#f85149", high: "#e3b341", medium: "#58a6ff", low: "#8b949e" };
const SURPRISE_COLOR = (v) => v > 0 ? "#3fb950" : v < 0 ? "#f85149" : "#8b949e";

const BLANK = {
  event_type: "cpi", description: "", country: "US",
  actual: "", forecast: "", previous: "", importance: "",
};

export default function MacroEvents() {
  const [events, setEvents] = useState([]);
  const [form, setForm] = useState(BLANK);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [tab, setTab] = useState("list");
  const [selected, setSelected] = useState(null);
  const [filterType, setFilterType] = useState("");
  const [filterCountry, setFilterCountry] = useState("");

  const load = async () => {
    try {
      const params = { limit: 100 };
      if (filterType) params.event_type = filterType;
      if (filterCountry) params.country = filterCountry.toUpperCase();
      const r = await eventsApi.listMacro(params);
      setEvents(r.data || []);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterType, filterCountry]);

  const submit = async () => {
    if (!form.description) return;
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        actual: form.actual !== "" ? parseFloat(form.actual) : undefined,
        forecast: form.forecast !== "" ? parseFloat(form.forecast) : undefined,
        previous: form.previous !== "" ? parseFloat(form.previous) : undefined,
        importance: form.importance || undefined,
      };
      await eventsApi.addMacro(payload);
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
      const r = await eventsApi.getMacro(id);
      setSelected(r.data);
      setTab("detail");
    } catch {
      setSelected(null);
    }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15</div>
      <h1 style={{ margin: "0 0 20px", fontSize: 22 }}>Macro Events</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {["list","add","detail"].map((t) => (
          <button key={t} style={BTN(tab === t)} onClick={() => setTab(t)}>
            {t === "list" ? "Release List" : t === "add" ? "+ Add Release" : "Detail"}
          </button>
        ))}
      </div>

      {tab === "list" && (
        <>
          <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
            <select style={{ ...INPUT, width: 180 }} value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="">All types</option>
              {MACRO_TYPES.map((t) => <option key={t} value={t}>{t.toUpperCase().replace(/_/g, " ")}</option>)}
            </select>
            <input style={{ ...INPUT, width: 100 }} placeholder="Country" value={filterCountry}
              onChange={(e) => setFilterCountry(e.target.value)} />
          </div>
          {loading ? <div style={{ color: "#8b949e" }}>Loading…</div> : events.length === 0 ? (
            <div style={{ ...CARD, color: "#8b949e" }}>No macro events. Add one above.</div>
          ) : (
            <div style={CARD}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #30363d" }}>
                    {["Date","Type","Country","Actual","Forecast","Surprise%","Vol Exp","Importance"].map((h) => (
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
                      <td style={{ padding: "6px 8px", fontWeight: 700, color: "#e3b341" }}>{ev.event_type.toUpperCase().replace(/_/g," ")}</td>
                      <td style={{ padding: "6px 8px", color: "#c9d1d9" }}>{ev.country}</td>
                      <td style={{ padding: "6px 8px", color: "#f0f6fc" }}>{ev.actual ?? "—"}</td>
                      <td style={{ padding: "6px 8px", color: "#8b949e" }}>{ev.forecast ?? "—"}</td>
                      <td style={{ padding: "6px 8px", color: SURPRISE_COLOR(ev.surprise_pct) }}>
                        {ev.surprise_pct != null ? `${ev.surprise_pct > 0 ? "+" : ""}${ev.surprise_pct.toFixed(2)}%` : "—"}
                      </td>
                      <td style={{ padding: "6px 8px", color: "#58a6ff" }}>
                        {ev.volatility_expectation != null ? `${(ev.volatility_expectation * 100).toFixed(0)}%` : "—"}
                      </td>
                      <td style={{ padding: "6px 8px" }}>
                        <span style={{ color: IMP_COLOR[ev.importance] || "#8b949e", fontSize: 11 }}>{ev.importance}</span>
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
        <div style={{ ...CARD, maxWidth: 560 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16, color: "#e3b341" }}>Add Macro Release</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Event Type</div>
              <select style={{ ...INPUT, width: "100%" }} value={form.event_type}
                onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value }))}>
                {MACRO_TYPES.map((t) => <option key={t} value={t}>{t.toUpperCase().replace(/_/g," ")}</option>)}
              </select>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Country</div>
              <input style={{ ...INPUT, width: "100%" }} value={form.country}
                onChange={(e) => setForm((f) => ({ ...f, country: e.target.value }))} />
            </div>
            {[["Actual","actual"],["Forecast","forecast"],["Previous","previous"]].map(([l,k]) => (
              <div key={k}>
                <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>{l}</div>
                <input style={{ ...INPUT, width: "100%" }} type="number" step="any" value={form[k]}
                  onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))} />
              </div>
            ))}
            <div>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Importance (optional)</div>
              <select style={{ ...INPUT, width: "100%" }} value={form.importance}
                onChange={(e) => setForm((f) => ({ ...f, importance: e.target.value }))}>
                <option value="">Auto</option>
                {["critical","high","medium","low"].map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div style={{ gridColumn: "span 2" }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Description</div>
              <textarea style={{ ...INPUT, width: "100%", height: 72, resize: "vertical" }}
                value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
            </div>
          </div>
          <button style={{ ...BTN(true), marginTop: 16 }} disabled={submitting} onClick={submit}>
            {submitting ? "Adding…" : "Add Release"}
          </button>
        </div>
      )}

      {tab === "detail" && selected && (
        <div style={{ ...CARD, maxWidth: 560 }}>
          <div style={{ fontWeight: 700, fontSize: 16, color: "#e3b341", marginBottom: 16 }}>
            {selected.event_type.toUpperCase().replace(/_/g," ")} — {selected.country}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {[
              ["Actual", selected.actual ?? "N/A"],
              ["Forecast", selected.forecast ?? "N/A"],
              ["Previous", selected.previous ?? "N/A"],
              ["Surprise", selected.surprise ?? "N/A"],
              ["Surprise %", selected.surprise_pct != null ? `${selected.surprise_pct.toFixed(2)}%` : "N/A"],
              ["Historical Pct", selected.historical_percentile != null ? `${selected.historical_percentile.toFixed(1)}%` : "N/A"],
              ["Vol Expectation", selected.volatility_expectation != null ? `${(selected.volatility_expectation * 100).toFixed(1)}%` : "N/A"],
              ["Importance", selected.importance],
            ].map(([k, v]) => (
              <div key={k} style={{ fontSize: 12 }}>
                <div style={{ color: "#8b949e", fontSize: 11 }}>{k}</div>
                <div style={{ color: "#f0f6fc", fontWeight: 700 }}>{String(v)}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12, fontSize: 12, color: "#c9d1d9", lineHeight: 1.6 }}>{selected.description}</div>
        </div>
      )}
    </div>
  );
}
