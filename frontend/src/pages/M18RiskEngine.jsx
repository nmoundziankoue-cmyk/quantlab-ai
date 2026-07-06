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
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 12 },
  row: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box" },
  btn: (c="#58a6ff") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "7px 16px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginTop: 10 }),
  badge: (c) => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700 }),
  alert: { background: "#ff7b7211", border: "1px solid #ff7b7233", borderRadius: 6, padding: "8px 12px", marginBottom: 8, fontSize: 12, color: "#ff7b72" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
};

export default function M18RiskEngine() {
  const [dash, setDash] = useState(null);
  const [positions, setPositions] = useState({});
  const [form, setForm] = useState({ ticker: "AAPL", quantity: "100", market_price: "175.50", sector: "Technology", adv: "5000000", beta: "1.1" });
  const [nav, setNav] = useState("10000000");
  const [pnl, setPnl] = useState("5000");
  const [stressResult, setStressResult] = useState(null);
  const [varResult, setVarResult] = useState(null);
  const [msg, setMsg] = useState("");

  const refresh = () => {
    fetch("/m18/risk/dashboard").then(r => r.json()).then(setDash).catch(() => {});
    fetch("/m18/risk/positions").then(r => r.json()).then(setPositions).catch(() => {});
  };
  useEffect(() => { refresh(); const t = setInterval(refresh, 5000); return () => clearInterval(t); }, []);

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const updatePos = async () => {
    await post("/m18/risk/positions", { ...form, quantity: parseFloat(form.quantity), market_price: parseFloat(form.market_price), adv: parseFloat(form.adv), beta: parseFloat(form.beta) });
    setMsg(`Position updated: ${form.ticker}`); refresh();
  };
  const setNavFn = async () => { await post("/m18/risk/nav", { nav: parseFloat(nav) }); setMsg("NAV set"); refresh(); };
  const addPnl = async () => { await post("/m18/risk/pnl", { pnl: parseFloat(pnl) }); setMsg("P&L recorded"); };
  const computeVar = async () => {
    const r = await post("/m18/risk/var", { confidence: 0.95, window: 252 });
    if (r.ok) { const d = await r.json(); setVarResult(d); } else { const d = await r.json(); setMsg(formatApiError(d.detail)); }
  };
  const runStress = async () => {
    const r = await post("/m18/risk/stress-test", { scenario_name: "EQUITY_CRASH_20PCT", shock_pct: -0.20 });
    if (r.ok) { const d = await r.json(); setStressResult(d); }
  };

  const posArray = Object.values(positions);

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Real-Time Risk Engine</div>
      {msg && <div style={{ ...S.alert, marginBottom: 14 }}>{msg}</div>}

      <div style={S.grid4}>
        {[
          { label: "NAV", val: dash ? `$${dash.nav?.toLocaleString() ?? "—"}` : "—" },
          { label: "VaR 95%", val: dash ? (dash.var_95 != null ? `${(dash.var_95 * 100).toFixed(3)}%` : "—") : "—" },
          { label: "Gross Leverage", val: dash ? (dash.gross_leverage != null ? `${dash.gross_leverage.toFixed(2)}x` : "—") : "—" },
          { label: "Margin Usage", val: dash ? (dash.margin_usage_pct != null ? `${(dash.margin_usage_pct * 100).toFixed(1)}%` : "—") : "—" },
        ].map(k => <div key={k.label} style={S.card}><div style={S.label}>{k.label}</div><div style={S.val}>{k.val}</div></div>)}
      </div>

      {dash?.active_alerts?.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          {dash.active_alerts.map(a => <div key={a.alert_id} style={S.alert}>{a.message}</div>)}
        </div>
      )}

      <div style={S.row}>
        <div style={S.section}>
          <div style={S.sHdr}>Update Position</div>
          {["ticker","quantity","market_price","sector","adv","beta"].map(f => (
            <div key={f} style={{ marginBottom: 8 }}>
              <div style={{ ...S.label, marginBottom: 3 }}>{f}</div>
              <input style={S.input} value={form[f]} onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))} />
            </div>
          ))}
          <button style={S.btn()} onClick={updatePos}>Update Position</button>
        </div>

        <div>
          <div style={{ ...S.section, marginBottom: 14 }}>
            <div style={S.sHdr}>Set NAV</div>
            <input style={S.input} value={nav} onChange={e => setNav(e.target.value)} placeholder="NAV in USD" />
            <button style={S.btn()} onClick={setNavFn}>Set NAV</button>
          </div>
          <div style={{ ...S.section, marginBottom: 14 }}>
            <div style={S.sHdr}>Add P&L Observation</div>
            <input style={S.input} value={pnl} onChange={e => setPnl(e.target.value)} placeholder="Daily P&L USD" />
            <button style={S.btn("#3fb950")} onClick={addPnl}>Add P&L</button>
          </div>
          <div style={S.section}>
            <div style={S.sHdr}>Analytics</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button style={S.btn()} onClick={computeVar}>Compute VaR</button>
              <button style={S.btn("#ff7b72")} onClick={runStress}>Stress Test −20%</button>
            </div>
            {varResult && <div style={{ marginTop: 10, fontSize: 12, color: "#c9d1d9" }}>VaR: <b style={{ color: "#ff7b72" }}>${varResult.var_usd != null ? varResult.var_usd.toFixed(2) : "—"}</b> ({varResult.var_pct != null ? (varResult.var_pct * 100).toFixed(3) : "—"}%)</div>}
            {stressResult && <div style={{ marginTop: 8, fontSize: 12, color: "#c9d1d9" }}>{stressResult.scenario_name}: <b style={{ color: "#ff7b72" }}>${stressResult.pnl_impact_usd != null ? stressResult.pnl_impact_usd.toFixed(2) : "—"}</b> ({stressResult.pnl_impact_pct != null ? (stressResult.pnl_impact_pct * 100).toFixed(2) : "—"}%)</div>}
          </div>
        </div>
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Positions ({posArray.length})</div>
        {posArray.length === 0 ? <div style={{ color: "#8b949e", fontSize: 12 }}>No positions loaded.</div> : (
          <table style={S.table}>
            <thead><tr>{["Ticker","Qty","Price","Market Value","Sector","Beta"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {posArray.map(p => (
                <tr key={p.ticker}>
                  <td style={{ ...S.td, color: "#58a6ff" }}>{p.ticker}</td>
                  <td style={S.td}>{p.quantity}</td>
                  <td style={S.td}>{p.market_price != null ? `$${p.market_price.toFixed(2)}` : "—"}</td>
                  <td style={S.td}>{p.market_value != null ? `$${p.market_value.toLocaleString()}` : "—"}</td>
                  <td style={S.td}>{p.sector ?? "—"}</td>
                  <td style={S.td}>{p.beta != null ? p.beta.toFixed(2) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {dash?.sector_exposure && Object.keys(dash.sector_exposure).length > 0 && (
        <div style={S.section}>
          <div style={S.sHdr}>Sector Exposure</div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {Object.entries(dash.sector_exposure).map(([s, w]) => (
              <div key={s} style={{ background: "#161b22", borderRadius: 6, padding: "6px 12px" }}>
                <span style={{ fontSize: 11, color: "#8b949e" }}>{s}: </span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "#f0f6fc" }}>{(w * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
