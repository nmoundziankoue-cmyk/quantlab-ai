import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#79c0ff", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c="#79c0ff") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  badge: (dir) => {
    const c = { BEAT: "#3fb950", MISS: "#ff7b72", IN_LINE: "#8b949e" }[dir] || "#8b949e";
    return { display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700 };
  },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
  kv: { display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #21262d33", fontSize: 12 },
};

const INDICATOR_TYPES = ["GDP","INFLATION","UNEMPLOYMENT","INTEREST_RATE","PMI","CONSUMER_CONFIDENCE","RETAIL_SALES","LEADING"];

export default function M18EconomicIntel() {
  const [indicators, setIndicators] = useState([]);
  const [recession, setRecession] = useState(null);
  const [inflation, setInflation] = useState(null);
  const [cycle, setCycle] = useState(null);
  const [country, setCountry] = useState("US");
  const [indForm, setIndForm] = useState({ name: "US GDP", country: "US", indicator_type: "GDP", value: "2.8", previous_value: "2.1", forecast: "2.5", unit: "% QoQ annualised", frequency: "Quarterly" });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const refresh = () => {
    setLoading(true);
    fetch(`/m18/economic/indicators?country=${country}`)
      .then(r => r.json())
      .then(d => { setIndicators(Array.isArray(d) ? d : []); setLoading(false); setError(null); })
      .catch(() => { setError("Unable to connect to the backend"); setLoading(false); });
  };
  useEffect(() => { refresh(); }, [country]);

  const recordIndicator = async () => {
    await post("/m18/economic/indicators", { ...indForm, value: parseFloat(indForm.value), previous_value: parseFloat(indForm.previous_value), forecast: parseFloat(indForm.forecast) });
    refresh();
  };

  const fetchAnalytics = async () => {
    fetch(`/m18/economic/recession-probability/${country}`).then(r => r.json()).then(setRecession).catch(() => {});
    fetch(`/m18/economic/inflation-forecast/${country}`).then(r => r.json()).then(setInflation).catch(() => {});
    fetch(`/m18/economic/business-cycle/${country}`).then(r => r.json()).then(setCycle).catch(() => {});
  };

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 300, color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
      Loading…
    </div>
  );

  if (error && indicators.length === 0) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, gap: 12 }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--negative)", letterSpacing: "0.1em" }}>ERROR</div>
      <div style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-3)" }}>Unable to connect to the backend</div>
      <button onClick={refresh} style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)", background: "var(--accent)22", border: "1px solid var(--accent)55", borderRadius: 6, padding: "6px 16px", cursor: "pointer" }}>Retry</button>
    </div>
  );

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Economic Intelligence</div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center" }}>
        <input style={{ ...S.input, width: 100, marginBottom: 0 }} value={country} onChange={e => setCountry(e.target.value.toUpperCase())} placeholder="Country (US/GB/EU)" />
        <button style={S.btn()} onClick={refresh}>Load Indicators</button>
        <button style={S.btn("#a371f7")} onClick={fetchAnalytics}>Run Analytics</button>
      </div>

      <div style={S.row2}>
        <div style={S.section}>
          <div style={S.sHdr}>Record Indicator</div>
          {[["name","Indicator Name"],["country","Country"],["indicator_type","Type"],["value","Value"],["previous_value","Previous"],["forecast","Forecast"],["unit","Unit"],["frequency","Frequency"]].map(([f, l]) => (
            <div key={f}>
              <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{l}</div>
              {f === "indicator_type" ? (
                <select style={{ ...S.input, marginBottom: 6 }} value={indForm[f]} onChange={e => setIndForm(p => ({ ...p, [f]: e.target.value }))}>
                  {INDICATOR_TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              ) : (
                <input style={S.input} value={indForm[f]} onChange={e => setIndForm(p => ({ ...p, [f]: e.target.value }))} />
              )}
            </div>
          ))}
          <button style={S.btn()} onClick={recordIndicator}>Record</button>
        </div>

        <div>
          {recession && (
            <div style={{ ...S.section, marginBottom: 14 }}>
              <div style={S.sHdr}>Recession Probability — {recession.country}</div>
              {[["12-Month Prob", `${(recession.probability_12m * 100).toFixed(1)}%`], ["24-Month Prob", `${(recession.probability_24m * 100).toFixed(1)}%`], ["Model", recession.model]].map(([k, v]) => (
                <div key={k} style={S.kv}><span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: recession.probability_12m > 0.4 ? "#ff7b72" : "#3fb950" }}>{v}</span></div>
              ))}
            </div>
          )}
          {inflation && (
            <div style={{ ...S.section, marginBottom: 14 }}>
              <div style={S.sHdr}>Inflation Forecast — {inflation.country}</div>
              {[["Current CPI", `${(inflation.current_cpi_yoy * 100).toFixed(2)}%`], ["3M Forecast", `${(inflation.forecast_3m * 100).toFixed(2)}%`], ["6M Forecast", `${(inflation.forecast_6m * 100).toFixed(2)}%`], ["12M Forecast", `${(inflation.forecast_12m * 100).toFixed(2)}%`], ["Trend", inflation.trend]].map(([k, v]) => (
                <div key={k} style={S.kv}><span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: "#79c0ff" }}>{v}</span></div>
              ))}
            </div>
          )}
          {cycle && (
            <div style={S.section}>
              <div style={S.sHdr}>Business Cycle — {cycle.country}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 8 }}>{cycle.phase}</div>
              {[["Confidence", `${(cycle.confidence * 100).toFixed(0)}%`], ["Leading Score", cycle.leading_indicators_score?.toFixed(3)], ["Coincident Score", cycle.coincident_indicators_score?.toFixed(3)]].map(([k, v]) => (
                <div key={k} style={S.kv}><span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: "#f0f6fc" }}>{v}</span></div>
              ))}
              <div style={{ fontSize: 11, color: "#8b949e", marginTop: 8 }}>{cycle.notes}</div>
            </div>
          )}
        </div>
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Indicators — {country} ({indicators.length})</div>
        {indicators.length === 0 ? <div style={{ color: "#8b949e", fontSize: 12 }}>No indicators recorded. Add one above.</div> : (
          <table style={S.table}>
            <thead><tr>{["Indicator","Type","Value","Previous","Forecast","Surprise","Direction","Frequency"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {indicators.map(ind => (
                <tr key={ind.indicator_id}>
                  <td style={{ ...S.td, color: "#79c0ff" }}>{ind.name}</td>
                  <td style={S.td}>{ind.indicator_type}</td>
                  <td style={{ ...S.td, color: "#f0f6fc", fontWeight: 700 }}>{ind.value}</td>
                  <td style={S.td}>{ind.previous_value}</td>
                  <td style={S.td}>{ind.forecast}</td>
                  <td style={{ ...S.td, color: ind.surprise >= 0 ? "#3fb950" : "#ff7b72" }}>{ind.surprise?.toFixed(3)}</td>
                  <td style={S.td}><span style={S.badge(ind.surprise_direction)}>{ind.surprise_direction}</span></td>
                  <td style={S.td}>{ind.frequency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
