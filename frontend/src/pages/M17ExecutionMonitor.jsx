import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  row: { display: "flex", gap: 16 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 14 },
  field: { marginBottom: 10 },
  label: { fontSize: 11, color: "#8b949e", display: "block", marginBottom: 4, textTransform: "uppercase" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  select: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "7px 16px", cursor: "pointer", fontSize: 12, fontWeight: 700 },
  kv: { display:"flex", justifyContent:"space-between", fontSize:12, padding:"5px 0", borderBottom:"1px solid #21262d" },
  grid3: { display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10 },
  metric: { background:"#161b22", borderRadius:6, padding:"12px 14px" },
  mLabel: { fontSize:10, color:"#8b949e", textTransform:"uppercase", marginBottom:4 },
  mVal: { fontSize:18, fontWeight:700, color:"#f0f6fc" },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
};

export default function M17ExecutionMonitor() {
  const [slipForm, setSlipForm] = useState({ order_size:10000, adv:500000, price:175.0, volatility:0.02, model:"SQRT" });
  const [slipResult, setSlipResult] = useState(null);
  const [impactForm, setImpactForm] = useState({ order_size:10000, adv:500000, price:175.0, volatility:0.02, sigma_daily:0.015 });
  const [impactResult, setImpactResult] = useState(null);
  const [fillForm, setFillForm] = useState({ order_id:"ORD-001", ticker:"AAPL", side:"BUY", quantity:500, order_type:"MARKET", limit_price:"", market_price:175.0, bid:174.98, ask:175.02, adv:500000, volatility:0.02, commission_rate:0.005 });
  const [fillResult, setFillResult] = useState(null);
  const [qualForm, setQualForm] = useState({ order_id:"ORD-001", arrival_price:175.0, vwap:175.15, execution_price:175.35, quantity:500, adv:500000, commission:2.5 });
  const [qualResult, setQualResult] = useState(null);
  const [err, setErr] = useState(null);

  const post = async (url, body, setter) => {
    setErr(null);
    const r = await fetch(url, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    if (r.ok) setter(await r.json());
    else { const d = await r.json(); setErr(d.detail); }
  };

  const bps = v => v != null ? `${v.toFixed(2)} bps` : "—";
  const pct = v => v != null ? `${(v * 100).toFixed(3)}%` : "—";

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Execution Monitor</div>

      <div style={S.row}>
        <div style={{ flex:"0 0 320px" }}>
          <div style={S.card}>
            <div style={S.sHdr}>Slippage Estimate</div>
            {[["order_size","Order Size","number"],["adv","ADV","number"],["price","Price","number"],["volatility","Volatility (daily)","number"]].map(([k,l,t])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} type={t} step="any" value={slipForm[k]} onChange={e=>setSlipForm(p=>({...p,[k]:e.target.value}))} /></div>
            ))}
            <div style={S.field}><label style={S.label}>Model</label>
              <select style={S.select} value={slipForm.model} onChange={e=>setSlipForm(p=>({...p,model:e.target.value}))}>
                {["SQRT","LINEAR","VOLUME_ADJ","FIXED_BPS"].map(m=><option key={m}>{m}</option>)}
              </select>
            </div>
            <button style={S.btn} onClick={() => post("/trading/execution/slippage", { ...slipForm, order_size:Number(slipForm.order_size), adv:Number(slipForm.adv), price:Number(slipForm.price), volatility:Number(slipForm.volatility) }, setSlipResult)}>Estimate Slippage</button>
            {slipResult && (
              <div style={{ marginTop:12 }}>
                {[["Slippage %",pct(slipResult.slippage_pct)],["Slippage bps",bps(slipResult.slippage_bps)],["Cost $",`$${slipResult.slippage_cost?.toFixed(2)}`],["Model",slipResult.model]].map(([l,v])=>(
                  <div key={l} style={S.kv}><span style={{color:"#8b949e"}}>{l}</span><span style={{color:"#f0f6fc"}}>{v}</span></div>
                ))}
              </div>
            )}
          </div>

          <div style={S.card}>
            <div style={S.sHdr}>Market Impact</div>
            {[["order_size","Order Size","number"],["adv","ADV","number"],["price","Price","number"],["volatility","Volatility","number"],["sigma_daily","Daily Sigma","number"]].map(([k,l,t])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} type={t} step="any" value={impactForm[k]} onChange={e=>setImpactForm(p=>({...p,[k]:e.target.value}))} /></div>
            ))}
            <button style={S.btn} onClick={() => post("/trading/execution/market-impact", { ...impactForm, order_size:Number(impactForm.order_size), adv:Number(impactForm.adv), price:Number(impactForm.price), volatility:Number(impactForm.volatility), sigma_daily:Number(impactForm.sigma_daily) }, setImpactResult)}>Estimate Impact</button>
            {impactResult && (
              <div style={{ marginTop:12 }}>
                {[["Permanent",bps(impactResult.permanent_bps)],["Temporary",bps(impactResult.temporary_bps)],["Total",bps(impactResult.total_bps)],["Total $",`$${impactResult.total_cost?.toFixed(2)}`]].map(([l,v])=>(
                  <div key={l} style={S.kv}><span style={{color:"#8b949e"}}>{l}</span><span style={{color:"#f0f6fc"}}>{v}</span></div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div style={{ flex:1 }}>
          <div style={S.card}>
            <div style={S.sHdr}>Simulate Fill</div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
              {[["order_id","Order ID","text"],["ticker","Ticker","text"],["side","Side","text"],["quantity","Qty","number"],["order_type","Order Type","text"],["limit_price","Limit Price","number"],["market_price","Mkt Price","number"],["bid","Bid","number"],["ask","Ask","number"],["adv","ADV","number"],["volatility","Volatility","number"],["commission_rate","Comm Rate","number"]].map(([k,l,t])=>(
                <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} type={t} step="any" value={fillForm[k]} onChange={e=>setFillForm(p=>({...p,[k]:e.target.value}))} /></div>
              ))}
            </div>
            <button style={S.btn} onClick={() => post("/trading/execution/simulate-fill", { ...fillForm, quantity:Number(fillForm.quantity), limit_price:fillForm.limit_price?Number(fillForm.limit_price):null, market_price:Number(fillForm.market_price), bid:Number(fillForm.bid), ask:Number(fillForm.ask), adv:Number(fillForm.adv), volatility:Number(fillForm.volatility), commission_rate:Number(fillForm.commission_rate) }, setFillResult)}>Simulate</button>
            {fillResult && (
              <div style={{ ...S.grid3, marginTop:14 }}>
                {[["Fill Price",`$${fillResult.fill_price?.toFixed(4)}`],["Filled Qty",fillResult.filled_qty],["Commission",`$${fillResult.commission?.toFixed(2)}`],["Slippage bps",bps(fillResult.slippage_bps)],["Market Impact",bps(fillResult.market_impact_bps)],["POV",`${(fillResult.participation_rate*100)?.toFixed(2)}%`]].map(([l,v])=>(
                  <div key={l} style={S.metric}><div style={S.mLabel}>{l}</div><div style={S.mVal}>{v}</div></div>
                ))}
              </div>
            )}
          </div>

          <div style={S.card}>
            <div style={S.sHdr}>Execution Quality Score</div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:10 }}>
              {[["order_id","Order ID","text"],["arrival_price","Arrival Price","number"],["vwap","VWAP","number"],["execution_price","Exec Price","number"],["quantity","Quantity","number"],["adv","ADV","number"],["commission","Commission","number"]].map(([k,l,t])=>(
                <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} type={t} step="any" value={qualForm[k]} onChange={e=>setQualForm(p=>({...p,[k]:e.target.value}))} /></div>
              ))}
            </div>
            <button style={S.btn} onClick={() => post("/trading/execution/quality", { ...qualForm, arrival_price:Number(qualForm.arrival_price), vwap:Number(qualForm.vwap), execution_price:Number(qualForm.execution_price), quantity:Number(qualForm.quantity), adv:Number(qualForm.adv), commission:Number(qualForm.commission) }, setQualResult)}>Score</button>
            {qualResult && (
              <div style={{ ...S.grid3, marginTop:14 }}>
                {[["Quality Score",qualResult.quality_score?.toFixed(1)],["Arrival Slip",bps(qualResult.arrival_slippage_bps)],["vs VWAP",bps(qualResult.vwap_slippage_bps)],["POV",`${(qualResult.participation_rate*100)?.toFixed(2)}%`],["Commission",bps(qualResult.commission_bps)],["IS",bps(qualResult.implementation_shortfall_bps)]].map(([l,v])=>(
                  <div key={l} style={S.metric}><div style={S.mLabel}>{l}</div><div style={{ ...S.mVal, color: l==="Quality Score"?(qualResult.quality_score>=80?"#3fb950":qualResult.quality_score>=60?"#e3b341":"#ff7b72"):"#f0f6fc" }}>{v}</div></div>
                ))}
              </div>
            )}
          </div>
          {err && <div style={S.err}>{err}</div>}
        </div>
      </div>
    </div>
  );
}
