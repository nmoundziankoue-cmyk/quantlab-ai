import { useState, useEffect } from "react";

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
  btnDanger: { background: "#da3633", color: "#fff", border: "none", borderRadius: 6, padding: "7px 16px", cursor: "pointer", fontSize: 12, fontWeight: 700 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { fontSize: 11, color: "#8b949e", textAlign: "left", borderBottom: "1px solid #21262d", padding: "4px 8px" },
  td: { fontSize: 12, color: "#c9d1d9", padding: "6px 8px", borderBottom: "1px solid #161b22" },
  metric: { display:"flex", flexDirection:"column" },
  mLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase", marginBottom: 2 },
  mVal: { fontSize: 18, fontWeight: 700, color: "#f0f6fc" },
  ok: { color: "#3fb950", fontSize: 12, marginTop: 8 },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
};

export default function M17PaperTrading() {
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [fills, setFills] = useState([]);
  const [prices, setPrices] = useState("AAPL:175,MSFT:420,NVDA:890,TSLA:250");
  const [orderForm, setOrderForm] = useState({ ticker:"AAPL", side:"BUY", quantity:100, order_type:"market", limit_price:"" });
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      fetch("/trading/paper/account").then(r=>r.json()).then(setAccount).catch(()=>{}),
      fetch("/trading/paper/positions").then(r=>r.json()).then(d=>setPositions(d.positions||[])).catch(()=>{}),
      fetch("/trading/paper/fills").then(r=>r.json()).then(d=>setFills(d.fills||[])).catch(()=>{}),
    ]).then(() => { setLoading(false); setFetchError(null); }).catch(() => { setFetchError("Unable to connect to the backend"); setLoading(false); });
  };
  useEffect(() => { load(); }, []);

  const updatePrices = async () => {
    const pricesObj = {};
    prices.split(",").forEach(s => { const [t,v] = s.split(":"); if(t&&v) pricesObj[t.trim().toUpperCase()]=Number(v); });
    const r = await fetch("/trading/paper/prices", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({prices:pricesObj}) });
    if (r.ok) { setMsg("Prices updated"); load(); }
  };

  const placeOrder = async () => {
    setMsg(null); setErr(null);
    const isMarket = orderForm.order_type === "market";
    const url = isMarket ? "/trading/paper/market-order" : "/trading/paper/limit-order";
    const body = { ticker: orderForm.ticker, side: orderForm.side, quantity: Number(orderForm.quantity) };
    if (!isMarket) body.limit_price = Number(orderForm.limit_price);
    const r = await fetch(url, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    if (r.ok) {
      const d = await r.json();
      setMsg(d.is_filled === false ? `Rejected: ${d.reject_reason}` : `Filled ${d.filled_qty} @ $${d.fill_price?.toFixed(2)}`);
      load();
    } else {
      const d = await r.json();
      setErr(d.detail || "Error");
    }
  };

  const reset = async () => {
    await fetch("/trading/paper/reset", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({}) });
    setMsg("Simulator reset"); load();
  };

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 300, color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
      Loading…
    </div>
  );

  if (fetchError && !account) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, gap: 12 }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--negative)", letterSpacing: "0.1em" }}>ERROR</div>
      <div style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-3)" }}>Unable to connect to the backend</div>
      <button onClick={load} style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)", background: "var(--accent)22", border: "1px solid var(--accent)55", borderRadius: 6, padding: "6px 16px", cursor: "pointer" }}>Retry</button>
    </div>
  );

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Paper Trading Simulator</div>

      {account && (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:20 }}>
          {[["Cash",`$${account.cash?.toLocaleString("en-US",{minimumFractionDigits:2})}`],["Equity",`$${account.equity?.toLocaleString("en-US",{minimumFractionDigits:2})}`],["Unrealised P&L",`$${account.unrealised_pnl?.toFixed(2)}`],["Trades",account.trade_count]].map(([l,v])=>(
            <div key={l} style={{ ...S.card, marginBottom:0 }}><div style={S.mLabel}>{l}</div><div style={S.mVal}>{v}</div></div>
          ))}
        </div>
      )}

      <div style={S.row}>
        <div style={{ flex:"0 0 300px" }}>
          <div style={S.card}>
            <div style={S.sHdr}>Market Prices</div>
            <textarea style={{ ...S.input, height:80, resize:"vertical", fontFamily:"monospace", fontSize:11 }} value={prices} onChange={e=>setPrices(e.target.value)} placeholder="AAPL:175,MSFT:420" />
            <button style={{ ...S.btn, marginTop:8, width:"100%" }} onClick={updatePrices}>Update Prices</button>
          </div>

          <div style={S.card}>
            <div style={S.sHdr}>Place Order</div>
            <div style={S.field}><label style={S.label}>Ticker</label><input style={S.input} value={orderForm.ticker} onChange={e=>setOrderForm(p=>({...p,ticker:e.target.value.toUpperCase()}))} /></div>
            <div style={S.field}><label style={S.label}>Side</label>
              <select style={S.select} value={orderForm.side} onChange={e=>setOrderForm(p=>({...p,side:e.target.value}))}>
                {["BUY","SELL","SELL_SHORT","BUY_TO_COVER"].map(s=><option key={s}>{s}</option>)}
              </select>
            </div>
            <div style={S.field}><label style={S.label}>Quantity</label><input style={S.input} type="number" value={orderForm.quantity} onChange={e=>setOrderForm(p=>({...p,quantity:e.target.value}))} /></div>
            <div style={S.field}><label style={S.label}>Order Type</label>
              <select style={S.select} value={orderForm.order_type} onChange={e=>setOrderForm(p=>({...p,order_type:e.target.value}))}>
                <option value="market">MARKET</option>
                <option value="limit">LIMIT</option>
              </select>
            </div>
            {orderForm.order_type === "limit" && (
              <div style={S.field}><label style={S.label}>Limit Price</label><input style={S.input} type="number" step="0.01" value={orderForm.limit_price} onChange={e=>setOrderForm(p=>({...p,limit_price:e.target.value}))} /></div>
            )}
            <div style={{ display:"flex", gap:8, marginTop:4 }}>
              <button style={{ ...S.btn, flex:1 }} onClick={placeOrder}>Place Order</button>
              <button style={{ ...S.btnDanger, flex:"0 0 auto" }} onClick={reset}>Reset</button>
            </div>
            {msg && <div style={S.ok}>{msg}</div>}
            {err && <div style={S.err}>{err}</div>}
          </div>
        </div>

        <div style={{ flex:1 }}>
          <div style={{ ...S.card, marginBottom:12 }}>
            <div style={{ ...S.sHdr, display:"flex", justifyContent:"space-between" }}>Open Positions<button style={{ ...S.btn, padding:"4px 10px", fontSize:11, background:"#21262d" }} onClick={load}>↻</button></div>
            <table style={S.table}>
              <thead><tr>{["Ticker","Side","Qty","Avg Cost","P&L","Mkt Value"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
              <tbody>
                {positions.map(p=>(
                  <tr key={p.ticker}>
                    <td style={{...S.td,fontWeight:700}}>{p.ticker}</td>
                    <td style={{...S.td,color:p.side==="LONG"?"#3fb950":"#ff7b72"}}>{p.side}</td>
                    <td style={S.td}>{p.quantity}</td>
                    <td style={S.td}>${p.avg_cost?.toFixed(2)}</td>
                    <td style={{...S.td,color:p.unrealised_pnl>=0?"#3fb950":"#ff7b72"}}>${p.unrealised_pnl?.toFixed(2)}</td>
                    <td style={S.td}>${p.market_value?.toFixed(2)}</td>
                  </tr>
                ))}
                {positions.length===0 && <tr><td colSpan={6} style={{...S.td,textAlign:"center",color:"#8b949e"}}>No open positions</td></tr>}
              </tbody>
            </table>
          </div>
          <div style={S.card}>
            <div style={S.sHdr}>Recent Fills ({fills.length})</div>
            <table style={S.table}>
              <thead><tr>{["Ticker","Side","Qty","Fill Price","Commission","Status"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
              <tbody>
                {fills.slice().reverse().slice(0,10).map((f,i)=>(
                  <tr key={i}>
                    <td style={{...S.td,fontWeight:700}}>{f.ticker}</td>
                    <td style={{...S.td,color:f.side==="BUY"?"#3fb950":"#ff7b72"}}>{f.side}</td>
                    <td style={S.td}>{f.filled_qty}</td>
                    <td style={S.td}>${f.fill_price?.toFixed(2)}</td>
                    <td style={S.td}>${f.commission?.toFixed(2)}</td>
                    <td style={S.td}>{f.is_filled ? "✓ FILLED" : "✗ REJECTED"}</td>
                  </tr>
                ))}
                {fills.length===0 && <tr><td colSpan={6} style={{...S.td,textAlign:"center",color:"#8b949e"}}>No fills yet</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
