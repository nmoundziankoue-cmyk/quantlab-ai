import { useState, useEffect } from "react";
import { formatApiError } from "../utils/formatApiError";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  row: { display: "flex", gap: 16 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 14 },
  field: { marginBottom: 10 },
  label: { fontSize: 11, color: "#8b949e", display: "block", marginBottom: 4, textTransform: "uppercase" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "7px 16px", cursor: "pointer", fontSize: 12, fontWeight: 700 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { fontSize: 11, color: "#8b949e", textAlign: "left", borderBottom: "1px solid #21262d", padding: "4px 8px" },
  td: { fontSize: 12, color: "#c9d1d9", padding: "6px 8px", borderBottom: "1px solid #161b22" },
  badge: (c) => ({ display:"inline-block", fontSize:10, padding:"2px 6px", borderRadius:4, background:c+"22", color:c, fontWeight:700 }),
  ok: { color: "#3fb950", fontSize: 12, marginTop: 8 },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
};

const SCORE_COLOR = (s) => s>=80?"#3fb950":s>=60?"#e3b341":"#ff7b72";

export default function M17BrokerDashboard() {
  const [brokers, setBrokers] = useState([]);
  const [stats, setStats] = useState(null);
  const [regForm, setRegForm] = useState({ name: "Goldman Sachs Prime", supported_asset_classes: "EQUITY,OPTIONS", supported_exchanges: "NYSE,NASDAQ" });
  const [commForm, setCommForm] = useState({ broker_id:"", asset_class:"EQUITY", commission_type:"PER_SHARE", base_rate:0.005, minimum_per_trade:1.0 });
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);

  const load = () => {
    fetch("/trading/brokers").then(r=>r.json()).then(d=>setBrokers(d.brokers||[]));
    fetch("/trading/brokers/statistics").then(r=>r.json()).then(setStats);
  };
  useEffect(() => { load(); }, []);

  const register = async () => {
    setMsg(null); setErr(null);
    const body = { name: regForm.name, supported_asset_classes: regForm.supported_asset_classes.split(",").map(s=>s.trim()), supported_exchanges: regForm.supported_exchanges.split(",").map(s=>s.trim()) };
    const r = await fetch("/trading/brokers/register", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    if (r.ok) { setMsg("Broker registered"); load(); }
    else { const d = await r.json(); setErr(formatApiError(d.detail)); }
  };

  const addCommission = async () => {
    const body = { ...commForm, base_rate: Number(commForm.base_rate), minimum_per_trade: Number(commForm.minimum_per_trade) };
    const r = await fetch("/trading/brokers/commission/add", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    if (r.ok) { setMsg("Commission schedule added"); load(); }
    else { const d = await r.json(); setErr(formatApiError(d.detail)); }
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Broker Management</div>

      {stats && (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:16 }}>
          {[["Total Brokers", stats.total],["Active", stats.by_status?.ACTIVE||0],["Avg Quality Score", stats.avg_quality_score?.toFixed(1)]].map(([l,v])=>(
            <div key={l} style={{ ...S.card, marginBottom:0 }}><div style={{ fontSize:11, color:"#8b949e", marginBottom:4 }}>{l}</div><div style={{ fontSize:20, fontWeight:700, color:"#f0f6fc" }}>{v}</div></div>
          ))}
        </div>
      )}

      <div style={S.row}>
        <div style={{ flex:"0 0 300px" }}>
          <div style={S.card}>
            <div style={S.sHdr}>Register Broker</div>
            <div style={S.field}><label style={S.label}>Name</label><input style={S.input} value={regForm.name} onChange={e=>setRegForm(p=>({...p,name:e.target.value}))} /></div>
            <div style={S.field}><label style={S.label}>Asset Classes (comma-sep)</label><input style={S.input} value={regForm.supported_asset_classes} onChange={e=>setRegForm(p=>({...p,supported_asset_classes:e.target.value}))} /></div>
            <div style={S.field}><label style={S.label}>Exchanges (comma-sep)</label><input style={S.input} value={regForm.supported_exchanges} onChange={e=>setRegForm(p=>({...p,supported_exchanges:e.target.value}))} /></div>
            <button style={S.btn} onClick={register}>Register</button>
            {msg && <div style={S.ok}>{msg}</div>}
            {err && <div style={S.err}>{err}</div>}
          </div>
          <div style={S.card}>
            <div style={S.sHdr}>Add Commission Schedule</div>
            <div style={S.field}><label style={S.label}>Broker ID</label><input style={S.input} value={commForm.broker_id} onChange={e=>setCommForm(p=>({...p,broker_id:e.target.value}))} placeholder="UUID" /></div>
            {[["asset_class","Asset Class","EQUITY"],["commission_type","Type","PER_SHARE"],["base_rate","Base Rate","0.005"],["minimum_per_trade","Min Trade","1.0"]].map(([k,l,ph])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} value={commForm[k]} onChange={e=>setCommForm(p=>({...p,[k]:e.target.value}))} placeholder={ph} /></div>
            ))}
            <button style={S.btn} onClick={addCommission}>Add Schedule</button>
          </div>
        </div>

        <div style={{ flex:1 }}>
          <div style={S.card}>
            <div style={{ ...S.sHdr, display:"flex", justifyContent:"space-between" }}>
              Registered Brokers ({brokers.length})
              <button style={{ ...S.btn, background:"#21262d", padding:"4px 10px", fontSize:11 }} onClick={load}>Refresh</button>
            </div>
            <table style={S.table}>
              <thead><tr>{["Name","Status","Asset Classes","Quality Score","Schedules"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
              <tbody>
                {brokers.map(b=>(
                  <tr key={b.broker_id}>
                    <td style={{ ...S.td, fontWeight:700 }}>{b.name}</td>
                    <td style={S.td}><span style={S.badge(b.status==="ACTIVE"?"#3fb950":"#8b949e")}>{b.status}</span></td>
                    <td style={S.td}>{b.supported_asset_classes?.join(", ")}</td>
                    <td style={S.td}>
                      <span style={{ color: SCORE_COLOR(b.quality_score), fontWeight:700 }}>{b.quality_score?.toFixed(1)}</span>
                      <div style={{ background:"#21262d", borderRadius:4, height:4, width:80, marginTop:4 }}>
                        <div style={{ background:SCORE_COLOR(b.quality_score), height:"100%", width:`${b.quality_score}%`, borderRadius:4 }} />
                      </div>
                    </td>
                    <td style={S.td}>{b.commission_schedules?.length || 0} schedules</td>
                  </tr>
                ))}
                {brokers.length===0 && <tr><td colSpan={5} style={{...S.td,textAlign:"center",color:"#8b949e"}}>No brokers registered</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
