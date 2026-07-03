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
  table: { width: "100%", borderCollapse: "collapse" },
  th: { fontSize: 11, color: "#8b949e", textAlign: "left", borderBottom: "1px solid #21262d", padding: "4px 8px" },
  td: { fontSize: 12, color: "#c9d1d9", padding: "6px 8px", borderBottom: "1px solid #161b22" },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  ok: { color: "#3fb950", fontSize: 12, marginTop: 8 },
};

const STATUS_COLORS = { NEW:"#58a6ff", PENDING_NEW:"#e3b341", PARTIALLY_FILLED:"#e3b341", FILLED:"#3fb950", CANCELLED:"#8b949e", REJECTED:"#ff7b72", EXPIRED:"#8b949e", PENDING_CANCEL:"#e3b341", REPLACED:"#8b949e" };
const SIDE_COLORS = { BUY:"#3fb950", SELL:"#ff7b72", SELL_SHORT:"#ff7b72", BUY_TO_COVER:"#3fb950" };

export default function M17Orders() {
  const [orders, setOrders] = useState([]);
  const [openOrders, setOpenOrders] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filterForm, setFilterForm] = useState({ ticker:"", status:"", side:"" });
  const [cancelId, setCancelId] = useState("");
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);
  const [tab, setTab] = useState("all");
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);

  const loadAll = async () => {
    const params = new URLSearchParams();
    if (filterForm.ticker) params.set("ticker", filterForm.ticker.toUpperCase());
    if (filterForm.status) params.set("status", filterForm.status);
    if (filterForm.side) params.set("side", filterForm.side);
    const r = await fetch(`/trading/oms/orders?${params}`);
    if (r.ok) setOrders((await r.json()).orders || []);
  };

  const loadOpen = async () => {
    const r = await fetch("/trading/oms/orders/open");
    if (r.ok) setOpenOrders((await r.json()).orders || []);
  };

  const loadSummary = async () => {
    const r = await fetch("/trading/oms/summary");
    if (r.ok) setSummary(await r.json());
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([loadAll(), loadOpen(), loadSummary()])
      .then(() => { setLoading(false); setFetchError(null); })
      .catch(() => { setFetchError("Unable to connect to the backend"); setLoading(false); });
  }, []);

  const cancelOrder = async () => {
    setMsg(null); setErr(null);
    const r = await fetch("/trading/oms/orders/cancel", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ order_id:cancelId }) });
    if (r.ok) { setMsg("Order cancelled"); loadAll(); loadOpen(); loadSummary(); }
    else { const d = await r.json(); setErr(d.detail); }
  };

  const renderOrderRow = (o) => (
    <tr key={o.order_id}>
      <td style={{ ...S.td, fontFamily:"monospace", fontSize:10, color:"#8b949e" }}>{o.order_id?.slice(0,8)}…</td>
      <td style={{ ...S.td, fontWeight:700 }}>{o.ticker}</td>
      <td style={{ ...S.td, color: SIDE_COLORS[o.side] || "#c9d1d9" }}>{o.side}</td>
      <td style={S.td}>{o.order_type}</td>
      <td style={S.td}>{o.quantity}</td>
      <td style={S.td}>{o.filled_quantity || 0}</td>
      <td style={S.td}>{o.limit_price ? `$${o.limit_price}` : "MKT"}</td>
      <td style={S.td}><span style={{ background:(STATUS_COLORS[o.status]||"#8b949e")+"22", color:STATUS_COLORS[o.status]||"#8b949e", padding:"2px 6px", borderRadius:4, fontSize:10, fontWeight:700 }}>{o.status}</span></td>
      <td style={S.td}>{o.avg_fill_price ? `$${Number(o.avg_fill_price).toFixed(2)}` : "—"}</td>
    </tr>
  );

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 300, color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
      Loading…
    </div>
  );

  if (fetchError && orders.length === 0 && openOrders.length === 0) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, gap: 12 }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--negative)", letterSpacing: "0.1em" }}>ERROR</div>
      <div style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-3)" }}>Unable to connect to the backend</div>
      <button onClick={() => { setLoading(true); Promise.all([loadAll(), loadOpen(), loadSummary()]).finally(() => setLoading(false)); }} style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)", background: "var(--accent)22", border: "1px solid var(--accent)55", borderRadius: 6, padding: "6px 16px", cursor: "pointer" }}>Retry</button>
    </div>
  );

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Order Book</div>

      {summary && (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:10, marginBottom:16 }}>
          {[["Total Orders",summary.total_orders],["Open",summary.open_orders],["Filled",summary.filled_orders],["Cancelled",summary.cancelled_orders],["Rejected",summary.rejected_orders]].map(([l,v])=>(
            <div key={l} style={{ ...S.card, marginBottom:0 }}>
              <div style={{ fontSize:10, color:"#8b949e", textTransform:"uppercase" }}>{l}</div>
              <div style={{ fontSize:20, fontWeight:700, color:"#f0f6fc" }}>{v ?? 0}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display:"flex", gap:8, marginBottom:16 }}>
        {["all","open"].map(t=>(
          <button key={t} style={{ ...S.btn, background:tab===t?"#1f6feb":"#21262d" }} onClick={()=>setTab(t)}>{t==="all"?"All Orders":"Open Orders"}</button>
        ))}
      </div>

      {tab === "all" && (
        <div style={S.card}>
          <div style={{ ...S.sHdr, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            All Orders ({orders.length})
            <button style={{ ...S.btn, background:"#21262d", padding:"4px 10px", fontSize:11 }} onClick={loadAll}>↻</button>
          </div>
          <div style={{ display:"flex", gap:8, marginBottom:12 }}>
            <input style={{ ...S.input, flex:1 }} placeholder="Filter by ticker" value={filterForm.ticker} onChange={e=>setFilterForm(p=>({...p,ticker:e.target.value}))} />
            <select style={{ ...S.select, flex:1 }} value={filterForm.status} onChange={e=>setFilterForm(p=>({...p,status:e.target.value}))}>
              <option value="">All Statuses</option>
              {["NEW","PENDING_NEW","PARTIALLY_FILLED","FILLED","CANCELLED","REJECTED","EXPIRED","REPLACED"].map(s=><option key={s}>{s}</option>)}
            </select>
            <select style={{ ...S.select, flex:1 }} value={filterForm.side} onChange={e=>setFilterForm(p=>({...p,side:e.target.value}))}>
              <option value="">All Sides</option>
              {["BUY","SELL","SELL_SHORT","BUY_TO_COVER"].map(s=><option key={s}>{s}</option>)}
            </select>
            <button style={S.btn} onClick={loadAll}>Filter</button>
          </div>
          <table style={S.table}>
            <thead><tr>{["ID","Ticker","Side","Type","Qty","Filled","Price","Status","Avg Fill"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {orders.map(renderOrderRow)}
              {orders.length===0 && <tr><td colSpan={9} style={{...S.td,textAlign:"center",color:"#8b949e"}}>No orders</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "open" && (
        <div style={S.card}>
          <div style={{ ...S.sHdr, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            Open Orders ({openOrders.length})
            <button style={{ ...S.btn, background:"#21262d", padding:"4px 10px", fontSize:11 }} onClick={loadOpen}>↻</button>
          </div>
          <table style={S.table}>
            <thead><tr>{["ID","Ticker","Side","Type","Qty","Filled","Price","Status","Avg Fill"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {openOrders.map(renderOrderRow)}
              {openOrders.length===0 && <tr><td colSpan={9} style={{...S.td,textAlign:"center",color:"#8b949e"}}>No open orders</td></tr>}
            </tbody>
          </table>
          <div style={{ marginTop:16, display:"flex", gap:8, alignItems:"center" }}>
            <input style={{ ...S.input, flex:1 }} placeholder="Order ID to cancel" value={cancelId} onChange={e=>setCancelId(e.target.value)} />
            <button style={{ background:"#da3633", color:"#fff", border:"none", borderRadius:6, padding:"7px 16px", cursor:"pointer", fontSize:12, fontWeight:700 }} onClick={cancelOrder}>Cancel Order</button>
          </div>
          {msg && <div style={S.ok}>{msg}</div>}
          {err && <div style={S.err}>{err}</div>}
        </div>
      )}
    </div>
  );
}
