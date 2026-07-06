import { useState, useEffect } from "react";
import { formatApiError } from "../utils/formatApiError";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 20 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "14px 18px" },
  label: { fontSize: 11, color: "#8b949e", textTransform: "uppercase", marginBottom: 4 },
  val: { fontSize: 18, fontWeight: 700, color: "#f0f6fc" },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#ffa657", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c="#ffa657") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  badge: (sev) => {
    const c = { CRITICAL: "#ff7b72", HIGH: "#ff7b72", MEDIUM: "#e3b341", LOW: "#8b949e", INFO: "#58a6ff" }[sev] || "#8b949e";
    return { display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700 };
  },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
};

export default function M18AlertCenter() {
  const [stats, setStats] = useState(null);
  const [rules, setRules] = useState([]);
  const [history, setHistory] = useState([]);
  const [form, setForm] = useState({ name: "AAPL Price Alert", alert_type: "PRICE", severity: "HIGH", field: "price", direction: "ABOVE", threshold: "180", ticker: "AAPL" });
  const [evalForm, setEvalForm] = useState({ ticker: "AAPL", field: "price", value: "185" });
  const [fireResult, setFireResult] = useState([]);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const refresh = (isInitial = false) => {
    if (isInitial) setLoading(true);
    Promise.all([
      fetch("/m18/alerts/stats").then(r => r.json()).then(setStats).catch(() => {}),
      fetch("/m18/alerts/rules").then(r => r.json()).then(d => setRules(Array.isArray(d) ? d : [])).catch(() => {}),
      fetch("/m18/alerts/history?limit=30").then(r => r.json()).then(d => setHistory(Array.isArray(d) ? d : [])).catch(() => {}),
    ]).then(() => { setLoading(false); setError(null); }).catch(() => { setError("Unable to connect to the backend"); setLoading(false); });
  };
  useEffect(() => { refresh(true); const t = setInterval(() => refresh(false), 5000); return () => clearInterval(t); }, []);

  const addRule = async () => {
    const r = await post("/m18/alerts/rules", { ...form, threshold: parseFloat(form.threshold) });
    if (r.ok) { setMsg("Rule added"); refresh(); } else { const d = await r.json(); setMsg(formatApiError(d.detail)); }
  };
  const deleteRule = async (id) => { await fetch(`/m18/alerts/rules/${id}`, { method: "DELETE" }); refresh(); };
  const evalAlert = async () => {
    const r = await post("/m18/alerts/evaluate", { ...evalForm, value: parseFloat(evalForm.value) });
    if (r.ok) { const d = await r.json(); setFireResult(d); refresh(); } else setFireResult([]);
  };

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 300, color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
      Loading…
    </div>
  );

  if (error && !stats && rules.length === 0) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, gap: 12 }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--negative)", letterSpacing: "0.1em" }}>ERROR</div>
      <div style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-3)" }}>Unable to connect to the backend</div>
      <button onClick={() => refresh(true)} style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)", background: "var(--accent)22", border: "1px solid var(--accent)55", borderRadius: 6, padding: "6px 16px", cursor: "pointer" }}>Retry</button>
    </div>
  );

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Institutional Alert Center</div>

      <div style={S.grid4}>
        {[
          { label: "Total Rules", val: stats?.total_rules ?? "—" },
          { label: "Active Rules", val: stats?.active_rules ?? "—" },
          { label: "Total Triggers", val: stats?.total_triggers ?? "—" },
          { label: "Last Hour", val: stats?.triggers_last_hour ?? "—" },
        ].map(k => <div key={k.label} style={S.card}><div style={S.label}>{k.label}</div><div style={S.val}>{k.val}</div></div>)}
      </div>

      <div style={S.row2}>
        <div style={S.section}>
          <div style={S.sHdr}>Add Alert Rule</div>
          {[["name","Rule Name"],["alert_type","Type (PRICE/VOLUME/RSI_OVERBOUGHT)"],["severity","Severity (HIGH/MEDIUM/LOW)"],["field","Field (price/volume/rsi)"],["direction","Direction (ABOVE/BELOW)"],["threshold","Threshold"],["ticker","Ticker (optional)"]].map(([f, label]) => (
            <div key={f}>
              <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{label}</div>
              <input style={S.input} value={form[f]} onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))} />
            </div>
          ))}
          <button style={S.btn()} onClick={addRule}>Add Rule</button>
          {msg && <div style={{ fontSize: 11, color: "#8b949e", marginTop: 6 }}>{msg}</div>}
        </div>

        <div style={S.section}>
          <div style={S.sHdr}>Evaluate Market Data</div>
          {[["ticker","Ticker"],["field","Field"],["value","Value"]].map(([f, l]) => (
            <div key={f}>
              <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{l}</div>
              <input style={S.input} value={evalForm[f]} onChange={e => setEvalForm(p => ({ ...p, [f]: e.target.value }))} />
            </div>
          ))}
          <button style={S.btn()} onClick={evalAlert}>Evaluate</button>
          {fireResult.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 11, color: "#3fb950", marginBottom: 6 }}>{fireResult.length} alert(s) fired:</div>
              {fireResult.map(a => <div key={a.alert_id} style={{ fontSize: 11, color: "#c9d1d9", marginBottom: 4 }}>• {a.message}</div>)}
            </div>
          )}
        </div>
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Active Rules ({rules.length})</div>
        {rules.length === 0 ? <div style={{ color: "#8b949e", fontSize: 12 }}>No rules configured.</div> : (
          <table style={S.table}>
            <thead><tr>{["Name","Type","Field","Direction","Threshold","Ticker","Severity",""].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {rules.map(r => (
                <tr key={r.rule_id}>
                  <td style={{ ...S.td, color: "#f0f6fc" }}>{r.name}</td>
                  <td style={S.td}>{r.alert_type}</td>
                  <td style={S.td}>{r.field}</td>
                  <td style={S.td}>{r.direction}</td>
                  <td style={{ ...S.td, color: "#ffa657" }}>{r.threshold}</td>
                  <td style={S.td}>{r.ticker || "—"}</td>
                  <td style={S.td}><span style={S.badge(r.severity)}>{r.severity}</span></td>
                  <td style={S.td}><button onClick={() => deleteRule(r.rule_id)} style={{ background: "none", border: "none", color: "#ff7b72", cursor: "pointer", fontSize: 11 }}>✕</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Alert History</div>
        {history.length === 0 ? <div style={{ color: "#8b949e", fontSize: 12 }}>No alerts triggered yet.</div> : (
          <table style={S.table}>
            <thead><tr>{["Time","Ticker","Type","Severity","Message"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {history.map(a => (
                <tr key={a.alert_id}>
                  <td style={{ ...S.td, color: "#8b949e" }}>{a.timestamp?.slice(11,19)}</td>
                  <td style={{ ...S.td, color: "#58a6ff" }}>{a.ticker || "—"}</td>
                  <td style={S.td}>{a.alert_type}</td>
                  <td style={S.td}><span style={S.badge(a.severity)}>{a.severity}</span></td>
                  <td style={{ ...S.td, fontSize: 10 }}>{a.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
