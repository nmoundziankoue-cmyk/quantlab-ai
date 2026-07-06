import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  row: { display: "flex", gap: 16 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 14 },
  field: { marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", display: "block", marginBottom: 4, textTransform: "uppercase" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  select: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "7px 16px", cursor: "pointer", fontSize: 12, fontWeight: 700 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { fontSize: 11, color: "#8b949e", textAlign: "left", borderBottom: "1px solid #21262d", padding: "4px 8px" },
  td: { fontSize: 12, color: "#c9d1d9", padding: "6px 8px", borderBottom: "1px solid #161b22" },
  badge: (c) => ({ display:"inline-block", fontSize:10, padding:"2px 6px", borderRadius:4, background:c+"22", color:c, fontWeight:700 }),
  result: { marginTop: 16, borderRadius: 6, padding: 14, border: "1px solid #21262d", background: "#161b22" },
};

const LIMIT_TYPES = ["MAX_POSITION_SIZE","MAX_ORDER_SIZE","MAX_SECTOR_WEIGHT","MAX_COUNTRY_WEIGHT","MAX_LEVERAGE","MAX_GROSS_LEVERAGE","MAX_NET_LEVERAGE","MAX_DRAWDOWN","MAX_TURNOVER_DAILY","MAX_BETA","MAX_VAR","MAX_CONCENTRATION"];

export default function M17RiskLimits() {
  const [limits, setLimits] = useState([]);
  const [addForm, setAddForm] = useState({ limit_type:"MAX_POSITION_SIZE", hard_limit:1000000, soft_limit:800000, description:"" });
  const [checkForm, setCheckForm] = useState({ ticker:"AAPL", side:"BUY", quantity:1000, price:175, nav:1000000, sector:"TECHNOLOGY", gross_leverage:1.0 });
  const [checkResult, setCheckResult] = useState(null);
  const [msg, setMsg] = useState(null);

  const loadLimits = () => fetch("/trading/risk/limits").then(r => r.ok ? r.json() : Promise.reject()).then(d=>setLimits(d.limits||[])).catch(()=>{});
  useEffect(() => { loadLimits(); }, []);

  const addLimit = async () => {
    const r = await fetch("/trading/risk/limits/add", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({...addForm, hard_limit:Number(addForm.hard_limit), soft_limit:Number(addForm.soft_limit)}) });
    if (r.ok) { setMsg("Limit added"); loadLimits(); }
  };

  const removeLimit = async (id) => {
    await fetch(`/trading/risk/limits/${id}`, { method:"DELETE" });
    loadLimits();
  };

  const checkOrder = async () => {
    const body = { ...checkForm, quantity:Number(checkForm.quantity), price:Number(checkForm.price), nav:Number(checkForm.nav), gross_leverage:Number(checkForm.gross_leverage), cash:Number(checkForm.nav)*0.1, sector_weights:{"TECHNOLOGY":0.25} };
    const r = await fetch("/trading/risk/check", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    if (r.ok) setCheckResult(await r.json());
  };

  const RESULT_COLORS = { PASS:"#3fb950", SOFT_WARNING:"#e3b341", HARD_REJECT:"#ff7b72" };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Risk Limits Engine</div>
      <div style={S.row}>
        <div style={{ flex:"0 0 300px" }}>
          <div style={S.card}>
            <div style={S.sHdr}>Add Limit</div>
            <div style={S.field}><label style={S.label}>Limit Type</label>
              <select style={S.select} value={addForm.limit_type} onChange={e=>setAddForm(p=>({...p,limit_type:e.target.value}))}>
                {LIMIT_TYPES.map(t=><option key={t}>{t}</option>)}
              </select>
            </div>
            {[["hard_limit","Hard Limit"],["soft_limit","Soft Limit"]].map(([k,l])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label>
                <input style={S.input} type="number" value={addForm[k]} onChange={e=>setAddForm(p=>({...p,[k]:e.target.value}))} />
              </div>
            ))}
            <div style={S.field}><label style={S.label}>Description</label>
              <input style={S.input} value={addForm.description} onChange={e=>setAddForm(p=>({...p,description:e.target.value}))} />
            </div>
            <button style={S.btn} onClick={addLimit}>Add Limit</button>
            {msg && <div style={{ color:"#3fb950", fontSize:12, marginTop:8 }}>{msg}</div>}
          </div>
          <div style={S.card}>
            <div style={S.sHdr}>Pre-Trade Check</div>
            {[["ticker","Ticker","text"],["side","Side","text"],["quantity","Qty","number"],["price","Price","number"],["nav","NAV","number"],["gross_leverage","Leverage","number"]].map(([k,l,t])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label>
                <input style={S.input} type={t} value={checkForm[k]} onChange={e=>setCheckForm(p=>({...p,[k]:e.target.value}))} />
              </div>
            ))}
            <button style={S.btn} onClick={checkOrder}>Check Order</button>
            {checkResult && (
              <div style={{ ...S.result, borderColor: RESULT_COLORS[checkResult.result] }}>
                <div style={{ fontSize:14, fontWeight:700, color:RESULT_COLORS[checkResult.result], marginBottom:8 }}>{checkResult.result}</div>
                <div style={{ fontSize:12, color:"#8b949e" }}>Order Allowed: {checkResult.order_allowed ? "✓ Yes" : "✗ No"}</div>
                {checkResult.violations?.map((v,i)=>(
                  <div key={i} style={{ fontSize:11, color:v.result==="HARD_REJECT"?"#ff7b72":"#e3b341", marginTop:4 }}>• {v.message}</div>
                ))}
              </div>
            )}
          </div>
        </div>
        <div style={{ flex:1 }}>
          <div style={S.card}>
            <div style={{ ...S.sHdr, display:"flex", justifyContent:"space-between" }}>
              Active Limits ({limits.length})
              <button style={{ ...S.btn, padding:"4px 10px", fontSize:11, background:"#21262d" }} onClick={loadLimits}>Refresh</button>
            </div>
            <table style={S.table}>
              <thead><tr>{["Type","Hard Limit","Soft Limit","Description",""].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
              <tbody>
                {limits.map(l=>(
                  <tr key={l.limit_id}>
                    <td style={{ ...S.td, color:"#58a6ff" }}>{l.limit_type}</td>
                    <td style={S.td}>{l.hard_limit?.toLocaleString()}</td>
                    <td style={S.td}>{l.soft_limit?.toLocaleString()}</td>
                    <td style={S.td}>{l.description}</td>
                    <td style={S.td}><button style={{ background:"#da3633", color:"#fff", border:"none", borderRadius:4, padding:"2px 8px", cursor:"pointer", fontSize:11 }} onClick={()=>removeLimit(l.limit_id)}>Remove</button></td>
                  </tr>
                ))}
                {limits.length===0 && <tr><td colSpan={5} style={{...S.td,textAlign:"center",color:"#8b949e"}}>No limits configured</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
