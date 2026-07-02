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
  btn: { background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "8px 20px", cursor: "pointer", fontSize: 13, fontWeight: 700 },
  btnDanger: { background: "#da3633", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", cursor: "pointer", fontSize: 12 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { fontSize: 11, color: "#8b949e", textAlign: "left", borderBottom: "1px solid #21262d", padding: "4px 8px" },
  td: { fontSize: 12, color: "#c9d1d9", padding: "6px 8px", borderBottom: "1px solid #161b22" },
  badge: (c) => ({ display:"inline-block", fontSize:10, padding:"2px 6px", borderRadius:4, background:c+"22", color:c, fontWeight:700 }),
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  ok: { color: "#3fb950", fontSize: 12, marginTop: 8 },
};

const STATUS_COLORS = { WORKING:"#58a6ff", PARTIAL:"#e3b341", FILLED:"#3fb950", CANCELLED:"#8b949e", REJECTED:"#ff7b72", EXPIRED:"#8b949e", AMENDED:"#a371f7" };

const ORDER_TYPES = ["MARKET","LIMIT","STOP","STOP_LIMIT","TRAILING_STOP","IOC","FOK","GTC","GTD","DAY","BRACKET","OCO","ICEBERG","TWAP","VWAP","PEGGED","HIDDEN","SYNTHETIC","MOO","MOC","LOO","LOC"];
const SIDES = ["BUY","SELL","SELL_SHORT","BUY_TO_COVER"];
const TIFS = ["DAY","GTC","GTD","IOC","FOK","ATO","ATC"];

export default function M17OMS() {
  const [form, setForm] = useState({ ticker:"AAPL", order_type:"MARKET", side:"BUY", quantity:100, limit_price:"", stop_price:"", strategy_tag:"" });
  const [orders, setOrders] = useState([]);
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);

  const load = () =>
    fetch("/trading/orders").then(r => r.json()).then(d => setOrders(d.orders || [])).catch(() => {});

  useEffect(() => { load(); }, []);

  const submit = async () => {
    setMsg(null); setErr(null);
    const body = { ...form, quantity: Number(form.quantity) };
    if (form.limit_price) body.limit_price = Number(form.limit_price);
    if (form.stop_price) body.stop_price = Number(form.stop_price);
    if (!form.limit_price) delete body.limit_price;
    if (!form.stop_price) delete body.stop_price;
    const r = await fetch("/trading/orders/submit", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    if (r.ok) { setMsg("Order submitted"); load(); }
    else { const d = await r.json(); setErr(d.detail || "Error"); }
  };

  const cancelOrder = async (id) => {
    await fetch(`/trading/orders/${id}/cancel`, { method:"POST" });
    load();
  };

  const f = (k, v) => setForm(p => ({ ...p, [k]: v }));

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Order Management System</div>
      <div style={S.row}>
        <div style={{ flex: "0 0 340px" }}>
          <div style={S.card}>
            <div style={S.sHdr}>Submit Order</div>
            {[["ticker","Ticker","text"],["quantity","Quantity","number"]].map(([k,l,t]) => (
              <div key={k} style={S.field}>
                <label style={S.label}>{l}</label>
                <input style={S.input} type={t} value={form[k]} onChange={e => f(k, e.target.value)} />
              </div>
            ))}
            <div style={S.field}>
              <label style={S.label}>Order Type</label>
              <select style={S.select} value={form.order_type} onChange={e => f("order_type", e.target.value)}>
                {ORDER_TYPES.map(ot => <option key={ot}>{ot}</option>)}
              </select>
            </div>
            <div style={S.field}>
              <label style={S.label}>Side</label>
              <select style={S.select} value={form.side} onChange={e => f("side", e.target.value)}>
                {SIDES.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
            {["limit_price","stop_price"].map(k => (
              <div key={k} style={S.field}>
                <label style={S.label}>{k.replace("_"," ").toUpperCase()}</label>
                <input style={S.input} type="number" step="0.01" value={form[k]} onChange={e => f(k, e.target.value)} placeholder="Optional" />
              </div>
            ))}
            <div style={S.field}>
              <label style={S.label}>Strategy Tag</label>
              <input style={S.input} value={form.strategy_tag} onChange={e => f("strategy_tag", e.target.value)} placeholder="Optional" />
            </div>
            <button style={S.btn} onClick={submit}>Submit Order</button>
            {msg && <div style={S.ok}>{msg}</div>}
            {err && <div style={S.err}>{err}</div>}
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <div style={S.card}>
            <div style={{ ...S.sHdr, display:"flex", justifyContent:"space-between" }}>
              All Orders
              <button style={{ ...S.btn, padding:"4px 12px", fontSize:11 }} onClick={load}>Refresh</button>
            </div>
            <table style={S.table}>
              <thead>
                <tr>{["ID","Ticker","Type","Side","Qty","Filled","Price","Status","Actions"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {orders.slice(-20).reverse().map(o => (
                  <tr key={o.order_id}>
                    <td style={S.td}>{o.order_id.slice(0,8)}</td>
                    <td style={S.td}>{o.ticker}</td>
                    <td style={S.td}>{o.order_type}</td>
                    <td style={S.td}>{o.side}</td>
                    <td style={S.td}>{o.quantity}</td>
                    <td style={S.td}>{o.filled_quantity}</td>
                    <td style={S.td}>{o.avg_fill_price ? o.avg_fill_price.toFixed(2) : o.limit_price?.toFixed(2) ?? "—"}</td>
                    <td style={S.td}><span style={S.badge(STATUS_COLORS[o.status] || "#8b949e")}>{o.status}</span></td>
                    <td style={S.td}>
                      {["WORKING","PARTIAL","AMENDED"].includes(o.status) &&
                        <button style={S.btnDanger} onClick={() => cancelOrder(o.order_id)}>Cancel</button>}
                    </td>
                  </tr>
                ))}
                {orders.length === 0 && <tr><td colSpan={9} style={{ ...S.td, textAlign:"center", color:"#8b949e" }}>No orders</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
