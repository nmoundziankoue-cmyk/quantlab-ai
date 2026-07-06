import { useState } from "react";
import { formatApiError } from "../utils/formatApiError";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  row: { display: "flex", gap: 16, marginBottom: 16 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 14 },
  field: { marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", display: "block", marginBottom: 4, textTransform: "uppercase" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "7px 16px", cursor: "pointer", fontSize: 12, fontWeight: 700 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { fontSize: 11, color: "#8b949e", textAlign: "left", borderBottom: "1px solid #21262d", padding: "4px 8px" },
  td: { fontSize: 12, color: "#c9d1d9", padding: "6px 8px", borderBottom: "1px solid #161b22" },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  ok: { color: "#3fb950", fontSize: 12, marginTop: 8 },
  kv: { display:"flex", justifyContent:"space-between", fontSize:12, padding:"4px 0", borderBottom:"1px solid #21262d", color:"#c9d1d9" },
};

export default function M17Positions() {
  const [prices, setPrices] = useState("AAPL:175,MSFT:420,NVDA:890");
  const [positions, setPositions] = useState(null);
  const [exposure, setExposure] = useState(null);
  const [openForm, setOpenForm] = useState({ ticker:"AAPL", quantity:100, price:175 });
  const [closeForm, setCloseForm] = useState({ ticker:"AAPL", quantity:50, price:180 });
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);

  const parsePrices = () => {
    const p = {};
    prices.split(",").forEach(s => { const [t,v] = s.trim().split(":"); if(t && v) p[t.trim().toUpperCase()] = Number(v); });
    return p;
  };

  const loadPositions = async () => {
    const p = parsePrices();
    const r = await fetch("/trading/positions/all", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({prices:p}) });
    if (r.ok) setPositions(await r.json());
  };

  const loadExposure = async () => {
    const p = parsePrices();
    const nav = Object.values(p).reduce((a,b)=>a+b,0) * 100;
    const r = await fetch("/trading/positions/exposure", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({prices:p,nav}) });
    if (r.ok) setExposure(await r.json());
  };

  const openPos = async () => {
    setMsg(null); setErr(null);
    const r = await fetch("/trading/positions/open", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({...openForm, quantity:Number(openForm.quantity), price:Number(openForm.price)}) });
    if (r.ok) { setMsg("Position opened"); loadPositions(); }
    else { const d = await r.json(); setErr(formatApiError(d.detail)); }
  };

  const closePos = async () => {
    setMsg(null); setErr(null);
    const r = await fetch("/trading/positions/close", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({...closeForm, quantity:Number(closeForm.quantity), price:Number(closeForm.price)}) });
    if (r.ok) { const d = await r.json(); setMsg(`Closed — Realised P&L: $${d.realised_pnl}`); loadPositions(); }
    else { const d = await r.json(); setErr(formatApiError(d.detail)); }
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Position Engine</div>

      <div style={{ ...S.card, marginBottom:16 }}>
        <div style={S.sHdr}>Market Prices (ticker:price, comma-separated)</div>
        <div style={{ display:"flex", gap:8 }}>
          <input style={{ ...S.input, flex:1 }} value={prices} onChange={e=>setPrices(e.target.value)} />
          <button style={S.btn} onClick={() => { loadPositions(); loadExposure(); }}>Load</button>
        </div>
      </div>

      <div style={S.row}>
        <div style={{ flex:"0 0 260px" }}>
          <div style={{ ...S.card, marginBottom:16 }}>
            <div style={S.sHdr}>Open Lot (BUY)</div>
            {[["ticker","Ticker"],["quantity","Qty"],["price","Price"]].map(([k,l]) => (
              <div key={k} style={S.field}><label style={S.label}>{l}</label>
                <input style={S.input} type={k==="ticker"?"text":"number"} value={openForm[k]} onChange={e=>setOpenForm(p=>({...p,[k]:e.target.value}))} />
              </div>
            ))}
            <button style={S.btn} onClick={openPos}>Open Position</button>
          </div>
          <div style={S.card}>
            <div style={S.sHdr}>Close Lot (SELL)</div>
            {[["ticker","Ticker"],["quantity","Qty"],["price","Price"]].map(([k,l]) => (
              <div key={k} style={S.field}><label style={S.label}>{l}</label>
                <input style={S.input} type={k==="ticker"?"text":"number"} value={closeForm[k]} onChange={e=>setCloseForm(p=>({...p,[k]:e.target.value}))} />
              </div>
            ))}
            <button style={S.btn} onClick={closePos}>Close Position</button>
          </div>
          {msg && <div style={{...S.ok, marginTop:8}}>{msg}</div>}
          {err && <div style={{...S.err, marginTop:8}}>{err}</div>}
        </div>

        <div style={{ flex:1 }}>
          {positions && (
            <div style={{ ...S.card, marginBottom:16 }}>
              <div style={S.sHdr}>Open Positions ({positions.count})</div>
              <table style={S.table}>
                <thead><tr>{["Ticker","Side","Qty","Avg Cost","Mkt Price","Unreal P&L","Mkt Value","Lots","Days"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
                <tbody>
                  {positions.positions?.map(p => (
                    <tr key={p.ticker}>
                      <td style={{...S.td,fontWeight:700,color:"#f0f6fc"}}>{p.ticker}</td>
                      <td style={{...S.td,color:p.side==="LONG"?"#3fb950":"#ff7b72"}}>{p.side}</td>
                      <td style={S.td}>{p.quantity.toLocaleString()}</td>
                      <td style={S.td}>${p.avg_cost.toFixed(2)}</td>
                      <td style={S.td}>${p.market_price.toFixed(2)}</td>
                      <td style={{...S.td,color:p.unrealised_pnl>=0?"#3fb950":"#ff7b72"}}>${p.unrealised_pnl.toFixed(2)}</td>
                      <td style={S.td}>${p.market_value.toFixed(2)}</td>
                      <td style={S.td}>{p.open_lots}</td>
                      <td style={S.td}>{p.holding_days}d</td>
                    </tr>
                  ))}
                  {(!positions.positions || positions.positions.length === 0) && <tr><td colSpan={9} style={{...S.td,textAlign:"center",color:"#8b949e"}}>No positions</td></tr>}
                </tbody>
              </table>
            </div>
          )}
          {exposure && (
            <div style={S.card}>
              <div style={S.sHdr}>Exposure Report</div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
                {[["Gross Exposure",`$${exposure.gross_exposure?.toFixed(0)}`],["Net Exposure",`$${exposure.net_exposure?.toFixed(0)}`],["Leverage",`${exposure.leverage?.toFixed(2)}x`],["Net Leverage",`${exposure.net_leverage?.toFixed(2)}x`],["Long MV",`$${exposure.long_exposure?.toFixed(0)}`],["Short MV",`$${exposure.short_exposure?.toFixed(0)}`]].map(([k,v])=>(
                  <div key={k} style={S.kv}><span style={{color:"#8b949e"}}>{k}</span><span>{v}</span></div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
